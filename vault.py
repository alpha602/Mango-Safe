from __future__ import annotations

import os
import json
import gc
import hmac
import base64
import asyncio
import hashlib
import logging
import secrets
import threading
import importlib
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

log = logging.getLogger("MangoSafe.vault")

PBKDF2_ITERATIONS = 480_000
RECOVERY_KDF_ITERATIONS = 100_000
VERIFICATION_MARKER = b"MangoSafe verification marker v3"


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


class VaultError(Exception):
    pass


class VaultLockedError(VaultError):
    pass


def _new_salt() -> bytes:
    return secrets.token_bytes(16)


def _b64e(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _b64d(data: str) -> bytes:
    return base64.b64decode(data.encode("ascii"))


def _derive_key(password: str, salt: bytes, iterations: int = PBKDF2_ITERATIONS) -> bytes:
    password = password or ""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=iterations,
    )
    raw_key = kdf.derive(password.encode("utf-8"))
    return base64.urlsafe_b64encode(raw_key)


def _new_recovery_token() -> str:
    return secrets.token_urlsafe(32)


def _derive_recovery_wrapping_key(token: str, salt: bytes,
                                  iterations: int = RECOVERY_KDF_ITERATIONS) -> bytes:
    normalized = "".join((token or "").split())
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=iterations,
    )
    raw_key = kdf.derive(normalized.encode("utf-8"))
    return base64.urlsafe_b64encode(raw_key)


# ---------------------------------------------------------------------------
# Windows Hello / DPAPI
# ---------------------------------------------------------------------------

def _ctypes_dpapi_protect(data: bytes) -> Optional[bytes]:
    if os.name != "nt":
        return None
    try:
        import ctypes
        from ctypes import wintypes as _wt

        class _DATA_BLOB(ctypes.Structure):
            _fields_ = [("cbData", _wt.DWORD),
                        ("pbData", ctypes.POINTER(ctypes.c_char))]

        buf = ctypes.create_string_buffer(data, len(data))
        src = _DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
        dst = _DATA_BLOB()
        ok = ctypes.windll.crypt32.CryptProtectData(
            ctypes.byref(src), "MangoSafe vault key",
            None, None, None, 0, ctypes.byref(dst),
        )
        if not ok:
            return None
        out = ctypes.string_at(dst.pbData, dst.cbData)
        ctypes.windll.kernel32.LocalFree(dst.pbData)
        return bytes(out)
    except Exception:
        log.exception("ctypes DPAPI protect failed.")
        return None


def _ctypes_dpapi_unprotect(data: bytes) -> Optional[bytes]:
    if os.name != "nt":
        return None
    try:
        import ctypes
        from ctypes import wintypes as _wt

        class _DATA_BLOB(ctypes.Structure):
            _fields_ = [("cbData", _wt.DWORD),
                        ("pbData", ctypes.POINTER(ctypes.c_char))]

        buf = ctypes.create_string_buffer(data, len(data))
        src = _DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
        dst = _DATA_BLOB()
        ok = ctypes.windll.crypt32.CryptUnprotectData(
            ctypes.byref(src), None, None, None, None, 0, ctypes.byref(dst),
        )
        if not ok:
            return None
        out = ctypes.string_at(dst.pbData, dst.cbData)
        ctypes.windll.kernel32.LocalFree(dst.pbData)
        return bytes(out)
    except Exception:
        log.exception("ctypes DPAPI unprotect failed.")
        return None


_CONSENT_API_CACHE: dict = {}


