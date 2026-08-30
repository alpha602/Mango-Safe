from __future__ import annotations

import sys
import os
import json
import time
import logging
import threading
import traceback
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

APP_NAME = "MangoSafe"
APP_VERSION = "0.3.0"

if os.name == "nt":
    APP_DATA_DIR = Path(os.environ.get("APPDATA", Path.home())) / APP_NAME
else:
    APP_DATA_DIR = Path.home() / f".{APP_NAME.lower()}"

VAULT_FILE = APP_DATA_DIR / "vault.dat"
CONFIG_FILE = APP_DATA_DIR / "config.json"
LOG_FILE = APP_DATA_DIR / "mangosafe.log"

DEFAULT_AUTO_LOCK_MINUTES = 2
MAX_QUICK_ATTEMPTS = 3
LOCKOUT_SECONDS = 30

SUPPORTED_LANGUAGES = ("de", "en", "ru")


def _detect_system_language() -> str:
    candidates = []
    if os.name == "nt":
        try:
            import ctypes
            lcid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            import locale as _locale
            windows_locale = _locale.windows_locale.get(lcid)
            if windows_locale:
                candidates.append(windows_locale)
        except Exception:
            pass
    try:
        import locale as _locale
        loc = _locale.getlocale()[0] or _locale.getdefaultlocale()[0]
        if loc:
            candidates.append(loc)
    except Exception:
        pass
    for env_var in ("LANG", "LANGUAGE", "LC_ALL"):
        val = os.environ.get(env_var)
        if val:
            candidates.append(val)
    for candidate in candidates:
        prefix = candidate.lower().replace("-", "_").split("_")[0]
        if prefix in SUPPORTED_LANGUAGES:
            return prefix
    return "de"


@dataclass
class PasswordEntry:
    entry_id: str
    site: str
    username: str
    password: str
    notes: str = ""
    favorite: bool = False
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def matches(self, query: str) -> bool:
        q = query.strip().lower()
        if not q:
            return True
        return q in self.site.lower() or q in self.username.lower()


@dataclass
class AppConfig:
    auto_lock_minutes: int = DEFAULT_AUTO_LOCK_MINUTES
    use_windows_hello: bool = True
    first_run_completed: bool = False
    theme: str = "dark"
    language: str = "de"
    accent_color: str = "purple"

    @classmethod
    def load(cls) -> "AppConfig":
        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
                cfg = cls()
                for key, value in data.items():
                    if hasattr(cfg, key):
                        setattr(cfg, key, value)
                if cfg.language not in SUPPORTED_LANGUAGES:
                    cfg.language = _detect_system_language()
                return cfg
            except Exception:
                logging.exception("Could not read config.json, using defaults.")
        config = cls()
        config.language = _detect_system_language()
        return config

    def save(self) -> None:
        APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")


def setup_logging() -> None:
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


class InactivityMonitor:
    def __init__(self, timeout_minutes: int, on_timeout: Callable[[], None]):
        self.timeout_minutes = timeout_minutes
        self.on_timeout = on_timeout
        self._last_activity = time.monotonic()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._stop.clear()
        self._last_activity = time.monotonic()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def notify_activity(self) -> None:
        self._last_activity = time.monotonic()

    def update_timeout(self, minutes: int) -> None:
        self.timeout_minutes = max(1, minutes)

    def _run(self) -> None:
        while not self._stop.is_set():
            time.sleep(1)
            if self.timeout_minutes <= 0:
                continue
            idle_seconds = time.monotonic() - self._last_activity
            if idle_seconds >= self.timeout_minutes * 60:
                try:
                    self.on_timeout()
                except Exception:
                    logging.exception("Error while auto-locking.")
                self._last_activity = time.monotonic()


class LoginThrottle:
    def __init__(self):
        self.failed_attempts = 0
        self.locked_until: float = 0.0

    def is_locked(self) -> bool:
        return time.monotonic() < self.locked_until

    def seconds_remaining(self) -> int:
        return max(0, int(self.locked_until - time.monotonic()))

    def register_failure(self) -> bool:
        self.failed_attempts += 1
        if self.failed_attempts >= MAX_QUICK_ATTEMPTS:
            self.locked_until = time.monotonic() + LOCKOUT_SECONDS
            self.failed_attempts = 0
            return True
        return False

    def register_success(self) -> None:
        self.failed_attempts = 0
        self.locked_until = 0.0


