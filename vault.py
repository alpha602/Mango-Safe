from __future__ import annotations

import os
import json
import time
import base64
import logging
import secrets
import asyncio
import threading
import contextlib
import hmac
import hashlib
import gc
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

try:
    from main import PasswordEntry
except Exception:
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


log = logging.getLogger("vault")


class VaultError(Exception):
    pass


class VaultLockedError(VaultError):
    def __init__(self):
        super().__init__("Vault is locked - unlock it first.")


PBKDF2_ITERATIONS = 480_000
SALT_SIZE_BYTES = 16
VERIFICATION_MARKER = b"mangosafe-vault-ok-v1"


def _new_salt() -> bytes:
    return secrets.token_bytes(SALT_SIZE_BYTES)


def _derive_key(password: str, salt: bytes, iterations: int = PBKDF2_ITERATIONS) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=iterations,
    )
    raw_key = kdf.derive(password.encode("utf-8"))
    return base64.urlsafe_b64encode(raw_key)


def _b64e(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _b64d(data: str) -> bytes:
    return base64.b64decode(data.encode("ascii"))

class WindowsHello:
    @staticmethod
    def is_available() -> bool:
        if os.name != "nt":
            return False
        try:
            import win32crypt
            import winsdk.windows.security.credentials.ui
        except Exception:
            return False
        return True

    @staticmethod
    def verify_user(message: str = "Bitte bestätige deine Identität für MangoSafe.",
                    owner_hwnd: Optional[int] = None) -> bool:
        if not WindowsHello.is_available():
            return False

        if owner_hwnd:
            threading.Thread(
                target=WindowsHello._reposition_hello_dialog,
                args=(owner_hwnd,),
                daemon=True
            ).start()

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(WindowsHello._verify_async(message))
            loop.close()
            return result
        except Exception:
            log.exception("Windows Hello verification failed.")
            return False

    @staticmethod
    def _reposition_hello_dialog(owner_hwnd: int, timeout_seconds: float = 2.0) -> None:
        try:
            import win32gui
            import win32con
        except Exception:
            return

        known_titles = ("windows-sicherheit", "windows security", "windows hello")
        deadline = time.monotonic() + timeout_seconds

        while time.monotonic() < deadline:
            dialog_hwnd = None

            def enum_callback(hwnd, _):
                nonlocal dialog_hwnd
                if dialog_hwnd is not None:
                    return
                if hwnd == owner_hwnd or not win32gui.IsWindowVisible(hwnd):
                    return
                title = win32gui.GetWindowText(hwnd).strip().lower()
                if any(needle in title for needle in known_titles):
                    dialog_hwnd = hwnd

            try:
                win32gui.EnumWindows(enum_callback, None)
            except Exception:
                return

            if dialog_hwnd is not None:
                try:
                    win32gui.SetForegroundWindow(dialog_hwnd)
                    win32gui.BringWindowToTop(dialog_hwnd)

                    win32gui.SetWindowPos(
                        dialog_hwnd,
                        win32con.HWND_TOPMOST,
                        0, 0, 0, 0,
                        win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW
                    )
                    ox1, oy1, ox2, oy2 = win32gui.GetWindowRect(owner_hwnd)
                    dx1, dy1, dx2, dy2 = win32gui.GetWindowRect(dialog_hwnd)
                    dw, dh = dx2 - dx1, dy2 - dy1
                    new_x = ox1 + ((ox2 - ox1) - dw) // 2
                    new_y = oy1 + ((oy2 - oy1) - dh) // 2

                    win32gui.SetWindowPos(
                        dialog_hwnd,
                        win32con.HWND_TOP,
                        new_x, new_y, 0, 0,
                        win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW
                    )

                    try:
                        win32gui.SetWindowLongPtr(
                            dialog_hwnd,
                            win32con.GWLP_HWNDPARENT,
                            owner_hwnd
                        )
                    except Exception:
                        pass

                    log.debug("Windows Hello dialog repositioned.")
                except Exception as e:
                    log.debug("Failed to reposition Windows Hello dialog: %s", e)
                return

            time.sleep(0.1)

    @staticmethod
    async def _verify_async(message: str) -> bool:
        from winsdk.windows.security.credentials.ui import (
            UserConsentVerifier,
            UserConsentVerifierAvailability,
            UserConsentVerificationResult,
        )
        availability = await UserConsentVerifier.check_availability_async()
        if availability != UserConsentVerifierAvailability.AVAILABLE:
            log.info("Windows Hello not available on this device (%s).", availability)
            return False
        result = await UserConsentVerifier.request_verification_async(message)
        return result == UserConsentVerificationResult.VERIFIED

    @staticmethod
    def protect_key(key: bytes) -> Optional[bytes]:
        if not WindowsHello.is_available():
            return None
        try:
            import win32crypt
            blob = win32crypt.CryptProtectData(
                key, "MangoSafe vault key", None, None, None, 0
            )
            return bytes(blob)
        except Exception:
            log.exception("DPAPI protect failed.")
            return None

    @staticmethod
    def unprotect_key(blob: bytes) -> Optional[bytes]:
        if not WindowsHello.is_available():
            return None
        try:
            import win32crypt
            _description, key = win32crypt.CryptUnprotectData(
                blob, None, None, None, 0
            )
            return bytes(key)
        except Exception:
            log.exception("DPAPI unprotect failed.")
            return None

class Vault:
    FORMAT_VERSION = 2

    def __init__(self, vault_path: Path):
        self.path = Path(vault_path)
        self._lock = threading.Lock()
        self._key: Optional[bytes] = None
        self._entries: list[PasswordEntry] = []
        self._index: dict[str, set[str]] = {}

    def _index_entry(self, entry: PasswordEntry) -> None:
        words = set(entry.site.lower().split()) | set(entry.username.lower().split())
        for word in words:
            if len(word) >= 2:
                self._index.setdefault(word, set()).add(entry.entry_id)

    def _unindex_entry(self, entry: PasswordEntry) -> None:
        words = set(entry.site.lower().split()) | set(entry.username.lower().split())
        for word in words:
            if len(word) >= 2 and word in self._index:
                self._index[word].discard(entry.entry_id)
                if not self._index[word]:
                    del self._index[word]

    def _rebuild_index(self) -> None:
        self._index.clear()
        for entry in self._entries:
            self._index_entry(entry)

    def exists(self) -> bool:
        return self.path.exists()

    def is_unlocked(self) -> bool:
        return self._key is not None

    def _require_unlocked(self) -> None:
        if not self.is_unlocked():
            raise VaultLockedError()

    def _read_raw(self) -> dict:
        with open(self.path, "r", encoding="utf-8") as fh:
            return json.load(fh)

    def _write_raw(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        os.replace(tmp_path, self.path)

    def _compute_hmac(self, key: bytes, payload_token: str) -> str:
        raw_key = base64.urlsafe_b64decode(key)
        h = hmac.new(raw_key, payload_token.encode("utf-8"), hashlib.sha256)
        return base64.b64encode(h.digest()).decode("ascii")

    def _verify_hmac(self, data: dict, key: bytes) -> bool:
        stored_hmac = data.get("hmac")
        if stored_hmac is None:
            return True
        payload = data["payload"]
        computed = self._compute_hmac(key, payload)
        return hmac.compare_digest(computed, stored_hmac)
    
    def create(self, master_password: str) -> None:
        if self.exists():
            raise VaultError("A vault already exists at this location.")

        salt = _new_salt()
        key = _derive_key(master_password, salt)
        fernet = Fernet(key)

        verification_token = fernet.encrypt(VERIFICATION_MARKER).decode("ascii")
        payload_token = fernet.encrypt(json.dumps([]).encode("utf-8")).decode("ascii")
        hmac_token = self._compute_hmac(key, payload_token)

        data = {
            "version": self.FORMAT_VERSION,
            "kdf_iterations": PBKDF2_ITERATIONS,
            "salt": _b64e(salt),
            "verification": verification_token,
            "payload": payload_token,
            "hmac": hmac_token,
            "windows_hello_enabled": False,
            "windows_hello_blob": None,
        }

        with self._lock:
            self._write_raw(data)

        log.info("Created new vault at %s", self.path)

        if WindowsHello.is_available():
            try:
                self._key = key
                self._entries = []
                self._rebuild_index()
                self.enable_windows_hello(skip_prompt=True)
            except Exception:
                log.exception("Could not auto-enable Windows Hello.")
            finally:
                self._key = None
                self._entries = []

    def unlock(self, master_password: str) -> bool:
        if not self.exists():
            raise VaultError("No vault found - call create() first.")

        with self._lock:
            data = self._read_raw()

        salt = _b64d(data["salt"])
        stored_iterations = data.get("kdf_iterations")

        candidates = []
        if stored_iterations is not None:
            candidates.append(stored_iterations)
        candidates.append(PBKDF2_ITERATIONS)
        candidates.append(100000)
        candidates.append(200000)
        candidates.append(300000)
        seen = set()
        candidates = [x for x in candidates if not (x in seen or seen.add(x))]

        for iterations in candidates:
            key = _derive_key(master_password, salt, iterations)
            if self._verify_hmac(data, key) and self._verify_key(data, key):
                self._load_payload(data, key)
                if stored_iterations is None or stored_iterations != PBKDF2_ITERATIONS:
                    log.info("Migrating vault to new iteration count (%d).", PBKDF2_ITERATIONS)
                    with self._lock:
                        data2 = self._read_raw()
                        data2["kdf_iterations"] = PBKDF2_ITERATIONS
                        if data2.get("windows_hello_enabled") and WindowsHello.is_available():
                            blob = WindowsHello.protect_key(self._key)
                            if blob is not None:
                                data2["windows_hello_blob"] = _b64e(blob)
                            else:
                                data2["windows_hello_enabled"] = False
                                data2["windows_hello_blob"] = None
                        fernet = Fernet(self._key)
                        entries_raw = [asdict(e) for e in self._entries]
                        payload_token = fernet.encrypt(json.dumps(entries_raw).encode("utf-8")).decode("ascii")
                        hmac_token = self._compute_hmac(self._key, payload_token)
                        data2["payload"] = payload_token
                        data2["hmac"] = hmac_token

                        self._write_raw(data2)
                    log.info("Migration complete.")

                return True

        log.warning("No candidate iteration count unlocked the vault.")
        return False

    def _verify_key(self, data: dict, key: bytes) -> bool:
        try:
            fernet = Fernet(key)
            plaintext = fernet.decrypt(data["verification"].encode("ascii"))
            return plaintext == VERIFICATION_MARKER
        except (InvalidToken, ValueError, KeyError):
            return False

    def _load_payload(self, data: dict, key: bytes) -> None:
        fernet = Fernet(key)
        raw = fernet.decrypt(data["payload"].encode("ascii"))
        entries_raw = json.loads(raw.decode("utf-8"))
        self._entries = [PasswordEntry(**e) for e in entries_raw]
        self._key = key
        self._rebuild_index()

    def lock(self) -> None:
        self._entries = []
        self._key = None
        self._index.clear()
        gc.collect()
        log.info("Vault locked and memory garbage collected.")

    def wipe(self) -> None:
        self.lock()
        try:
            if self.path.exists():
                self.path.unlink()
            tmp_path = self.path.with_suffix(".tmp")
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            log.exception("Could not delete vault file during security wipe.")
            raise
        log.warning("Vault wiped (file permanently deleted).")
        
    def enable_windows_hello(self, skip_prompt: bool = False) -> bool:
        self._require_unlocked()
        if not WindowsHello.is_available():
            return False
        if not skip_prompt and not WindowsHello.verify_user(
            "Bestätige deine Identität, um Windows Hello für MangoSafe zu aktivieren."
        ):
            return False
        blob = WindowsHello.protect_key(self._key)
        if blob is None:
            return False
        with self._lock:
            data = self._read_raw()
            data["windows_hello_enabled"] = True
            data["windows_hello_blob"] = _b64e(blob)
            self._write_raw(data)
        log.info("Windows Hello enabled for this vault.")
        return True

    def try_windows_hello(self, owner_hwnd: Optional[int] = None) -> bool:
        if not self.exists():
            return False

        with self._lock:
            data = self._read_raw()

        if not data.get("windows_hello_enabled") or not data.get("windows_hello_blob"):
            return False
        if not WindowsHello.verify_user(owner_hwnd=owner_hwnd):
            log.info("Windows Hello prompt was cancelled or failed.")
            return False

        blob = _b64d(data["windows_hello_blob"])
        key = WindowsHello.unprotect_key(blob)
        if key is None:
            log.warning("Windows Hello verified the user, but the key could not be unwrapped.")
            return False

        if not self._verify_key(data, key):
            log.error("Unwrapped Windows Hello key does not match the vault - ignoring.")
            return False
        if not self._verify_hmac(data, key):
            log.warning("HMAC verification failed for Windows Hello key – attempting to repair.")
            with self._lock:
                data2 = self._read_raw()
                payload_token = data2["payload"]
                hmac_token = self._compute_hmac(key, payload_token)
                data2["hmac"] = hmac_token
                self._write_raw(data2)
                data = data2
            log.info("HMAC repaired for Windows Hello key.")

        self._load_payload(data, key)
        log.info("Vault unlocked via Windows Hello (%d entries).", len(self._entries))
        return True

    def disable_windows_hello(self) -> None:
        with self._lock:
            data = self._read_raw()
            data["windows_hello_enabled"] = False
            data["windows_hello_blob"] = None
            self._write_raw(data)
        log.info("Windows Hello disabled for this vault.")

    def is_windows_hello_enabled(self) -> bool:
        if not self.exists():
            return False
        with self._lock:
            data = self._read_raw()
        return bool(data.get("windows_hello_enabled"))
    
    def _persist_entries(self) -> None:
        self._require_unlocked()
        fernet = Fernet(self._key)
        entries_raw = [asdict(e) for e in self._entries]
        payload_token = fernet.encrypt(json.dumps(entries_raw).encode("utf-8")).decode("ascii")
        hmac_token = self._compute_hmac(self._key, payload_token)

        with self._lock:
            data = self._read_raw()
            data["payload"] = payload_token
            data["hmac"] = hmac_token
            self._write_raw(data)
            
    def add_entry(self, site: str, username: str, password: str, notes: str = "") -> PasswordEntry:
        self._require_unlocked()
        entry = PasswordEntry(
            entry_id=secrets.token_hex(8),
            site=site,
            username=username,
            password=password,
            notes=notes,
        )
        self._entries.append(entry)
        self._index_entry(entry)
        self._persist_entries()
        return entry

    def delete_entry(self, entry_id: str) -> bool:
        self._require_unlocked()
        before = len(self._entries)
        for entry in self._entries:
            if entry.entry_id == entry_id:
                self._unindex_entry(entry)
                break
        self._entries = [e for e in self._entries if e.entry_id != entry_id]
        deleted = len(self._entries) != before
        if deleted:
            self._persist_entries()
        return deleted

    def update_entry(self, entry_id: str, **fields) -> bool:
        self._require_unlocked()
        allowed = {"site", "username", "password", "notes", "favorite"}
        unknown = set(fields) - allowed
        if unknown:
            raise VaultError(f"Cannot update unknown fields: {sorted(unknown)}")
        for entry in self._entries:
            if entry.entry_id == entry_id:
                self._unindex_entry(entry)
                for key, value in fields.items():
                    setattr(entry, key, value)
                entry.updated_at = datetime.now().isoformat()
                self._index_entry(entry)
                self._persist_entries()
                return True
        return False

    def get_entry(self, entry_id: str) -> Optional[PasswordEntry]:
        self._require_unlocked()
        for entry in self._entries:
            if entry.entry_id == entry_id:
                return entry
        return None

    def get_all_entries(self) -> list[PasswordEntry]:
        self._require_unlocked()
        return sorted(self._entries, key=lambda e: e.site.lower())

    def search_entries(self, query: str) -> list[PasswordEntry]:
        self._require_unlocked()
        query = query.strip().lower()
        if not query:
            return self.get_all_entries()

        words = query.split()
        matching_ids = None
        for word in words:
            ids = self._index.get(word, set())
            if matching_ids is None:
                matching_ids = ids
            else:
                matching_ids &= ids
            if not matching_ids:
                break

        if matching_ids is None or not matching_ids:
            return []

        results = [e for e in self._entries if e.entry_id in matching_ids]
        results.sort(key=lambda e: (not e.site.lower().startswith(query), e.site.lower()))
        return results

    def change_master_password(self, old_password: str, new_password: str) -> bool:
        if not self.unlock(old_password):
            return False

        was_hello_enabled = self.is_windows_hello_enabled()

        with self._lock:
            data = self._read_raw()

        new_salt = _new_salt()
        new_key = _derive_key(new_password, new_salt)
        fernet = Fernet(new_key)

        verification_token = fernet.encrypt(VERIFICATION_MARKER).decode("ascii")
        entries_raw = [asdict(e) for e in self._entries]
        payload_token = fernet.encrypt(json.dumps(entries_raw).encode("utf-8")).decode("ascii")
        hmac_token = self._compute_hmac(new_key, payload_token)

        data["salt"] = _b64e(new_salt)
        data["kdf_iterations"] = PBKDF2_ITERATIONS
        data["verification"] = verification_token
        data["payload"] = payload_token
        data["hmac"] = hmac_token

        self._key = new_key

        if was_hello_enabled:
            blob = WindowsHello.protect_key(new_key)
            if blob is not None:
                data["windows_hello_enabled"] = True
                data["windows_hello_blob"] = _b64e(blob)
            else:
                data["windows_hello_enabled"] = False
                data["windows_hello_blob"] = None

        with self._lock:
            self._write_raw(data)

        log.info("Master password changed.")
        return True

    def entry_count(self) -> int:
        self._require_unlocked()
        return len(self._entries)

    @contextlib.contextmanager
    def unlocked_session(self, master_password: str):
        ok = self.unlock(master_password)
        try:
            yield ok
        finally:
            if ok:
                self.lock()