class WindowsHello:
    """
    Echter Windows-Hello-Dialog (UserConsentVerifier) + DPAPI-Schlüsselbindung.
    """

    @staticmethod
    def _import_consent_api():
        """
        Importiert die WinRT-Consent-API aus allen bekannten Paket-Namensräumen
        (winrt / pywinrt / winsdk) und cachet das Ergebnis.
        """
        if "api" in _CONSENT_API_CACHE:
            return _CONSENT_API_CACHE["api"]
        api = None
        for mod_name in ("winrt.windows.security.credentials.ui",
                         "pywinrt.windows.security.credentials.ui",
                         "winsdk.windows.security.credentials.ui"):
            try:
                mod = importlib.import_module(mod_name)
                api = (mod.UserConsentVerifier, mod.UserConsentVerificationResult)
                break
            except Exception:
                continue
        _CONSENT_API_CACHE["api"] = api
        return api

    @staticmethod
    def is_available() -> bool:
        if os.name != "nt":
            return False
        return WindowsHello._import_consent_api() is not None

    @staticmethod
    def request_user_consent(message: str) -> Optional[bool]:
        """
        Zeigt den echten Windows-Hello-Dialog (PIN / Face / Fingerprint).
        True  = Nutzer erfolgreich verifiziert
        False = Nutzer abgebrochen / abgelehnt
        None  = API nicht verfügbar
        """
        if os.name != "nt":
            return None
        api = WindowsHello._import_consent_api()
        if api is None:
            return None
        UserConsentVerifier, UserConsentVerificationResult = api
        try:
            import ctypes
            ctypes.windll.ole32.CoInitializeEx(None, 0x2)  # STA für WinRT-UI
        except Exception:
            pass
        try:
            async def _run():
                return await UserConsentVerifier.request_verification_async(message)

            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(_run())
            finally:
                loop.close()
            return result == UserConsentVerificationResult.VERIFIED
        except Exception:
            log.exception("Windows Hello consent prompt failed.")
            return None

    @staticmethod
    def protect_key(key: bytes) -> Optional[bytes]:
        blob = _ctypes_dpapi_protect(key)
        if blob is not None:
            return blob
        try:
            import win32crypt
            return bytes(win32crypt.CryptProtectData(
                key, "MangoSafe vault key", None, None, None, 0))
        except Exception:
            return None

    @staticmethod
    def unprotect_key(blob: bytes) -> Optional[bytes]:
        key = _ctypes_dpapi_unprotect(blob)
        if key is not None:
            return key
        try:
            import win32crypt
            _desc, key = win32crypt.CryptUnprotectData(
                blob, None, None, None, None, 0)
            return bytes(key)
        except Exception:
            return None


# ---------------------------------------------------------------------------
# Vault
# ---------------------------------------------------------------------------