class MangoSafeApp:
    def __init__(self):
        self.log = logging.getLogger(__name__)
        self.config = AppConfig.load()
        from vault import Vault
        from uiDS import MangoSafeUI
        self.vault = Vault(VAULT_FILE)
        self.ui = MangoSafeUI(self)
        self.throttle = LoginThrottle()
        self.auto_lock = InactivityMonitor(
            timeout_minutes=self.config.auto_lock_minutes,
            on_timeout=self._handle_auto_lock,
        )

    def run(self) -> None:
        try:
            if not self.vault.exists():
                self.ui.show_setup_screen(on_submit=self.handle_first_time_setup)
            else:
                self._show_login(error=None)
            self.ui.run()
        except Exception:
            self.log.exception("Fatal error, shutting down.")
            raise
        finally:
            self._shutdown()

    def _shutdown(self) -> None:
        self.auto_lock.stop()
        if self.vault.is_unlocked():
            self.vault.lock()
        self.config.save()

    def notify_activity(self) -> None:
        self.auto_lock.notify_activity()

    def handle_first_time_setup(self, master_password: str) -> None:
        master_password = (master_password or "").strip()
        if len(master_password) < 8:
            self.ui.show_error(self.ui.t("error_master_password_too_short"))
            self.ui.show_setup_screen(on_submit=self.handle_first_time_setup)
            return
        try:
            recovery_token = self.vault.create(master_password)
        except Exception as exc:
            self.log.exception("Could not create vault.")
            self.ui.show_error(f"Tresor konnte nicht erstellt werden: {exc}")
            self.ui.show_setup_screen(on_submit=self.handle_first_time_setup)
            return
        self.config.first_run_completed = True
        self.config.save()
        self.ui.show_recovery_key(recovery_token, lambda: self._finish_first_time_setup(master_password))

    def _finish_first_time_setup(self, master_password: str) -> None:
        if self.vault.unlock(master_password):
            self._on_unlocked()
        else:
            self._show_login(error=None)

    def _show_login(self, error: Optional[str]) -> None:
        self.ui.show_login_screen(
            on_submit=self.handle_login_attempt,
            on_windows_hello=self.handle_windows_hello_attempt,
            error=error,
        )

    def handle_windows_hello_attempt(self, auto_triggered: bool = False) -> None:
        if not self.config.use_windows_hello:
            self._reject_login(self.ui.t("windows_hello_disabled"))
            return
        if self.throttle.is_locked():
            self._reject_login(self._lockout_message())
            return

        def worker() -> None:
            try:
                owner_hwnd = self.ui.root.winfo_id()
                success = self.vault.try_windows_hello(owner_hwnd=owner_hwnd)
            except Exception:
                success = False
            self.ui.root.after(0, lambda: self._finish_windows_hello_attempt(success, auto_triggered))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_windows_hello_attempt(self, success: bool, auto_triggered: bool) -> None:
        self.ui._bring_to_front_centered()
        if success:
            self.throttle.register_success()
            self._on_unlocked()
        elif not auto_triggered:
            if self.throttle.register_failure():
                if self.vault.has_recovery_key():
                    self._reject_login(self._lockout_message())
                else:
                    self._trigger_security_wipe()
            else:
                self._reject_login("Windows Hello fehlgeschlagen. Bitte PIN/Passwort eingeben.")

    def handle_login_attempt(self, password_or_pin: str) -> None:
        if self.throttle.is_locked():
            self._reject_login(self._lockout_message())
            return
        password_or_pin = (password_or_pin or "").strip()
        if not password_or_pin:
            self._reject_login("Bitte Passwort oder PIN eingeben.")
            return
        try:
            success = self.vault.unlock(password_or_pin)
        except Exception:
            success = False
        if success:
            self.throttle.register_success()
            self._on_unlocked()
        elif self.throttle.register_failure():
            if self.vault.has_recovery_key():
                self._reject_login(self._lockout_message())
            else:
                self._trigger_security_wipe()
        else:
            self._reject_login("Falsches Passwort/PIN.")

    def _trigger_security_wipe(self) -> None:
        try:
            self.vault.wipe()
        except Exception:
            pass
        self.throttle.register_success()
        self.config.first_run_completed = False
        self.config.save()
        self.ui.show_error("Zu viele Fehlversuche. Tresor wurde gelöscht.")
        self.ui.show_setup_screen(on_submit=self.handle_first_time_setup)

    def _reject_login(self, message: str) -> None:
        self._show_login(error=message)

    def _lockout_message(self) -> str:
        return f"Zu viele Fehlversuche. Bitte {self.throttle.seconds_remaining()}s warten."

    def _on_unlocked(self) -> None:
        self.auto_lock.start()
        entries = self._load_entries_safely()
        self.ui.show_main_screen(entries)

    def _handle_auto_lock(self) -> None:
        if self.vault.is_unlocked():
            self.vault.lock()
            self.auto_lock.stop()
            self._show_login(error=None)

    def _load_entries_safely(self) -> list[PasswordEntry]:
        try:
            return self.vault.get_all_entries()
        except Exception:
            return []

    def request_add_entry(self) -> None:
        self.ui.show_entry_form(existing_entry=None, on_save=self.handle_add_entry)

    def request_edit_entry(self, entry_id: str) -> None:
        entry = self._find_entry(entry_id)
        if entry is None:
            return
        def on_save(site: str, username: str, password: str, notes: str = "") -> None:
            self.handle_edit_entry(entry_id, site, username, password, notes)
        self.ui.show_entry_form(existing_entry=entry, on_save=on_save)

    def handle_edit_entry(self, entry_id: str, site: str, username: str, password: str, notes: str = "") -> None:
        try:
            self.vault.update_entry(entry_id, site=site, username=username, password=password, notes=notes)
            self.ui.show_toast(f"'{site}' gespeichert.")
            self.ui.show_main_screen(self._load_entries_safely())
            self.ui.invalidate_cache()
        except Exception:
            self.ui.show_error("Speichern fehlgeschlagen.")

    def request_toggle_favorite(self, entry_id: str) -> None:
        entry = self._find_entry(entry_id)
        if entry is None:
            return
        try:
            self.vault.update_entry(entry_id, favorite=not entry.favorite)
            self.ui.show_main_screen(self._load_entries_safely())
        except Exception:
            pass

    def _find_entry(self, entry_id: str) -> Optional[PasswordEntry]:
        for entry in self._load_entries_safely():
            if entry.entry_id == entry_id:
                return entry
        return None

    def handle_add_entry(self, site: str, username: str, password: str, notes: str = "") -> None:
        if not site or not password:
            self.ui.show_error("Website und Passwort sind Pflicht.")
            return
        try:
            self.vault.add_entry(site=site, username=username, password=password, notes=notes)
            self.ui.show_toast(f"'{site}' gespeichert.")
            self.ui.show_main_screen(self._load_entries_safely())
            self.ui.invalidate_cache()
        except Exception:
            self.ui.show_error("Speichern fehlgeschlagen.")

    def request_delete_entry(self, entry_id: str) -> None:
        try:
            self.vault.delete_entry(entry_id)
            self.ui.show_toast("Eintrag gelöscht.")
            self.ui.show_main_screen(self._load_entries_safely())
            self.ui.invalidate_cache()
        except Exception:
            self.ui.show_error("Löschen fehlgeschlagen.")

    def handle_search(self, query: str) -> None:
        if not query.strip():
            self.ui.show_main_screen(self._load_entries_safely())
            return
        try:
            results = self.vault.search_entries(query)
            self.ui.show_search_results(query, results)
        except Exception:
            pass

    def set_auto_lock_minutes(self, minutes: int) -> None:
        self.config.auto_lock_minutes = max(1, int(minutes))
        self.config.save()
        self.auto_lock.update_timeout(self.config.auto_lock_minutes)

    def set_use_windows_hello(self, enabled: bool) -> None:
        self.config.use_windows_hello = bool(enabled)
        self.config.save()

    def set_language(self, language_code: str) -> None:
        self.config.language = language_code
        self.config.save()
        self.ui.lang = language_code

    def set_accent_color(self, color_key: str) -> None:
        self.config.accent_color = color_key
        self.config.save()
        self.ui.accent_key = color_key

    def set_theme_mode(self, mode: str) -> None:
        self.config.theme = mode
        self.config.save()

    def request_lock_now(self) -> None:
        self._handle_auto_lock()

    def request_reset_master_password(self) -> None:
        if not self.vault.has_recovery_key():
            self.ui.show_error(self.ui.t("no_recovery_key"))
            self._show_login(error=None)
            return
        self.ui.show_reset_screen(on_submit=self.handle_reset_master_password)

    def handle_reset_master_password(self, recovery_token: str, new_password: str) -> None:
        recovery_token = (recovery_token or "").strip()
        new_password = (new_password or "").strip()
        if not recovery_token:
            self.ui.show_error(self.ui.t("error_recovery_required"))
            self.ui.show_reset_screen(on_submit=self.handle_reset_master_password)
            return
        if len(new_password) < 8:
            self.ui.show_error(self.ui.t("error_master_password_too_short"))
            self.ui.show_reset_screen(on_submit=self.handle_reset_master_password)
            return
        try:
            ok = self.vault.reset_master_password(recovery_token, new_password)
        except Exception:
            ok = False
        if not ok:
            self.ui.show_error(self.ui.t("error_recovery_invalid"))
            self.ui.show_reset_screen(on_submit=self.handle_reset_master_password)
            return
        self.throttle.register_success()
        if self.vault.unlock(new_password):
            self._on_unlocked()
        else:
            self._show_login(error=None)

    def request_create_recovery_key(self) -> None:
        try:
            token = self.vault.create_recovery_key()
        except Exception:
            self.ui.show_error(self.ui.t("error_recovery_create_failed"))
            return
        if not token:
            self.ui.show_error(self.ui.t("error_recovery_create_failed"))
            return
        self.ui.show_recovery_key(token, lambda: self.ui.show_main_screen(self._load_entries_safely()))

    def change_master_password(self, old_password: str, new_password: str) -> None:
        if len(new_password) < 8:
            self.ui.show_error(self.ui.t("error_master_password_too_short"))
            return
        try:
            ok = self.vault.change_master_password(old_password, new_password)
        except Exception:
            ok = False
        if not ok:
            self.ui.show_error(self.ui.t("error_old_password_wrong"))
            return
        self.ui.show_toast(self.ui.t("master_password_changed"))
        self.ui.show_main_screen(self._load_entries_safely())


def main() -> int:
    setup_logging()
    log = logging.getLogger("main")
    try:
        app = MangoSafeApp()
        app.run()
        return 0
    except Exception:
        log.critical("Fatal error:\n%s", traceback.format_exc())
        print(f"\n[{APP_NAME}] Ein unerwarteter Fehler ist aufgetreten.")
        print(f"Details in: {LOG_FILE}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    os._exit(exit_code)