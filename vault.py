from __future__ import annotations

import os
import json
import gc
import hmac
import base64
import hashlib
import logging
import secrets
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


log = logging.getLogger("MangoSafe.vault")

PBKDF2_ITERATIONS = 300_000
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


def _derive_recovery_wrapping_key(
    token: str,
    salt: bytes,
    iterations: int = RECOVERY_KDF_ITERATIONS,
) -> bytes:
    normalized = "".join((token or "").split())
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=iterations,
    )
    raw_key = kdf.derive(normalized.encode("utf-8"))
    return base64.urlsafe_b64encode(raw_key)


class WindowsHello:
    """
    Technisch nutzt das hier Windows DPAPI.
    Das ist kein echter Windows-Hello-Biometrie-Zwang, aber die Daten werden
    an den aktuellen Windows-Benutzer gebunden.
    """

    @staticmethod
    def is_available() -> bool:
        if os.name != "nt":
            return False
        try:
            import win32crypt  # noqa: F401
            return True
        except Exception:
            return False

    @staticmethod
    def protect_key(key: bytes) -> Optional[bytes]:
        if not WindowsHello.is_available():
            return None
        try:
            import win32crypt

            blob = win32crypt.CryptProtectData(
                key,
                "MangoSafe vault key",
                None,
                None,
                None,
                0,
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

            description, key = win32crypt.CryptUnprotectData(
                blob,
                None,
                None,
                None,
                0,
            )
            return bytes(key)
        except Exception:
            log.exception("DPAPI unprotect failed.")
            return None


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
        digest = hmac.new(
            raw_key,
            payload_token.encode("utf-8"),
            hashlib.sha256,
        ).digest()
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
        payload_token = fernet.encrypt(
            json.dumps(entries_raw).encode("utf-8")
        ).decode("ascii")
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
        payload_token = fernet.encrypt(
            json.dumps(entries_raw).encode("utf-8")
        ).decode("ascii")
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
        stored_iterations = data.get("kdf_iterations")

        candidates = []
        if stored_iterations is not None:
            candidates.append(stored_iterations)
        candidates.extend([PBKDF2_ITERATIONS, 100_000, 200_000, 300_000])

        seen = set()
        candidates = [x for x in candidates if not (x in seen or seen.add(x))]

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
        return bool(
            data.get("recovery_enabled")
            and data.get("recovery_salt")
            and data.get("recovery_blob")
        )

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

    def add_entry(
        self,
        site: str,
        username: str,
        password: str,
        notes: str = "",
        favorite: bool = False,
    ) -> PasswordEntry:
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

    def update_entry(
        self,
        entry_id: str,
        site: str,
        username: str,
        password: str,
        notes: str = "",
        favorite: bool = False,
    ) -> PasswordEntry:
        self._require_unlocked()

        if entry_id not in self._index:
            raise VaultError("Entry not found.")

        entry = self._index[entry_id]
        entry.site = site.strip()
        entry.username = username.strip()
        entry.password = password
        entry.notes = notes.strip()
        entry.favorite = bool(favorite)
        entry.updated_at = datetime.now().isoformat()

        self._persist_entries()
        return entry

    def delete_entry(self, entry_id: str) -> None:
        self._require_unlocked()

        self._entries = [entry for entry in self._entries if entry.entry_id != entry_id]
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