class Vault:
    FORMAT_VERSION = 3

    def __init__(self, path: Path):
        self.path = Path(path)
        self._key: Optional[bytes] = None
        self._entries: List[PasswordEntry] = []
        self._index: dict[str, PasswordEntry] = {}
        self._lock = threading.RLock()

    def exists(self) -> bool:
        return self.path.exists()

    def is_unlocked(self) -> bool:
        return self._key is not None

    def _require_unlocked(self) -> None:
        if not self.is_unlocked():
            raise VaultLockedError("Vault is locked.")

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
        digest = hmac.new(raw_key, payload_token.encode("utf-8"), hashlib.sha256).digest()
        return base64.b64encode(digest).decode("ascii")

    def _verify_hmac(self, data: dict, key: bytes) -> bool:
        stored_hmac = data.get("hmac")
        if stored_hmac is None:
            return True
        computed = self._compute_hmac(key, data["payload"])
        return hmac.compare_digest(computed, stored_hmac)

    def _verify_key(self, data: dict, key: bytes) -> bool:
        try:
            fernet = Fernet(key)
            marker = fernet.decrypt(data["verification"].encode("ascii"))
            return marker == VERIFICATION_MARKER
        except Exception:
            return False

    def _wrap_data_key(self, wrapping_key: bytes, data_key: bytes) -> str:
        return Fernet(wrapping_key).encrypt(data_key).decode("ascii")

    def _unwrap_data_key(self, wrapping_key: bytes, blob: Optional[str]) -> Optional[bytes]:
        if not blob:
            return None
        try:
            return Fernet(wrapping_key).decrypt(blob.encode("ascii"))
        except Exception:
            return None

    def _load_payload(self, data: dict, key: bytes) -> None:
        try:
            fernet = Fernet(key)
            raw = fernet.decrypt(data["payload"].encode("ascii"))
            entries_raw = json.loads(raw.decode("utf-8"))
            self._entries = [PasswordEntry(**e) for e in entries_raw]
            self._key = key
            self._rebuild_index()
        except InvalidToken as exc:
            raise VaultError("Invalid master password or corrupted vault.") from exc

    def _rebuild_index(self) -> None:
        self._index = {entry.entry_id: entry for entry in self._entries}

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

    def create(self, master_password: str) -> str:
        if self.exists():
            raise VaultError("A vault already exists at this location.")
        salt = _new_salt()
        password_key = _derive_key(master_password, salt)
        data_key = Fernet.generate_key()
        recovery_token = _new_recovery_token()
        recovery_salt = _new_salt()
        recovery_key = _derive_recovery_wrapping_key(recovery_token, recovery_salt)
        fernet = Fernet(data_key)
        verification_token = fernet.encrypt(VERIFICATION_MARKER).decode("ascii")
        payload_token = fernet.encrypt(json.dumps([]).encode("utf-8")).decode("ascii")
        hmac_token = self._compute_hmac(data_key, payload_token)
        data = {
            "version": self.FORMAT_VERSION,
            "kdf_iterations": PBKDF2_ITERATIONS,
            "salt": _b64e(salt),
            "password_blob": self._wrap_data_key(password_key, data_key),
            "recovery_enabled": True,
            "recovery_salt": _b64e(recovery_salt),
            "recovery_blob": self._wrap_data_key(recovery_key, data_key),
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
                self._key = data_key
                self._entries = []
                self._rebuild_index()
                self.enable_windows_hello(skip_prompt=True)
            except Exception:
                log.exception("Could not auto-enable Windows Hello.")
            finally:
                self._key = None
                self._entries = []
                self._index.clear()
        return recovery_token

    def _migrate_v2_to_v3(self, data: dict, old_key: bytes) -> None:
        data_key = Fernet.generate_key()
        fernet = Fernet(data_key)
        entries_raw = [asdict(e) for e in self._entries]
        payload_token = fernet.encrypt(json.dumps(entries_raw).encode("utf-8")).decode("ascii")
        hmac_token = self._compute_hmac(data_key, payload_token)
        verification_token = fernet.encrypt(VERIFICATION_MARKER).decode("ascii")
        new_data = {
            "version": self.FORMAT_VERSION,
            "kdf_iterations": PBKDF2_ITERATIONS,
            "salt": data.get("salt"),
            "password_blob": self._wrap_data_key(old_key, data_key),
            "recovery_enabled": False,
            "recovery_salt": None,
            "recovery_blob": None,
            "verification": verification_token,
            "payload": payload_token,
            "hmac": hmac_token,
            "windows_hello_enabled": False,
            "windows_hello_blob": None,
        }
        if data.get("windows_hello_enabled") and WindowsHello.is_available():
            blob = WindowsHello.protect_key(data_key)
            if blob is not None:
                new_data["windows_hello_enabled"] = True
                new_data["windows_hello_blob"] = _b64e(blob)
        with self._lock:
            self._write_raw(new_data)
        self._key = data_key

    def unlock(self, master_password: str) -> bool:
        if not self.exists():
            raise VaultError("No vault found - call create() first.")
        with self._lock:
            data = self._read_raw()
        version = int(data.get("version", 2))
        salt = _b64d(data["salt"])
        candidates = []
        stored = data.get("kdf_iterations")
        if stored is not None:
            candidates.append(int(stored))
        candidates.extend([PBKDF2_ITERATIONS, 300_000, 200_000, 100_000])
        seen = set()
        candidates = [c for c in candidates if not (c in seen or seen.add(c))]
        for iterations in candidates:
            password_key = _derive_key(master_password, salt, iterations)
            if version >= 3:
                data_key = self._unwrap_data_key(password_key, data.get("password_blob"))
                if data_key is None:
                    continue
                if not self._verify_key(data, data_key):
                    continue
                if not self._verify_hmac(data, data_key):
                    continue
                self._load_payload(data, data_key)
                return True
            else:
                if self._verify_hmac(data, password_key) and self._verify_key(data, password_key):
                    self._load_payload(data, password_key)
                    self._migrate_v2_to_v3(data, password_key)
                    return True
        log.warning("Failed to unlock vault.")
        return False

    def unlock_with_windows_hello(self) -> bool:
        if not self.exists() or not WindowsHello.is_available():
            return False
        with self._lock:
            data = self._read_raw()
        if not data.get("windows_hello_enabled"):
            return False
        blob_b64 = data.get("windows_hello_blob")
        if not blob_b64:
            return False
        data_key = WindowsHello.unprotect_key(_b64d(blob_b64))
        if not data_key:
            return False
        if not self._verify_key(data, data_key):
            return False
        if not self._verify_hmac(data, data_key):
            return False
        self._load_payload(data, data_key)
        return True

    def lock(self) -> None:
        self._entries = []
        self._key = None
        self._index.clear()
        gc.collect()
        log.info("Vault locked.")

    def wipe(self) -> None:
        self.lock()
        try:
            if self.path.exists():
                self.path.unlink()
            tmp_path = self.path.with_suffix(".tmp")
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            log.exception("Could not wipe vault.")

    def has_recovery_key(self) -> bool:
        if not self.exists():
            return False
        with self._lock:
            data = self._read_raw()
        return bool(data.get("recovery_enabled")
                    and data.get("recovery_salt")
                    and data.get("recovery_blob"))

    def create_recovery_key(self) -> Optional[str]:
        self._require_unlocked()
        with self._lock:
            data = self._read_raw()
        token = _new_recovery_token()
        salt = _new_salt()
        wrapping_key = _derive_recovery_wrapping_key(token, salt)
        data["version"] = self.FORMAT_VERSION
        data["recovery_enabled"] = True
        data["recovery_salt"] = _b64e(salt)
        data["recovery_blob"] = self._wrap_data_key(wrapping_key, self._key)
        with self._lock:
            self._write_raw(data)
        return token

    def reset_master_password(self, recovery_token: str, new_master_password: str) -> bool:
        if not self.exists():
            return False
        with self._lock:
            data = self._read_raw()
        if int(data.get("version", 2)) < 3:
            return False
        if not data.get("recovery_enabled"):
            return False
        recovery_salt = _b64d(data["recovery_salt"])
        recovery_key = _derive_recovery_wrapping_key(recovery_token, recovery_salt)
        data_key = self._unwrap_data_key(recovery_key, data.get("recovery_blob"))
        if data_key is None:
            return False
        if not self._verify_key(data, data_key):
            return False
        if not self._verify_hmac(data, data_key):
            return False
        new_salt = _new_salt()
        new_password_key = _derive_key(new_master_password, new_salt)
        data["salt"] = _b64e(new_salt)
        data["kdf_iterations"] = PBKDF2_ITERATIONS
        data["password_blob"] = self._wrap_data_key(new_password_key, data_key)
        if data.get("windows_hello_enabled") and WindowsHello.is_available():
            blob = WindowsHello.protect_key(data_key)
            if blob is not None:
                data["windows_hello_enabled"] = True
                data["windows_hello_blob"] = _b64e(blob)
            else:
                data["windows_hello_enabled"] = False
                data["windows_hello_blob"] = None
        with self._lock:
            self._write_raw(data)
        return True

    def is_windows_hello_enabled(self) -> bool:
        if not self.exists():
            return False
        with self._lock:
            data = self._read_raw()
        return bool(data.get("windows_hello_enabled"))

    def enable_windows_hello(self, skip_prompt: bool = False) -> bool:
        self._require_unlocked()
        if not WindowsHello.is_available():
            return False
        blob = WindowsHello.protect_key(self._key)
        if blob is None:
            return False
        with self._lock:
            data = self._read_raw()
            data["windows_hello_enabled"] = True
            data["windows_hello_blob"] = _b64e(blob)
            self._write_raw(data)
        log.info("Windows Hello enabled.")
        return True

    def disable_windows_hello(self) -> None:
        if not self.exists():
            return
        with self._lock:
            data = self._read_raw()
            data["windows_hello_enabled"] = False
            data["windows_hello_blob"] = None
            self._write_raw(data)
        log.info("Windows Hello disabled.")

    def list_entries(self) -> List[PasswordEntry]:
        self._require_unlocked()
        return list(self._entries)

    def get_all_entries(self) -> List[PasswordEntry]:
        return self.list_entries()

    def search_entries(self, query: str) -> List[PasswordEntry]:
        self._require_unlocked()
        q = (query or "").strip().lower()
        if not q:
            return list(self._entries)
        return [e for e in self._entries
                if q in e.site.lower() or q in e.username.lower()]

    def add_entry(self, site: str, username: str, password: str,
                  notes: str = "", favorite: bool = False) -> PasswordEntry:
        self._require_unlocked()
        now = datetime.now().isoformat()
        entry = PasswordEntry(
            entry_id=secrets.token_hex(16),
            site=site.strip(),
            username=username.strip(),
            password=password,
            notes=notes.strip(),
            favorite=bool(favorite),
            created_at=now,
            updated_at=now,
        )
        self._entries.append(entry)
        self._rebuild_index()
        self._persist_entries()
        return entry

    def update_entry(self, entry_id: str, site: str = None, username: str = None,
                     password: str = None, notes: str = None,
                     favorite: Optional[bool] = None) -> PasswordEntry:
        self._require_unlocked()
        if entry_id not in self._index:
            raise VaultError("Entry not found.")
        entry = self._index[entry_id]
        if site is not None:
            entry.site = site.strip()
        if username is not None:
            entry.username = username.strip()
        if password is not None:
            entry.password = password
        if notes is not None:
            entry.notes = notes.strip()
        if favorite is not None:
            entry.favorite = bool(favorite)
        entry.updated_at = datetime.now().isoformat()
        self._persist_entries()
        return entry

    def delete_entry(self, entry_id: str) -> None:
        self._require_unlocked()
        self._entries = [e for e in self._entries if e.entry_id != entry_id]
        self._rebuild_index()
        self._persist_entries()

    def change_master_password(self, old_password: str, new_password: str) -> bool:
        if not self.unlock(old_password):
            return False
        with self._lock:
            data = self._read_raw()
        new_salt = _new_salt()
        new_password_key = _derive_key(new_password, new_salt)
        data["version"] = self.FORMAT_VERSION
        data["salt"] = _b64e(new_salt)
        data["kdf_iterations"] = PBKDF2_ITERATIONS
        data["password_blob"] = self._wrap_data_key(new_password_key, self._key)
        if data.get("windows_hello_enabled") and WindowsHello.is_available():
            blob = WindowsHello.protect_key(self._key)
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
