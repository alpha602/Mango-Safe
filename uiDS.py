from __future__ import annotations

import io
import os
import sys
import secrets
import hashlib
import logging
import string
import urllib.request
import concurrent.futures
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
from typing import Callable, Optional, TYPE_CHECKING

import customtkinter as ctk

from vault import WindowsHello

if TYPE_CHECKING:
    from main import MangoSafeApp, PasswordEntry

try:
    from PIL import Image, ImageDraw, ImageFont
    _PIL_OK = True
except ImportError:
    _PIL_OK = False

log = logging.getLogger("MangoSafe.ui")

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# ---------------------------------------------------------------------------
# Design-System
# ---------------------------------------------------------------------------

THEMES = {
    "dark": {
        "bg": "#0B0D12",
        "sidebar": "#10131A",
        "card": "#151A23",
        "card_hover": "#1D2432",
        "border": "#242B3A",
        "input": "#0E1219",
        "text": "#F4F6FB",
        "text_dim": "#8B93A7",
    },
    "light": {
        "bg": "#D2B773",
        "sidebar": "#DBC284",
        "card": "#E2CD93",
        "card_hover": "#C9AE69",
        "border": "#B49A57",
        "input": "#EAD9A6",
        "text": "#800000",
        "text_dim": "#945050",
    },
}

COL_BG = THEMES["dark"]["bg"]
COL_SIDEBAR = THEMES["dark"]["sidebar"]
COL_CARD = THEMES["dark"]["card"]
COL_CARD_HOVER = THEMES["dark"]["card_hover"]
COL_BORDER = THEMES["dark"]["border"]
COL_INPUT = THEMES["dark"]["input"]
COL_TEXT = THEMES["dark"]["text"]
COL_TEXT_DIM = THEMES["dark"]["text_dim"]

COL_DANGER = "#F0564A"
COL_DANGER_HOVER = "#D64539"
COL_SUCCESS = "#22C55E"
COL_WARN = "#F59E0B"


def apply_theme(mode: str) -> None:
    global COL_BG, COL_SIDEBAR, COL_CARD, COL_CARD_HOVER, COL_BORDER
    global COL_INPUT, COL_TEXT, COL_TEXT_DIM
    palette = THEMES.get(mode, THEMES["dark"])
    COL_BG = palette["bg"]
    COL_SIDEBAR = palette["sidebar"]
    COL_CARD = palette["card"]
    COL_CARD_HOVER = palette["card_hover"]
    COL_BORDER = palette["border"]
    COL_INPUT = palette["input"]
    COL_TEXT = palette["text"]
    COL_TEXT_DIM = palette["text_dim"]
    ctk.set_appearance_mode("light" if mode == "light" else "dark")


def _hex_mix(a: str, b: str, t: float) -> str:
    ar, ag, ab = (int(a[i:i + 2], 16) for i in (1, 3, 5))
    br, bg, bb = (int(b[i:i + 2], 16) for i in (1, 3, 5))
    r = round(ar + (br - ar) * t)
    g = round(ag + (bg - ag) * t)
    bl = round(ab + (bb - ab) * t)
    return f"#{r:02X}{g:02X}{bl:02X}"


ACCENT_PALETTE = {
    "purple": "#8B5CF6",
    "blue": "#3E8BFF",
    "green": "#22C55E",
    "red": "#EF4444",
    "orange": "#F59E0B",
    "pink": "#EC4899",
    "teal": "#14B8A6",
    "yellow": "#EAB308",
    "indigo": "#6366F1",
    "rose": "#F43F5E",
}

ACCENT_HOVER = {
    "purple": "#7C4DEB",
    "blue": "#2F7AEF",
    "green": "#16A34A",
    "red": "#DC2626",
    "orange": "#D97706",
    "pink": "#DB2777",
    "teal": "#0D9488",
    "yellow": "#CA8A04",
    "indigo": "#4F46E5",
    "rose": "#E11D48",
}

ACCENT_GRADIENT = {
    "purple": "#EC4899",
    "blue": "#22D3EE",
    "green": "#A3E635",
    "red": "#F97316",
    "orange": "#EF4444",
    "pink": "#8B5CF6",
    "teal": "#3E8BFF",
    "yellow": "#22C55E",
    "indigo": "#3E8BFF",
    "rose": "#F59E0B",
}

FONT_LOGO = ("Segoe UI", 19, "bold")
FONT_TITLE = ("Segoe UI", 22, "bold")
FONT_SECTION = ("Segoe UI", 15, "bold")
FONT_SITE = ("Segoe UI", 15, "bold")
FONT_BODY = ("Segoe UI", 14)
FONT_LABEL = ("Segoe UI", 13)
FONT_SMALL = ("Segoe UI", 12)
FONT_NAV = ("Segoe UI", 14, "bold")
FONT_MONO = ("Consolas", 13)

WINDOW_SIZE = "1160x780"
SIDEBAR_WIDTH = 264
AVATAR_SIZE = 44
ICON_PIXELS = 44

_ICON_EXECUTOR = concurrent.futures.ThreadPoolExecutor(
    max_workers=4, thread_name_prefix="mangosafe-icon")

KNOWN_BRANDS = {
    "discord": {"domain": "discord.com", "color": "#5865F2", "letter": "D"},
    "steam": {"domain": "steampowered.com", "color": "#1B2838", "letter": "S"},
    "epicgames": {"domain": "epicgames.com", "color": "#313131", "letter": "E"},
    "riotgames": {"domain": "riotgames.com", "color": "#D13639", "letter": "R"},
    "blizzard": {"domain": "blizzard.com", "color": "#00AEFF", "letter": "B"},
    "ubisoft": {"domain": "ubisoft.com", "color": "#000000", "letter": "U"},
    "ea": {"domain": "ea.com", "color": "#FF0000", "letter": "E"},
    "rockstargames": {"domain": "rockstargames.com", "color": "#FCAF17", "letter": "R"},
    "nintendo": {"domain": "nintendo.com", "color": "#E60012", "letter": "N"},
    "playstation": {"domain": "playstation.com", "color": "#003791", "letter": "P"},
    "xbox": {"domain": "x.com", "color": "#107C10", "letter": "X"},
    "spotify": {"domain": "spotify.com", "color": "#1DB954", "letter": "S"},
    "github": {"domain": "github.com", "color": "#181717", "letter": "G"},
    "gitlab": {"domain": "gitlab.com", "color": "#FC6D26", "letter": "G"},
    "bitbucket": {"domain": "bitbucket.org", "color": "#0052CC", "letter": "B"},
    "stackoverflow": {"domain": "stackoverflow.com", "color": "#F48024", "letter": "S"},
    "leetcode": {"domain": "leetcode.com", "color": "#FFA116", "letter": "L"},
    "openai": {"domain": "openai.com", "color": "#10A37F", "letter": "O"},
    "anthropic": {"domain": "anthropic.com", "color": "#4F46E5", "letter": "A"},
    "huggingface": {"domain": "huggingface.co", "color": "#FFD21E", "letter": "H"},
    "apple": {"domain": "apple.com", "color": "#A2AAAD", "letter": "A"},
    "tiktok": {"domain": "tiktok.com", "color": "#000000", "letter": "T"},
    "google": {"domain": "google.com", "color": "#4285F4", "letter": "G"},
    "snapchat": {"domain": "snapchat.com", "color": "#FFFC00", "letter": "S"},
    "pinterest": {"domain": "pinterest.com", "color": "#E60023", "letter": "P"},
    "tumblr": {"domain": "tumblr.com", "color": "#36465D", "letter": "T"},
    "reddit": {"domain": "reddit.com", "color": "#FF4500", "letter": "R"},
    "quora": {"domain": "quora.com", "color": "#B92B27", "letter": "Q"},
    "telegram": {"domain": "telegram.org", "color": "#26A5E4", "letter": "T"},
    "paypal": {"domain": "paypal.com", "color": "#003087", "letter": "P"},
    "stripe": {"domain": "stripe.com", "color": "#008CDD", "letter": "S"},
    "revolut": {"domain": "revolut.com", "color": "#0077B6", "letter": "R"},
    "klarna": {"domain": "klarna.com", "color": "#FFB3C7", "letter": "K"},
    "n26": {"domain": "n26.com", "color": "#00A3BE", "letter": "N"},
    "wise": {"domain": "wise.com", "color": "#00B9B9", "letter": "W"},
    "coinbase": {"domain": "coinbase.com", "color": "#0052FF", "letter": "C"},
    "binance": {"domain": "binance.com", "color": "#F0B90B", "letter": "B"},
    "kraken": {"domain": "kraken.com", "color": "#1856B4", "letter": "K"},
    "dropbox": {"domain": "dropbox.com", "color": "#0061FF", "letter": "D"},
    "icloud": {"domain": "icloud.com", "color": "#3693F3", "letter": "I"},
    "mega": {"domain": "mega.nz", "color": "#D9000F", "letter": "M"},
    "netflix": {"domain": "netflix.com", "color": "#E50914", "letter": "N"},
    "disneyplus": {"domain": "disneyplus.com", "color": "#113CCF", "letter": "D"},
    "primevideo": {"domain": "amazon.com", "color": "#00A8E1", "letter": "P"},
    "crunchyroll": {"domain": "crunchyroll.com", "color": "#F47521", "letter": "C"},
    "twitch": {"domain": "twitch.tv", "color": "#9146FF", "letter": "T"},
    "amazon": {"domain": "amazon.com", "color": "#FF9900", "letter": "A"},
    "ebay": {"domain": "ebay.com", "color": "#E53238", "letter": "E"},
    "etsy": {"domain": "etsy.com", "color": "#F16522", "letter": "E"},
    "aliexpress": {"domain": "aliexpress.com", "color": "#FF4747", "letter": "A"},
    "zalando": {"domain": "zalando.com", "color": "#E40046", "letter": "Z"},
    "booking": {"domain": "booking.com", "color": "#003580", "letter": "B"},
    "airbnb": {"domain": "airbnb.com", "color": "#FF5A5F", "letter": "A"},
    "notion": {"domain": "notion.so", "color": "#000000", "letter": "N"},
    "trello": {"domain": "trello.com", "color": "#0052CC", "letter": "T"},
    "asana": {"domain": "asana.com", "color": "#F06A6A", "letter": "A"},
    "monday": {"domain": "monday.com", "color": "#FF5252", "letter": "M"},
    "slack": {"domain": "slack.com", "color": "#4A154B", "letter": "S"},
    "teams": {"domain": "microsoft.com", "color": "#6264A7", "letter": "T"},
    "zoom": {"domain": "zoom.us", "color": "#2D8CFF", "letter": "Z"},
    "youtube": {"domain": "youtube.com", "color": "#FF0000", "letter": "Y"},
    "facebook": {"domain": "facebook.com", "color": "#1877F2", "letter": "F"},
    "instagram": {"domain": "instagram.com", "color": "#E4405F", "letter": "I"},
    "twitter": {"domain": "x.com", "color": "#000000", "letter": "X"},
    "linkedin": {"domain": "linkedin.com", "color": "#0A66C2", "letter": "L"},
    "whatsapp": {"domain": "whatsapp.com", "color": "#25D366", "letter": "W"},
}

HASH_COLORS = ["#4C6EF5", "#12B886", "#F76707", "#E64980", "#7048E8", "#15AABF", "#F59F00"]


def _brand_for_site(site: str) -> tuple[str, str]:
    key = site.strip().lower()
    for needle, info in KNOWN_BRANDS.items():
        if needle in key:
            return info["color"], info["letter"]
    color = HASH_COLORS[int(hashlib.sha1(key.encode("utf-8")).hexdigest(), 16) % len(HASH_COLORS)]
    letter = (site.strip()[:1] or "?").upper()
    return color, letter


def _domain_for_site(site: str) -> Optional[str]:
    key = site.strip().lower()
    for needle, info in KNOWN_BRANDS.items():
        if needle in key:
            return info["domain"]
    if "." in key and " " not in key and "/" not in key.split(".", 1)[0]:
        return key.replace("https://", "").replace("http://", "").split("/")[0]
    return None


def _icon_cache_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home())) / "MangoSafe"
    else:
        base = Path.home() / ".mangosafe"
    d = base / "icons_v2"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _favicon_urls(domain: str) -> list[str]:
    return [
        f"https://icons.duckduckgo.com/ip3/{domain}.ico",
        f"https://www.google.com/s2/favicons?sz=128&domain={domain}",
    ]


def _download_icon(domain: str):
    if not _PIL_OK:
        return None
    cache_path = _icon_cache_dir() / f"{domain}.png"
    try:
        if cache_path.exists() and cache_path.stat().st_size > 0:
            data = cache_path.read_bytes()
        else:
            data = None
        if data is None:
            for url in _favicon_urls(domain):
                try:
                    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                    fetched = urllib.request.urlopen(req, timeout=3).read()
                    if fetched and len(fetched) > 200:
                        data = fetched
                        break
                except Exception:
                    continue
        if data is None:
            return None
        cache_path.write_bytes(data)
        source = Image.open(io.BytesIO(data)).convert("RGBA")
        target = ICON_PIXELS
        native = max(source.size)
        draw_size = max(1, min(target, native * 2))
        resized = source.resize((draw_size, draw_size), Image.LANCZOS)
        canvas_img = Image.new("RGBA", (target, target), (0, 0, 0, 0))
        offset = ((target - draw_size) // 2, (target - draw_size) // 2)
        canvas_img.paste(resized, offset, resized)
        return ctk.CTkImage(light_image=canvas_img, dark_image=canvas_img, size=(target, target))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Lokale Statik-Icons aus dem Ordner "ICONS" (neben main.py / neben der EXE)
# ---------------------------------------------------------------------------

_STATIC_ICON_CACHE: dict[str, Optional[ctk.CTkImage]] = {}


def _icon_search_dirs() -> list[Path]:
    dirs: list[Path] = []
    candidates: list[Path] = []
    try:
        if getattr(sys, "frozen", False):
            candidates.append(Path(sys.executable).resolve().parent)
            meipass = getattr(sys, "_MEIPASS", None)
            if meipass:
                candidates.append(Path(meipass))
        candidates.append(Path(__file__).resolve().parent)
        candidates.append(Path.cwd())
    except Exception:
        pass
    for base in candidates:
        d = base / "ICONS"
        if d not in dirs:
            dirs.append(d)
    return dirs


def load_static_icon(name: str, size: int) -> Optional[ctk.CTkImage]:
    """Lädt <name>.png aus dem ICONS-Ordner und skaliert es auf size x size."""
    if not _PIL_OK:
        return None
    cache_key = f"{name}@{size}"
    if cache_key in _STATIC_ICON_CACHE:
        return _STATIC_ICON_CACHE[cache_key]
    img: Optional[ctk.CTkImage] = None
    for d in _icon_search_dirs():
        for ext in (".png", ".PNG", ".ico", ".jpg", ".jpeg", ".webp"):
            path = d / f"{name}{ext}"
            if path.exists():
                try:
                    src = Image.open(path).convert("RGBA")
                    src = src.resize((size, size), Image.LANCZOS)
                    img = ctk.CTkImage(light_image=src, dark_image=src, size=(size, size))
                except Exception:
                    img = None
                break
        if img is not None:
            break
    _STATIC_ICON_CACHE[cache_key] = img
    return img


# ---------------------------------------------------------------------------
# Übersetzungen
# ---------------------------------------------------------------------------

TR = {
    "de": {
        "app_name_a": "Mango", "app_name_b": "Safe",
        "all_entries": "Alle Einträge", "favorites": "Favoriten", "settings": "Einstellungen",
        "lock_now": "Sperren",
        "local_secure_title": "100% lokal & sicher",
        "local_secure_body": "Deine Daten bleiben nur auf deinem Gerät.",
        "search_placeholder": "Suchen...",
        "found_results": "Gefundene Ergebnisse: ",
        "no_entries": "Noch keine Einträge gespeichert.",
        "no_favorites": "Noch keine Favoriten.",
        "no_matches": "Keine Treffer für '{q}'.",
        "new_entry": "Neuer Eintrag", "edit_entry": "Eintrag bearbeiten",
        "site_placeholder": "Website / Programm...",
        "user_placeholder": "Benutzername / E-Mail...",
        "pw_placeholder": "Passwort...",
        "notes_placeholder": "Notizen (optional)...",
        "cancel": "Abbrechen", "save": "Speichern",
        "favorite_on": "Favorisieren", "favorite_off": "Favorit entfernen",
        "edit": "Bearbeiten", "delete": "Löschen",
        "delete_confirm_title": "Eintrag löschen",
        "delete_confirm_body": "'{site}' wirklich endgültig löschen?",
        "saved_toast": "'{site}' gespeichert.",
        "deleted_toast": "Eintrag gelöscht.",
        "copied_toast": "Passwort für '{site}' kopiert.",
        "welcome": "Willkommen bei MangoSafe",
        "setup_hint": "Lege ein Master-Passwort fest (mind. 8 Zeichen).",
        "master_pw_placeholder": "Master-Passwort...",
        "create_vault": "Tresor erstellen",
        "login_pin_placeholder": "PIN oder Passwort...",
        "unlock": "Entsperren",
        "windows_hello": "🔑  Mit Windows Hello entsperren",
        "forgot_password": "Master-Passwort vergessen?",
        "language": "Sprache", "design_color": "Design-Farbe",
        "appearance": "Erscheinungsbild", "mode_dark": "Dunkel", "mode_light": "Hell",
        "lang_de": "Deutsch", "lang_en": "Englisch", "lang_ru": "Russisch",
        "section_appearance": "Sprache & Erscheinungsbild",
        "section_security": "Sicherheit",
        "error_site_required": "Bitte einen Website-/Programmnamen angeben.",
        "error_password_required": "Bitte ein Passwort angeben.",
        "auto_lock": "Auto-Sperre (Minuten)",
        "windows_hello_label": "Windows Hello verwenden",
        "password_strength": "Passwortstärke",
        "weak": "Schwach", "medium": "Mittel", "strong": "Stark",
        "windows_hello_disabled": "Windows Hello ist in den Einstellungen deaktiviert.",
        "error_master_password_too_short": "Bitte ein Master-Passwort mit mindestens 8 Zeichen wählen.",
        "recovery_title": "Dein Recovery-Key",
        "recovery_hint": "Speichere diesen Schlüssel sicher. Ohne ihn ist kein Zurücksetzen des Master-Passworts möglich.",
        "recovery_copy": "Kopieren",
        "recovery_saved": "Ich habe den Recovery-Key sicher gespeichert",
        "continue": "Weiter",
        "recovery_copied": "Recovery-Key kopiert.",
        "reset_title": "Master-Passwort zurücksetzen",
        "recovery_key_placeholder": "Recovery-Key...",
        "new_master_pw_placeholder": "Neues Master-Passwort...",
        "confirm_master_pw_placeholder": "Neues Master-Passwort bestätigen...",
        "reset_button": "Zurücksetzen",
        "back_to_login": "Zurück zum Login",
        "error_recovery_required": "Bitte einen Recovery-Key eingeben.",
        "error_recovery_invalid": "Recovery-Key ungültig.",
        "error_password_mismatch": "Die Passwörter stimmen nicht überein.",
        "no_recovery_key": "Für diesen Tresor wurde kein Recovery-Key hinterlegt.",
        "recovery_key_settings": "Recovery-Key",
        "create_recovery_key": "Recovery-Key erstellen / erneuern",
        "error_recovery_create_failed": "Recovery-Key konnte nicht erstellt werden.",
        "change_master_pw": "Master-Passwort ändern",
        "old_master_pw": "Altes Master-Passwort...",
        "new_master_pw": "Neues Master-Passwort...",
        "confirm_master_pw": "Neues Master-Passwort bestätigen...",
        "master_password_changed": "Master-Passwort geändert.",
        "error_old_password_wrong": "Altes Master-Passwort ist falsch.",
        "error_wrong_password": "Falsches Passwort oder PIN.",
        "error_empty_password": "Bitte Passwort oder PIN eingeben.",
        "windows_hello_failed": "Windows Hello fehlgeschlagen. Bitte PIN/Passwort eingeben.",
        "windows_hello_cancelled": "Windows Hello abgebrochen. Bitte PIN/Passwort eingeben.",
        "windows_hello_unavailable": "Windows-Hello-Dialog nicht verfügbar. Bitte PIN/Passwort eingeben.",
        "windows_hello_consent_msg": "MangoSafe entsperren – bitte mit Windows Hello bestätigen.",
        "error_wiped": "Zu viele Fehlversuche. Tresor wurde sicher gelöscht.",
        "lockout_msg": "Zu viele Fehlversuche. Bitte {s} s warten.",
        "error_vault_create": "Tresor konnte nicht erstellt werden: {exc}",
        "error_save_failed": "Speichern fehlgeschlagen: {exc}",
        "error_delete_failed": "Löschen fehlgeschlagen: {exc}",
    },
    "en": {
        "app_name_a": "Mango", "app_name_b": "Safe",
        "all_entries": "All Entries", "favorites": "Favorites", "settings": "Settings",
        "lock_now": "Lock",
        "local_secure_title": "100% local & secure",
        "local_secure_body": "Your data stays only on your device.",
        "search_placeholder": "Search...",
        "found_results": "Results found: ",
        "no_entries": "No entries saved yet.",
        "no_favorites": "No favorites yet.",
        "no_matches": "No matches for '{q}'.",
        "new_entry": "New Entry", "edit_entry": "Edit Entry",
        "site_placeholder": "Website / program...",
        "user_placeholder": "Username / email...",
        "pw_placeholder": "Password...",
        "notes_placeholder": "Notes (optional)...",
        "cancel": "Cancel", "save": "Save",
        "favorite_on": "Add to favorites", "favorite_off": "Remove favorite",
        "edit": "Edit", "delete": "Delete",
        "delete_confirm_title": "Delete entry",
        "delete_confirm_body": "Really delete '{site}' permanently?",
        "saved_toast": "'{site}' saved.",
        "deleted_toast": "Entry deleted.",
        "copied_toast": "Password for '{site}' copied.",
        "welcome": "Welcome to MangoSafe",
        "setup_hint": "Create a master password (at least 8 characters).",
        "master_pw_placeholder": "Master password...",
        "create_vault": "Create vault",
        "login_pin_placeholder": "PIN or password...",
        "unlock": "Unlock",
        "windows_hello": "🔑  Unlock with Windows Hello",
        "forgot_password": "Forgot master password?",
        "language": "Language", "design_color": "Accent color",
        "appearance": "Appearance", "mode_dark": "Dark", "mode_light": "Light",
        "lang_de": "German", "lang_en": "English", "lang_ru": "Russian",
        "section_appearance": "Language & appearance",
        "section_security": "Security",
        "error_site_required": "Please enter a website/program name.",
        "error_password_required": "Please enter a password.",
        "auto_lock": "Auto-lock (minutes)",
        "windows_hello_label": "Use Windows Hello",
        "password_strength": "Password strength",
        "weak": "Weak", "medium": "Medium", "strong": "Strong",
        "windows_hello_disabled": "Windows Hello is disabled in the settings.",
        "error_master_password_too_short": "Please choose a master password with at least 8 characters.",
        "recovery_title": "Your recovery key",
        "recovery_hint": "Store this key safely. Without it, the master password cannot be reset.",
        "recovery_copy": "Copy",
        "recovery_saved": "I have stored the recovery key safely",
        "continue": "Continue",
        "recovery_copied": "Recovery key copied.",
        "reset_title": "Reset master password",
        "recovery_key_placeholder": "Recovery key...",
        "new_master_pw_placeholder": "New master password...",
        "confirm_master_pw_placeholder": "Confirm new master password...",
        "reset_button": "Reset",
        "back_to_login": "Back to login",
        "error_recovery_required": "Please enter a recovery key.",
        "error_recovery_invalid": "Recovery key is invalid.",
        "error_password_mismatch": "The passwords do not match.",
        "no_recovery_key": "No recovery key is stored for this vault.",
        "recovery_key_settings": "Recovery key",
        "create_recovery_key": "Create / rotate recovery key",
        "error_recovery_create_failed": "Recovery key could not be created.",
        "change_master_pw": "Change master password",
        "old_master_pw": "Old master password...",
        "new_master_pw": "New master password...",
        "confirm_master_pw": "Confirm new master password...",
        "master_password_changed": "Master password changed.",
        "error_old_password_wrong": "Old master password is wrong.",
        "error_wrong_password": "Wrong password or PIN.",
        "error_empty_password": "Please enter your password or PIN.",
        "windows_hello_failed": "Windows Hello failed. Please enter your PIN/password.",
        "windows_hello_cancelled": "Windows Hello cancelled. Please enter your PIN/password.",
        "windows_hello_unavailable": "Windows Hello dialog not available. Please enter your PIN/password.",
        "windows_hello_consent_msg": "Unlock MangoSafe – please confirm with Windows Hello.",
        "error_wiped": "Too many failed attempts. Vault has been securely wiped.",
        "lockout_msg": "Too many attempts. Please wait {s}s.",
        "error_vault_create": "Could not create vault: {exc}",
        "error_save_failed": "Saving failed: {exc}",
        "error_delete_failed": "Deleting failed: {exc}",
    },
    "ru": {
        "app_name_a": "Mango", "app_name_b": "Safe",
        "all_entries": "Все записи", "favorites": "Избранное", "settings": "Настройки",
        "lock_now": "Заблокировать",
        "local_secure_title": "100% локально и безопасно",
        "local_secure_body": "Ваши данные остаются только на вашем устройстве.",
        "search_placeholder": "Поиск...",
        "found_results": "Найденные результаты: ",
        "no_entries": "Пока нет сохранённых записей.",
        "no_favorites": "Пока нет избранного.",
        "no_matches": "Нет совпадений для '{q}'.",
        "new_entry": "Новая запись", "edit_entry": "Редактировать запись",
        "site_placeholder": "Сайт / программа...",
        "user_placeholder": "Имя пользователя / email...",
        "pw_placeholder": "Пароль...",
        "notes_placeholder": "Заметки (необязательно)...",
        "cancel": "Отмена", "save": "Сохранить",
        "favorite_on": "В избранное", "favorite_off": "Убрать из избранного",
        "edit": "Редактировать", "delete": "Удалить",
        "delete_confirm_title": "Удалить запись",
        "delete_confirm_body": "Точно удалить '{site}' навсегда?",
        "saved_toast": "'{site}' сохранено.",
        "deleted_toast": "Запись удалена.",
        "copied_toast": "Пароль для '{site}' скопирован.",
        "welcome": "Добро пожаловать в MangoSafe",
        "setup_hint": "Задайте мастер-пароль (минимум 8 символов).",
        "master_pw_placeholder": "Мастер-пароль...",
        "create_vault": "Создать хранилище",
        "login_pin_placeholder": "PIN или пароль...",
        "unlock": "Разблокировать",
        "windows_hello": "🔑  Разблокировать через Windows Hello",
        "forgot_password": "Забыли мастер-пароль?",
        "language": "Язык", "design_color": "Акцентный цвет",
        "appearance": "Оформление", "mode_dark": "Тёмный", "mode_light": "Светлый",
        "lang_de": "Немецкий", "lang_en": "Английский", "lang_ru": "Русский",
        "section_appearance": "Язык и оформление",
        "section_security": "Безопасность",
        "error_site_required": "Пожалуйста, укажите сайт/программу.",
        "error_password_required": "Пожалуйста, укажите пароль.",
        "auto_lock": "Автоблокировка (минуты)",
        "windows_hello_label": "Использовать Windows Hello",
        "password_strength": "Сложность пароля",
        "weak": "Слабый", "medium": "Средний", "strong": "Сильный",
        "windows_hello_disabled": "Windows Hello отключен в настройках.",
        "error_master_password_too_short": "Мастер-пароль должен быть не короче 8 символов.",
        "recovery_title": "Ваш ключ восстановления",
        "recovery_hint": "Сохраните этот ключ в надёжном месте. Без него сброс мастер-пароля невозможен.",
        "recovery_copy": "Скопировать",
        "recovery_saved": "Я сохранил ключ восстановления",
        "continue": "Продолжить",
        "recovery_copied": "Ключ восстановления скопирован.",
        "reset_title": "Сброс мастер-пароля",
        "recovery_key_placeholder": "Ключ восстановления...",
        "new_master_pw_placeholder": "Новый мастер-пароль...",
        "confirm_master_pw_placeholder": "Подтвердите новый мастер-пароль...",
        "reset_button": "Сбросить",
        "back_to_login": "Назад ко входу",
        "error_recovery_required": "Введите ключ восстановления.",
        "error_recovery_invalid": "Ключ восстановления недействителен.",
        "error_password_mismatch": "Пароли не совпадают.",
        "no_recovery_key": "Для этого хранилища нет ключа восстановления.",
        "recovery_key_settings": "Ключ восстановления",
        "create_recovery_key": "Создать / обновить ключ восстановления",
        "error_recovery_create_failed": "Не удалось создать ключ восстановления.",
        "change_master_pw": "Изменить мастер-пароль",
        "old_master_pw": "Старый мастер-пароль...",
        "new_master_pw": "Новый мастер-пароль...",
        "confirm_master_pw": "Подтвердите новый пароль...",
        "master_password_changed": "Мастер-пароль изменён.",
        "error_old_password_wrong": "Старый мастер-пароль неверный.",
        "error_wrong_password": "Неверный пароль или PIN.",
        "error_empty_password": "Введите пароль или PIN.",
        "windows_hello_failed": "Windows Hello не сработал. Введите PIN/пароль.",
        "windows_hello_cancelled": "Windows Hello отменён. Введите PIN/пароль.",
        "windows_hello_unavailable": "Диалог Windows Hello недоступен. Введите PIN/пароль.",
        "windows_hello_consent_msg": "Разблокировка MangoSafe – подтвердите через Windows Hello.",
        "error_wiped": "Слишком много неудачных попыток. Хранилище удалено.",
        "lockout_msg": "Слишком много попыток. Подождите {s} с.",
        "error_vault_create": "Не удалось создать хранилище: {exc}",
        "error_save_failed": "Не удалось сохранить: {exc}",
        "error_delete_failed": "Не удалось удалить: {exc}",
    },
}


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

class MangoSafeUI:
    def __init__(self, controller: "MangoSafeApp"):
        self._cached_entries: list["PasswordEntry"] = []
        self._entries_loaded = False
        self._icon_cache: dict[str, object] = {}
        self._icon_pending: dict[str, list[ctk.CTkLabel]] = {}
        self._skeleton_active = False
        self.controller = controller
        self.accent_key = getattr(controller.config, "accent_color", "purple")
        self.lang = getattr(controller.config, "language", "de")
        self.theme_mode = getattr(controller.config, "theme", "dark")
        apply_theme(self.theme_mode)

        self.root = ctk.CTk(fg_color=COL_BG)
        try:
            self.root.attributes("-alpha", 0.0)
        except Exception:
            pass
        self.root.after(1500, self._force_reveal_failsafe)
        self._revealed = False
        self.root.title("MangoSafe")
        self.root.geometry(WINDOW_SIZE)
        self.root.minsize(880, 640)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.bind_all("<Button>", self._notify_activity, add="+")
        self.root.bind_all("<Key>", self._notify_activity, add="+")

        self.content = ctk.CTkFrame(self.root, fg_color="transparent")
        self.content.pack(fill="both", expand=True)

        self._toast_label: Optional[ctk.CTkLabel] = None
        self._all_entries: list["PasswordEntry"] = []
        self._current_view = "all"
        self._open_menu: Optional[ctk.CTkToplevel] = None
        self._shell_built = False
        self.sidebar: Optional[ctk.CTkFrame] = None
        self.page: Optional[ctk.CTkFrame] = None
        self._nav_buttons: dict[str, ctk.CTkButton] = {}
        self._nav_badges: dict[str, ctk.CTkLabel] = {}
        self._search_after_id: Optional[str] = None
        self._list_container: Optional[ctk.CTkScrollableFrame] = None
        self._search_field_widget: Optional[ctk.CTkEntry] = None
        self._results_badge: Optional[ctk.CTkLabel] = None
        self._pre_login_screen = "setup"
        self._pending_setup_submit = None
        self._pending_login_submit = None
        self._pending_login_hello = None

    # -- Helpers ---------------------------------------------------------------

    def t(self, key: str, **kwargs) -> str:
        text = TR.get(self.lang, TR["de"]).get(key, key)
        return text.format(**kwargs) if kwargs else text

    @property
    def accent(self) -> str:
        return ACCENT_PALETTE.get(self.accent_key, ACCENT_PALETTE["purple"])

    @property
    def accent_hover(self) -> str:
        return ACCENT_HOVER.get(self.accent_key, ACCENT_HOVER["purple"])

    @property
    def accent_grad(self) -> str:
        return ACCENT_GRADIENT.get(self.accent_key, self.accent)

    def _tint(self, base: str, amount: float) -> str:
        return _hex_mix(base, self.accent, amount)

    def run(self) -> None:
        self.root.mainloop()

    def close(self) -> None:
        self.root.destroy()

    def _on_close(self) -> None:
        self.close()

    def _notify_activity(self, _event=None) -> None:
        self.controller.notify_activity()

    def invalidate_cache(self) -> None:
        self._entries_loaded = False

    def _close_open_menu(self) -> None:
        if self._open_menu is not None:
            menu = self._open_menu
            self._open_menu = None
            try:
                menu.destroy()
            except Exception:
                pass

    def _clear_content(self) -> None:
        try:
            self.root.update_idletasks()
        except Exception:
            pass
        if self._search_after_id is not None:
            try:
                self.root.after_cancel(self._search_after_id)
            except Exception:
                pass
            self._search_after_id = None
        if self._toast_label is not None:
            try:
                self._toast_label.destroy()
            except Exception:
                pass
            self._toast_label = None
        self._close_open_menu()
        self._shell_built = False
        self.sidebar = None
        self.page = None
        self._nav_buttons = {}
        self._nav_badges = {}
        self._list_container = None
        self._search_field_widget = None
        self._results_badge = None
        for widget in self.content.winfo_children():
            widget.destroy()
        try:
            self.root.update_idletasks()
        except Exception:
            pass

    def _force_reveal_failsafe(self) -> None:
        try:
            alpha = float(self.root.attributes("-alpha"))
        except Exception:
            alpha = 1.0
        if alpha < 1.0:
            try:
                self.root.deiconify()
                self.root.attributes("-alpha", 1.0)
                self.root.lift()
                self._revealed = True
            except Exception:
                pass

    def _bring_to_front_centered(self) -> None:
        self.root.update_idletasks()
        if not self._revealed:
            w, h = (int(v) for v in WINDOW_SIZE.split("x"))
        else:
            w, h = self.root.winfo_width(), self.root.winfo_height()
            if w <= 1 or h <= 1:
                w, h = (int(v) for v in WINDOW_SIZE.split("x"))
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x, y = max(0, (sw - w) // 2), max(0, (sh - h) // 2)
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.after(400, lambda: self.root.attributes("-topmost", False))
        self.root.focus_force()
        try:
            self.root.attributes("-alpha", 1.0)
        except Exception:
            pass
        self._revealed = True

    # -- Skeleton-Loader (verdeckt Layout-Rebuilds) ------------------------------

    def _begin_skeleton(self) -> Optional[ctk.CTkFrame]:
        if self._skeleton_active:
            return None
        self._skeleton_active = True
        overlay = ctk.CTkFrame(self.root, fg_color=COL_BG)
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        sb = ctk.CTkFrame(overlay, fg_color=COL_SIDEBAR, width=SIDEBAR_WIDTH, corner_radius=0)
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)
        ctk.CTkFrame(sb, fg_color=COL_CARD_HOVER, corner_radius=12,
                     height=34, width=150).pack(anchor="w", padx=22, pady=(26, 30))
        for _ in range(3):
            ctk.CTkFrame(sb, fg_color=COL_CARD_HOVER, corner_radius=14,
                         height=44).pack(fill="x", padx=14, pady=4)
        page = ctk.CTkFrame(overlay, fg_color=COL_BG)
        page.pack(side="left", fill="both", expand=True)
        ctk.CTkFrame(page, fg_color=COL_CARD_HOVER, corner_radius=24,
                     height=48).pack(fill="x", padx=26, pady=(26, 14))
        for _ in range(6):
            ctk.CTkFrame(page, fg_color=COL_CARD, corner_radius=18, height=78,
                         border_width=1, border_color=COL_BORDER).pack(fill="x", padx=26, pady=6)
        try:
            overlay.lift()
            self.root.update()
        except Exception:
            pass
        return overlay

    def _end_skeleton(self, overlay: Optional[ctk.CTkFrame]) -> None:
        if overlay is None:
            return
        try:
            overlay.destroy()
        except Exception:
            pass
        self._skeleton_active = False

    # -- Design-Bausteine --------------------------------------------------------

    def _gradient_bar(self, parent, width: int = 150, height: int = 6,
                      bg: Optional[str] = None) -> tk.Canvas:
        canvas = tk.Canvas(parent, width=width, height=height,
                           highlightthickness=0, bg=bg or COL_CARD)
        steps = max(2, width // 4)
        c1, c2 = self.accent, self.accent_grad
        for i in range(steps):
            frac = i / (steps - 1)
            color = _hex_mix(c1, c2, frac)
            x0 = i * width / steps
            x1 = (i + 1) * width / steps + 1
            canvas.create_rectangle(x0, 0, x1, height, fill=color, outline=color)
        return canvas

    def _logo(self, parent) -> ctk.CTkFrame:
        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        ctk.CTkLabel(wrap, text=self.t("app_name_a"), font=FONT_LOGO,
                     text_color=COL_TEXT).pack(side="left")
        ctk.CTkLabel(wrap, text=self.t("app_name_b"), font=FONT_LOGO,
                     text_color=self.accent).pack(side="left")
        return wrap

    def _logo_stacked(self, parent) -> ctk.CTkFrame:
        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        text_row = ctk.CTkFrame(wrap, fg_color="transparent")
        text_row.pack()
        ctk.CTkLabel(text_row, text=self.t("app_name_a"), font=("Segoe UI", 26, "bold"),
                     text_color=COL_TEXT).pack(side="left")
        ctk.CTkLabel(text_row, text=self.t("app_name_b"), font=("Segoe UI", 26, "bold"),
                     text_color=self.accent).pack(side="left")
        self._gradient_bar(wrap, width=150, height=6, bg=COL_CARD).pack(pady=(10, 0))
        return wrap

    def _round_field(self, parent, placeholder: str, height: int = 46,
                     on_change=None) -> ctk.CTkEntry:
        entry = ctk.CTkEntry(
            parent, placeholder_text=placeholder, fg_color=COL_INPUT,
            border_color=COL_BORDER, border_width=1, corner_radius=height // 2,
            height=height, font=FONT_BODY, text_color=COL_TEXT,
            placeholder_text_color=COL_TEXT_DIM,
        )
        entry.bind("<FocusIn>", lambda e: entry.configure(border_color=self.accent))
        entry.bind("<FocusOut>", lambda e: entry.configure(border_color=COL_BORDER))
        if on_change:
            entry.bind("<KeyRelease>", lambda e: on_change(entry.get()))
        return entry

    def _accent_button(self, parent, text: str, command,
                       height=46, corner_radius=None) -> ctk.CTkButton:
        return ctk.CTkButton(
            parent, text=text, height=height,
            corner_radius=corner_radius or height // 2,
            fg_color=self.accent, hover_color=self.accent_hover,
            font=FONT_BODY, command=command,
        )

    def _bind_debounced_search(self, entry: ctk.CTkEntry, callback, delay_ms: int = 350) -> None:
        def on_key(event=None) -> None:
            if event and event.keysym == "Escape":
                entry.delete(0, "end")
                callback("")
                return
            if self._search_after_id is not None:
                try:
                    self.root.after_cancel(self._search_after_id)
                except Exception:
                    pass
            query = entry.get()
            self._search_after_id = self.root.after(delay_ms, lambda: callback(query))
        entry.bind("<KeyRelease>", on_key)

    # -- Zentrierte Karten (dynamische Höhe) ---------------------------------------

    def _center_card(self, width: int) -> tuple[ctk.CTkFrame, ctk.CTkFrame]:
        self._clear_content()
        self._language_picker_corner()
        self._theme_picker_corner()
        card = ctk.CTkFrame(self.content, fg_color=COL_CARD, corner_radius=28,
                            border_width=1, border_color=COL_BORDER, width=width)
        card.place(relx=0.5, rely=0.5, anchor="center")
        card.pack_propagate(False)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.place(relx=0.5, rely=0.5, anchor="center")
        return card, inner

    def _fit_card(self, card: ctk.CTkFrame, inner: ctk.CTkFrame) -> None:
        try:
            inner.update_idletasks()
            card.configure(height=inner.winfo_reqheight())
            card.update_idletasks()
        except Exception:
            log.exception("card fit failed")

    # -- Pre-Login Screens ---------------------------------------------------------

    def _language_picker_corner(self) -> None:
        wrap = ctk.CTkFrame(self.content, fg_color="transparent")
        wrap.place(relx=0.97, rely=0.04, anchor="ne")
        for code, label in (("de", "DE"), ("en", "EN"), ("ru", "RU")):
            active = self.lang == code
            ctk.CTkButton(
                wrap, text=label, width=40, height=32, corner_radius=10,
                fg_color=self.accent if active else COL_CARD,
                hover_color=self.accent_hover if active else COL_CARD_HOVER,
                text_color="white" if active else COL_TEXT_DIM,
                border_width=0 if active else 1, border_color=COL_BORDER,
                font=("Segoe UI", 11, "bold"),
                command=lambda c=code: self._pick_pre_login_language(c),
            ).pack(side="left", padx=3)

    def _pick_pre_login_language(self, code: str) -> None:
        self.lang = code
        self.controller.set_language(code)
        if self._pre_login_screen == "setup":
            self.show_setup_screen(self._pending_setup_submit)
        else:
            self.show_login_screen(self._pending_login_submit, self._pending_login_hello, error=None)

    def _theme_picker_corner(self) -> None:
        wrap = ctk.CTkFrame(self.content, fg_color="transparent")
        wrap.place(relx=0.03, rely=0.04, anchor="nw")
        for mode_key, label_key in (("dark", "mode_dark"), ("light", "mode_light")):
            active = self.theme_mode == mode_key
            ctk.CTkButton(
                wrap, text=self.t(label_key), width=68, height=32, corner_radius=10,
                fg_color=self.accent if active else COL_CARD,
                hover_color=self.accent_hover if active else COL_CARD_HOVER,
                text_color="white" if active else COL_TEXT_DIM,
                border_width=0 if active else 1, border_color=COL_BORDER,
                font=("Segoe UI", 11, "bold"),
                command=lambda m=mode_key: self._pick_pre_login_theme(m),
            ).pack(side="left", padx=3)

    def _pick_pre_login_theme(self, mode: str) -> None:
        self.theme_mode = mode
        apply_theme(mode)
        self.controller.set_theme_mode(mode)
        self.root.configure(fg_color=COL_BG)
        if self._pre_login_screen == "setup":
            self.show_setup_screen(self._pending_setup_submit)
        else:
            self.show_login_screen(self._pending_login_submit, self._pending_login_hello, error=None)

    def show_setup_screen(self, on_submit: Callable[[str], None]) -> None:
        self._pre_login_screen = "setup"
        self._pending_setup_submit = on_submit
        card, inner = self._center_card(470)
        self._logo_stacked(inner).pack(pady=(34, 16))
        ctk.CTkLabel(inner, text=self.t("welcome"), font=FONT_TITLE,
                     text_color=COL_TEXT).pack(pady=(0, 6))
        ctk.CTkLabel(inner, text=self.t("setup_hint"), font=FONT_LABEL,
                     text_color=COL_TEXT_DIM).pack(pady=(0, 22))
        pw_entry = self._round_field(inner, self.t("master_pw_placeholder"), height=48)
        pw_entry.configure(show="•", width=380, justify="center")
        pw_entry.pack(pady=(0, 14))
        pw_entry.bind("<Return>", lambda e: on_submit(pw_entry.get()))
        self._accent_button(inner, self.t("create_vault"),
                            lambda: on_submit(pw_entry.get()), height=48).pack(pady=(0, 34))
        self._fit_card(card, inner)
        self._bring_to_front_centered()
        pw_entry.focus_set()

    def show_login_screen(self, on_submit: Callable[[str], None],
                          on_windows_hello: Callable[[], None],
                          error: Optional[str] = None) -> None:
        self._pre_login_screen = "login"
        self._pending_login_submit = on_submit
        self._pending_login_hello = on_windows_hello
        card, inner = self._center_card(470)
        self._logo_stacked(inner).pack(pady=(34, 18))
        if error:
            ctk.CTkLabel(inner, text=error, font=FONT_LABEL, text_color=COL_DANGER,
                         wraplength=380, justify="center").pack(pady=(0, 10))
        pw_entry = self._round_field(inner, self.t("login_pin_placeholder"), height=48)
        pw_entry.configure(show="•", width=380, justify="center")
        pw_entry.pack(pady=(0, 14))
        pw_entry.bind("<Return>", lambda e: on_submit(pw_entry.get()))
        self._accent_button(inner, self.t("unlock"),
                            lambda: on_submit(pw_entry.get()), height=48).pack(fill="x", pady=(0, 10))
        if WindowsHello.is_available():
            ctk.CTkButton(
                inner, text=self.t("windows_hello"), height=44, corner_radius=22,
                fg_color=COL_CARD_HOVER, hover_color=COL_BORDER,
                text_color=COL_TEXT, font=FONT_LABEL,
                border_width=1, border_color=COL_BORDER,
                command=on_windows_hello,
            ).pack(fill="x", pady=(0, 6))
        ctk.CTkButton(
            inner, text=self.t("forgot_password"), height=36, corner_radius=18,
            fg_color="transparent", hover_color=COL_CARD_HOVER,
            text_color=COL_TEXT_DIM, font=FONT_LABEL,
            command=self.controller.request_reset_master_password,
        ).pack(fill="x", pady=(0, 30))
        self._fit_card(card, inner)
        self._bring_to_front_centered()
        pw_entry.focus_set()

    def show_recovery_key(self, token: str, on_continue: Callable[[], None]) -> None:
        card, inner = self._center_card(560)
        self._logo_stacked(inner).pack(pady=(34, 14))
        ctk.CTkLabel(inner, text=self.t("recovery_title"), font=FONT_TITLE,
                     text_color=COL_TEXT).pack(pady=(0, 6))
        ctk.CTkLabel(inner, text=self.t("recovery_hint"), font=FONT_LABEL,
                     text_color=COL_TEXT_DIM, wraplength=460,
                     justify="center").pack(pady=(0, 16))
        ctk.CTkLabel(inner, text=token, font=("Consolas", 15),
                     text_color=COL_TEXT, fg_color=COL_INPUT,
                     corner_radius=16, padx=18, pady=14, wraplength=460).pack(pady=(0, 12))

        def copy_token() -> None:
            self.root.clipboard_clear()
            self.root.clipboard_append(token)
            self.root.update_idletasks()
            self.show_toast(self.t("recovery_copied"))

        ctk.CTkButton(inner, text=f"📋  {self.t('recovery_copy')}", height=40,
                      corner_radius=20, fg_color=COL_CARD_HOVER, hover_color=COL_BORDER,
                      text_color=COL_TEXT, border_width=1, border_color=COL_BORDER,
                      command=copy_token).pack(pady=(0, 16))
        continue_btn = self._accent_button(inner, self.t("continue"), on_continue, height=46)
        continue_btn.configure(width=380, state="disabled")
        saved_var = tk.BooleanVar(value=False)

        def on_check() -> None:
            continue_btn.configure(state="normal" if saved_var.get() else "disabled")

        ctk.CTkCheckBox(inner, text=self.t("recovery_saved"), variable=saved_var,
                        font=FONT_LABEL, text_color=COL_TEXT, fg_color=self.accent,
                        hover_color=self.accent_hover, command=on_check).pack(pady=(0, 12))
        continue_btn.pack(pady=(0, 34))
        self._fit_card(card, inner)
        self._bring_to_front_centered()

    def show_reset_screen(self, on_submit: Callable[[str, str], None],
                          error: Optional[str] = None) -> None:
        card, inner = self._center_card(470)
        self._logo_stacked(inner).pack(pady=(34, 14))
        ctk.CTkLabel(inner, text=self.t("reset_title"), font=FONT_TITLE,
                     text_color=COL_TEXT).pack(pady=(0, 10))
        if error:
            ctk.CTkLabel(inner, text=error, font=FONT_LABEL, text_color=COL_DANGER,
                         wraplength=380, justify="center").pack(pady=(0, 10))
        recovery = self._round_field(inner, self.t("recovery_key_placeholder"))
        recovery.configure(width=380)
        recovery.pack(pady=(0, 10))
        new_pw = self._round_field(inner, self.t("new_master_pw_placeholder"))
        new_pw.configure(show="•", width=380)
        new_pw.pack(pady=(0, 10))
        confirm_pw = self._round_field(inner, self.t("confirm_master_pw_placeholder"))
        confirm_pw.configure(show="•", width=380)
        confirm_pw.pack(pady=(0, 14))

        def submit() -> None:
            if new_pw.get() != confirm_pw.get():
                self.show_error(self.t("error_password_mismatch"))
                return
            on_submit(recovery.get(), new_pw.get())

        self._accent_button(inner, self.t("reset_button"), submit,
                            height=46).configure(width=380)
        self._accent_button(inner, self.t("reset_button"), submit, height=46).pack(pady=(0, 8))
        ctk.CTkButton(inner, text=self.t("back_to_login"), height=38, corner_radius=19,
                      fg_color="transparent", hover_color=COL_CARD_HOVER,
                      text_color=COL_TEXT_DIM, font=FONT_LABEL,
                      command=lambda: self.controller._show_login(error=None)).pack(pady=(0, 34))
        self._fit_card(card, inner)
        self._bring_to_front_centered()
        recovery.focus_set()

    # -- Main Shell ------------------------------------------------------------------

    def _ensure_shell(self) -> None:
        if self._shell_built:
            return
        self._clear_content()
        self.sidebar = ctk.CTkFrame(self.content, fg_color=COL_SIDEBAR,
                                    width=SIDEBAR_WIDTH, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        self._logo(self.sidebar).pack(anchor="w", padx=22, pady=(26, 30))
        self._add_nav_button("all", "🔐", self.t("all_entries"))
        self._add_nav_button("favorites", "⭐", self.t("favorites"))
        self._add_nav_button("settings", "⚙️", self.t("settings"), show_badge=False)
        spacer = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        spacer.pack(fill="both", expand=True)
        lock_img = load_static_icon("lock", 16)
        if lock_img is not None:
            ctk.CTkButton(
                self.sidebar, image=lock_img, text=self.t("lock_now"), compound="left",
                anchor="w", height=40, corner_radius=12,
                fg_color="transparent", border_width=1, border_color=COL_BORDER,
                text_color=COL_TEXT_DIM, hover_color=COL_CARD_HOVER, font=FONT_LABEL,
                command=self.controller.request_lock_now,
            ).pack(fill="x", padx=14, pady=(0, 10), side="bottom")
        else:
            ctk.CTkButton(
                self.sidebar, text=f"🔒  {self.t('lock_now')}", height=40, corner_radius=12,
                fg_color="transparent", border_width=1, border_color=COL_BORDER,
                text_color=COL_TEXT_DIM, hover_color=COL_CARD_HOVER, font=FONT_LABEL,
                command=self.controller.request_lock_now,
            ).pack(fill="x", padx=14, pady=(0, 10), side="bottom")
        info = ctk.CTkFrame(self.sidebar, fg_color=self._tint(COL_SIDEBAR, 0.14),
                            corner_radius=18)
        info.pack(fill="x", padx=14, pady=(0, 16), side="bottom")
        ctk.CTkLabel(info, text="🛡️", font=("Segoe UI", 18),
                     text_color=self.accent).pack(anchor="w", padx=16, pady=(14, 2))
        ctk.CTkLabel(info, text=self.t("local_secure_title"),
                     font=("Segoe UI", 13, "bold"),
                     text_color=self.accent).pack(anchor="w", padx=16)
        ctk.CTkLabel(info, text=self.t("local_secure_body"),
                     font=("Segoe UI", 11), text_color=COL_TEXT_DIM,
                     wraplength=200, justify="left").pack(anchor="w", padx=16, pady=(2, 14))
        self.page = ctk.CTkFrame(self.content, fg_color=COL_BG)
        self.page.pack(side="left", fill="both", expand=True)
        self._shell_built = True
        self._update_nav_active()

    def _add_nav_button(self, view: str, icon: str, label: str,
                        show_badge: bool = True) -> None:
        img = load_static_icon(view, 20)
        if img is not None:
            row = ctk.CTkButton(
                self.sidebar, image=img, text=label, compound="left", anchor="w",
                height=44, corner_radius=14, font=FONT_NAV,
                command=lambda: self._switch_view(view),
            )
        else:
            row = ctk.CTkButton(
                self.sidebar, text=f"{icon}   {label}", anchor="w", height=44,
                corner_radius=14, font=FONT_NAV,
                command=lambda: self._switch_view(view),
            )
        row.pack(fill="x", padx=14, pady=4)
        self._nav_buttons[view] = row
        if show_badge:
            badge = ctk.CTkLabel(
                row, text="0", font=("Segoe UI", 11, "bold"), text_color=COL_TEXT_DIM,
                corner_radius=10, width=26, height=20, fg_color="transparent",
            )
            badge.place(relx=0.94, rely=0.5, anchor="e")
            self._nav_badges[view] = badge

    def _update_nav_active(self) -> None:
        for view, btn in self._nav_buttons.items():
            active = self._current_view == view
            btn.configure(
                fg_color=self.accent if active else "transparent",
                hover_color=self.accent_hover if active else COL_CARD_HOVER,
                text_color="white" if active else COL_TEXT,
            )
        for view, badge in self._nav_badges.items():
            active = self._current_view == view
            badge.configure(
                fg_color="transparent",
                text_color="white" if active else COL_TEXT_DIM,
            )

    def _update_nav_counts(self) -> None:
        n_all = len(self._all_entries)
        n_fav = sum(1 for e in self._all_entries if e.favorite)
        if "all" in self._nav_badges:
            self._nav_badges["all"].configure(text=str(n_all))
        if "favorites" in self._nav_badges:
            self._nav_badges["favorites"].configure(text=str(n_fav))

    def _switch_view(self, view: str) -> None:
        overlay = self._begin_skeleton()
        try:
            self._current_view = view
            self._update_nav_active()
            self._render_page_for_current_view()
        finally:
            self._end_skeleton(overlay)

    def _render_page_for_current_view(self) -> None:
        for widget in self.page.winfo_children():
            widget.destroy()
        self._list_container = None
        self._search_field_widget = None
        self._results_badge = None
        if self._current_view == "settings":
            self._render_settings_page()
            return
        if self._current_view == "favorites":
            entries = [e for e in self._all_entries if e.favorite]
            empty_text = self.t("no_favorites")
        else:
            entries = self._all_entries
            empty_text = self.t("no_entries")
        self._render_list_page(entries, empty_text)

    def show_main_screen(self, entries: list["PasswordEntry"]) -> None:
        overlay = self._begin_skeleton()
        try:
            self._all_entries = entries
            if entries is not None:
                self._cached_entries = entries
                self._entries_loaded = True
            if self._current_view == "settings":
                self._current_view = "all"
            self._ensure_shell()
            self._update_nav_counts()
            self._update_nav_active()
            self._render_page_for_current_view()
            if self._search_field_widget is not None:
                self._search_field_widget.focus_set()
        finally:
            self._end_skeleton(overlay)

    # -- List page ---------------------------------------------------------------------

    def _build_top_bar(self) -> None:
        top = ctk.CTkFrame(self.page, fg_color="transparent")
        top.pack(fill="x", padx=26, pady=(26, 14))
        top.grid_columnconfigure(0, weight=1)
        search = self._round_field(top, self.t("search_placeholder"), height=48)
        search.grid(row=0, column=0, sticky="ew", padx=(0, 12))
        self._bind_debounced_search(search, self.controller.handle_search)
        ctk.CTkButton(
            top, text="+", width=48, height=48, corner_radius=24,
            fg_color=self.accent, hover_color=self.accent_hover,
            font=("Segoe UI", 22, "bold"),
            command=self.controller.request_add_entry,
        ).grid(row=0, column=1)
        self._search_field_widget = search

    def _ensure_list_shell(self) -> None:
        if self._list_container is not None:
            return
        self._build_top_bar()
        badge_wrap = ctk.CTkFrame(self.page, fg_color="transparent", height=1)
        badge_wrap.pack(fill="x", padx=28)
        self._results_badge = ctk.CTkLabel(
            badge_wrap, text="", font=FONT_LABEL, text_color=COL_TEXT_DIM,
            fg_color="transparent", corner_radius=12, padx=14, pady=5,
        )
        self._list_container = ctk.CTkScrollableFrame(self.page, fg_color="transparent")
        self._list_container.pack(fill="both", expand=True, padx=26, pady=(0, 26))
        try:
            self._list_container.configure(
                scrollbar_button_color=self.accent,
                scrollbar_button_hover_color=self.accent_hover,
            )
        except Exception:
            pass

    def _clear_container(self) -> None:
        if self._list_container is None:
            return
        for widget in self._list_container.winfo_children():
            widget.destroy()

    def _update_scrollregion(self) -> None:
        if self._list_container is None:
            return
        canvas = getattr(self._list_container, "_parent_canvas", None)
        if canvas is not None:
            try:
                canvas.configure(scrollregion=canvas.bbox("all"))
            except Exception:
                pass

    def _render_list_page(self, entries: list["PasswordEntry"], empty_text: str) -> None:
        self._ensure_list_shell()
        if self._results_badge.winfo_ismapped():
            self._results_badge.pack_forget()
        self._list_container.configure(fg_color="transparent", corner_radius=0)
        self._populate_rows(entries, empty_text)
        if self._search_field_widget is not None:
            self._search_field_widget.focus_set()

    def show_search_results(self, query: str, entries: list["PasswordEntry"]) -> None:
        self._ensure_shell()
        self._ensure_list_shell()
        self._results_badge.configure(
            text=f"{self.t('found_results')} {len(entries)}")
        if not self._results_badge.winfo_ismapped():
            self._results_badge.pack(anchor="w", pady=(0, 10))
        self._list_container.configure(fg_color=COL_CARD, corner_radius=18)
        search = self._search_field_widget
        if search is not None and search.get() != query:
            search.delete(0, "end")
            search.insert(0, query)
        if search is not None:
            search.focus_set()
            search.icursor(len(query))
        self._populate_rows(entries, self.t("no_matches", q=query))

    def _populate_rows(self, entries: list["PasswordEntry"], empty_text: Optional[str]) -> None:
        self._clear_container()
        if not entries:
            ctk.CTkLabel(self._list_container, text=empty_text or "",
                         font=FONT_BODY, text_color=COL_TEXT_DIM).pack(pady=48)
            self._update_scrollregion()
            return
        for entry in entries:
            try:
                self._build_row(self._list_container, entry)
            except Exception:
                log.exception("Could not build row for %s",
                              getattr(entry, "site", "?"))
        self._update_scrollregion()

    def _create_letter_image(self, letter: str, bg_color: str,
                             size: int = AVATAR_SIZE) -> Optional[ctk.CTkImage]:
        if not _PIL_OK:
            return None
        img = Image.new("RGBA", (size, size), bg_color)
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("segoeui.ttf", int(size * 0.55))
        except Exception:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), letter, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (size - tw) // 2 - bbox[0]
        y = (size - th) // 2 - bbox[1]
        draw.text((x, y), letter, fill="white", font=font)
        return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))

    def _build_row(self, parent, entry: "PasswordEntry") -> None:
        row = ctk.CTkFrame(parent, fg_color=COL_CARD, corner_radius=18,
                           border_width=1, border_color=COL_BORDER, height=78)
        row.grid_columnconfigure(1, weight=1)
        row.bind("<Enter>", lambda e: row.configure(fg_color=COL_CARD_HOVER))
        row.bind("<Leave>", lambda e: row.configure(fg_color=COL_CARD))
        row.pack(fill="x", pady=6)
        avatar = ctk.CTkLabel(
            row, text="", font=("Segoe UI", 14, "bold"), text_color="white",
            fg_color=COL_CARD_HOVER, corner_radius=14,
            width=AVATAR_SIZE, height=AVATAR_SIZE,
        )
        avatar.grid(row=0, column=0, rowspan=2, padx=(16, 14), pady=16)
        site_label = ctk.CTkLabel(row, text="", font=FONT_SITE, text_color=COL_TEXT,
                                  anchor="w")
        site_label.grid(row=0, column=1, sticky="w", pady=(14, 0))
        user_label = ctk.CTkLabel(row, text="", font=FONT_SMALL,
                                  text_color=COL_TEXT_DIM, anchor="w")
        user_label.grid(row=1, column=1, sticky="w", pady=(0, 14))
        right = ctk.CTkFrame(row, fg_color="transparent")
        right.grid(row=0, column=2, rowspan=2, padx=14)
        pw_label = ctk.CTkLabel(right, text="•" * 8, font=FONT_MONO,
                                text_color=COL_TEXT_DIM, width=110, anchor="w")
        pw_label.pack(side="left", padx=(0, 10))
        state = {"showing_pw": False}

        def toggle_pw() -> None:
            state["showing_pw"] = not state["showing_pw"]
            if state["showing_pw"]:
                pw_label.configure(text=entry.password,
                                   width=max(110, len(entry.password) * 9),
                                   text_color=COL_TEXT)
            else:
                pw_label.configure(text="•" * 8, width=110, text_color=COL_TEXT_DIM)

        def copy_pw() -> None:
            self.root.clipboard_clear()
            self.root.clipboard_append(entry.password)
            self.root.update_idletasks()
            self.show_toast(self.t("copied_toast", site=entry.site))

        def icon_btn(symbol: str, command, font_size: int = 14) -> ctk.CTkButton:
            return ctk.CTkButton(
                right, text=symbol, width=36, height=36, corner_radius=12,
                fg_color="transparent", hover_color=COL_CARD_HOVER,
                text_color=COL_TEXT_DIM, font=("Segoe UI", font_size),
                command=command,
            )

        icon_btn("👁", toggle_pw).pack(side="left", padx=2)
        icon_btn("📋", copy_pw).pack(side="left", padx=2)
        icon_btn("⋮", lambda: self._open_entry_menu(right, entry),
                 font_size=16).pack(side="left", padx=2)
        color, letter = _brand_for_site(entry.site)
        letter_img = self._create_letter_image(letter, color)
        if letter_img is not None:
            avatar.configure(image=letter_img, text="", fg_color="transparent")
        else:
            avatar.configure(text=letter, fg_color=color)
        self._load_icon_async(entry.site, avatar)
        star = "★  " if entry.favorite else ""
        site_label.configure(text=f"{star}{entry.site}",
                             text_color="#FFD700" if entry.favorite else COL_TEXT)
        user_label.configure(text=entry.username)

    # -- Icons ------------------------------------------------------------------------

    def _load_icon_async(self, site: str, avatar: ctk.CTkLabel) -> None:
        domain = _domain_for_site(site)
        avatar._mangosafe_pending_domain = domain
        if not domain:
            return
        cached = self._icon_cache.get(domain)
        if cached is not None:
            self._apply_icon(avatar, domain, cached)
            return
        if domain in self._icon_pending:
            self._icon_pending[domain].append(avatar)
            return
        self._icon_pending[domain] = [avatar]
        _ICON_EXECUTOR.submit(self._fetch_icon_worker, domain)

    def _fetch_icon_worker(self, domain: str) -> None:
        img = _download_icon(domain)
        self._icon_cache[domain] = img
        avatars = self._icon_pending.pop(domain, [])
        if img is not None:
            for avatar in avatars:
                try:
                    self.root.after(0, lambda a=avatar, d=domain, i=img:
                                    self._apply_icon(a, d, i))
                except Exception:
                    pass

    def _apply_icon(self, avatar: ctk.CTkLabel, domain: str, image) -> None:
        if getattr(avatar, "_mangosafe_pending_domain", None) != domain:
            return
        try:
            if not avatar.winfo_exists():
                return
            avatar.configure(image=image, text="", fg_color="transparent")
        except Exception:
            pass

    # -- Entry menu ----------------------------------------------------------------------

    def _open_entry_menu(self, widget, entry: "PasswordEntry") -> None:
        self._close_open_menu()
        TRANSPARENT_KEY = "#010203"
        popup = ctk.CTkToplevel(self.root)
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)
        popup.configure(fg_color=TRANSPARENT_KEY)
        try:
            popup.attributes("-transparentcolor", TRANSPARENT_KEY)
        except Exception:
            pass
        frame = ctk.CTkFrame(popup, fg_color=COL_CARD, corner_radius=16,
                             border_width=1, border_color=COL_BORDER)
        frame.pack(fill="both", expand=True)

        def item(label: str, command, danger: bool = False) -> None:
            ctk.CTkButton(
                frame, text=label, anchor="w", height=44, corner_radius=10,
                fg_color="transparent", hover_color=COL_CARD_HOVER,
                text_color=COL_DANGER if danger else COL_TEXT, font=FONT_BODY,
                command=lambda: (self._close_open_menu(), command()),
            ).pack(fill="x", padx=8, pady=4)

        fav_label = self.t("favorite_off") if entry.favorite else self.t("favorite_on")
        item(fav_label, lambda: self.controller.request_toggle_favorite(entry.entry_id))
        item(self.t("edit"), lambda: self.controller.request_edit_entry(entry.entry_id))
        item(self.t("delete"), lambda: self._ask_delete(entry), danger=True)
        popup.update_idletasks()
        menu_w, menu_h = 250, 3 * 52 + 16
        x = widget.winfo_rootx() - menu_w + widget.winfo_width()
        y = widget.winfo_rooty() + widget.winfo_height() + 4
        popup.geometry(f"{menu_w}x{menu_h}+{max(x, 0)}+{y}")
        self._open_menu = popup
        popup.bind("<FocusOut>", lambda e: self._close_open_menu())
        popup.after(60, popup.focus_force)

    def _ask_delete(self, entry: "PasswordEntry") -> None:
        self.confirm_delete(entry,
                            on_confirm=lambda: self.controller.request_delete_entry(entry.entry_id))

    # -- Entry form -----------------------------------------------------------------------

    def show_entry_form(self, existing_entry: Optional["PasswordEntry"],
                        on_save: Callable[[str, str, str, str], None]) -> None:
        overlay = ctk.CTkFrame(self.root, fg_color="#000000")
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        card = ctk.CTkFrame(overlay, fg_color=COL_CARD, corner_radius=24,
                            border_width=1, border_color=COL_BORDER, width=470)
        card.place(relx=0.5, rely=0.5, anchor="center")
        card.pack_propagate(False)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.place(relx=0.5, rely=0.5, anchor="center")
        title = self.t("edit_entry") if existing_entry else self.t("new_entry")
        header = ctk.CTkFrame(inner, fg_color="transparent")
        header.pack(fill="x", padx=26, pady=(24, 4))
        ctk.CTkLabel(header, text=title, font=FONT_TITLE,
                     text_color=COL_TEXT).pack(side="left")
        ctk.CTkButton(header, text="✕", width=30, height=30, corner_radius=15,
                      fg_color="transparent", hover_color=COL_CARD_HOVER,
                      text_color=COL_TEXT_DIM,
                      command=overlay.destroy).pack(side="right")
        self._gradient_bar(inner, width=418, height=4, bg=COL_CARD).pack(pady=(0, 14))
        site = self._round_field(inner, self.t("site_placeholder"))
        site.configure(width=418)
        site.pack(pady=6)
        user = self._round_field(inner, self.t("user_placeholder"))
        user.configure(width=418)
        user.pack(pady=6)

        pw_row = ctk.CTkFrame(inner, fg_color="transparent", width=418)
        pw_row.pack(pady=6)
        password = self._round_field(pw_row, self.t("pw_placeholder"))
        password.configure(show="•", width=418)
        password.pack(fill="x")

        def generate_password() -> None:
            chars = string.ascii_letters + string.digits + "!@#$%^&*()-_=+[]{}|;:,.<>?"
            pw = ''.join(secrets.choice(chars) for _ in range(16))
            password.delete(0, "end")
            password.insert(0, pw)
            update_strength()

        def toggle_visibility():
            password.configure(show="" if password.cget("show") else "•")

        def pw_icon_btn(symbol: str, command) -> ctk.CTkButton:
            return ctk.CTkButton(
                pw_row, text=symbol, width=28, height=28, corner_radius=14,
                fg_color=COL_INPUT, hover_color=COL_CARD_HOVER,
                border_width=1, border_color=COL_BORDER,
                text_color=COL_TEXT_DIM, font=("Segoe UI", 11),
                command=command,
            )

        key_btn = pw_icon_btn("🔑", generate_password)
        eye_btn = pw_icon_btn("👁", toggle_visibility)
        key_btn.place(relx=1.0, rely=0.5, anchor="e", x=-40)
        eye_btn.place(relx=1.0, rely=0.5, anchor="e", x=-8)

        strength_label = ctk.CTkLabel(inner, text="", font=FONT_LABEL,
                                      text_color=COL_TEXT_DIM, width=418, anchor="w")
        strength_label.pack(pady=(6, 2))
        strength_bar = ctk.CTkProgressBar(inner, height=6, corner_radius=3,
                                          fg_color=COL_BORDER, progress_color=COL_DANGER,
                                          width=418)
        strength_bar.pack(pady=(0, 8))
        strength_bar.set(0)

        def update_strength():
            pw = password.get()
            if not pw:
                strength_label.configure(text="")
                strength_bar.set(0)
                return
            score = 0
            if len(pw) >= 8:
                score += 1
            if any(c.islower() for c in pw) and any(c.isupper() for c in pw):
                score += 1
            if any(c.isdigit() for c in pw):
                score += 1
            if any(c in "!@#$%^&*()-_=+[]{}|;:,.<>?" for c in pw):
                score += 1
            if len(pw) >= 16:
                score += 1
            if score <= 2:
                text, color = self.t("weak"), COL_DANGER
            elif score <= 4:
                text, color = self.t("medium"), COL_WARN
            else:
                text, color = self.t("strong"), COL_SUCCESS
            strength_label.configure(
                text=f"{self.t('password_strength')}: {text}", text_color=color)
            strength_bar.configure(progress_color=color)
            strength_bar.set(score / 5)

        password.bind("<KeyRelease>", lambda e: update_strength())
        self.root.after(100, update_strength)
        notes = self._round_field(inner, self.t("notes_placeholder"))
        notes.configure(width=418)
        notes.pack(pady=6)
        if existing_entry:
            site.insert(0, existing_entry.site)
            user.insert(0, existing_entry.username)
            password.insert(0, existing_entry.password)
            notes.insert(0, existing_entry.notes)
            self.root.after(200, update_strength)

        def submit():
            on_save(site.get(), user.get(), password.get(), notes.get())
            overlay.destroy()

        btn_row = ctk.CTkFrame(inner, fg_color="transparent")
        btn_row.pack(pady=(18, 26))
        ctk.CTkButton(btn_row, text=self.t("cancel"), height=46, corner_radius=23,
                      width=200, fg_color=COL_CARD_HOVER, hover_color=COL_BORDER,
                      text_color=COL_TEXT,
                      command=overlay.destroy).pack(side="left", padx=(0, 7))
        self._accent_button(btn_row, self.t("save"), submit,
                            height=46).configure(width=200)
        self._accent_button(btn_row, self.t("save"), submit, height=46).pack(side="left", padx=(7, 0))
        self._fit_card(card, inner)
        site.focus_set()

    # -- Settings ---------------------------------------------------------------------------

    def _settings_card(self, parent, title: str) -> ctk.CTkFrame:
        card = ctk.CTkFrame(parent, fg_color=COL_CARD, corner_radius=20,
                            border_width=1, border_color=COL_BORDER)
        card.pack(fill="x", pady=(0, 14))
        ctk.CTkLabel(card, text=title, font=FONT_SECTION,
                     text_color=COL_TEXT).pack(anchor="w", padx=22, pady=(18, 4))
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=22, pady=(6, 20))
        return inner

    def _render_settings_page(self) -> None:
        scroll = ctk.CTkScrollableFrame(self.page, fg_color="transparent",
                                        scrollbar_button_color=self.accent,
                                        scrollbar_button_hover_color=self.accent_hover)
        scroll.pack(fill="both", expand=True, padx=26, pady=(24, 26))
        ctk.CTkLabel(scroll, text=self.t("settings"), font=FONT_TITLE,
                     text_color=COL_TEXT).pack(anchor="w", pady=(0, 18))
        inner = self._settings_card(scroll, self.t("section_appearance"))
        ctk.CTkLabel(inner, text=self.t("language"), font=FONT_LABEL,
                     text_color=COL_TEXT_DIM).pack(anchor="w", pady=(0, 6))
        lang_options = {"de": self.t("lang_de"), "en": self.t("lang_en"),
                        "ru": self.t("lang_ru")}
        lang_var = tk.StringVar(value=lang_options.get(self.lang, self.t("lang_de")))

        def on_lang_pick(choice: str):
            code = next((k for k, v in lang_options.items() if v == choice), "de")
            self.lang = code
            self.controller.set_language(code)
            self._refresh_keep_settings()

        ctk.CTkOptionMenu(
            inner, values=list(lang_options.values()), variable=lang_var,
            command=on_lang_pick, fg_color=COL_INPUT, button_color=self.accent,
            button_hover_color=self.accent_hover, dropdown_fg_color=COL_CARD,
            text_color=COL_TEXT, dropdown_text_color=COL_TEXT,
            dropdown_hover_color=COL_CARD_HOVER,
            width=260, height=42, corner_radius=14, font=FONT_BODY,
        ).pack(anchor="w", pady=(0, 16))
        ctk.CTkLabel(inner, text=self.t("appearance"), font=FONT_LABEL,
                     text_color=COL_TEXT_DIM).pack(anchor="w", pady=(0, 6))
        mode_row = ctk.CTkFrame(inner, fg_color="transparent")
        mode_row.pack(anchor="w")
        for mode_key, label_key in (("dark", "mode_dark"), ("light", "mode_light")):
            active = self.theme_mode == mode_key
            ctk.CTkButton(
                mode_row, text=self.t(label_key), width=120, height=42, corner_radius=14,
                fg_color=self.accent if active else COL_INPUT,
                hover_color=self.accent_hover if active else COL_CARD_HOVER,
                text_color="white" if active else COL_TEXT, font=FONT_BODY,
                border_width=0 if active else 1, border_color=COL_BORDER,
                command=lambda m=mode_key: self._pick_theme_mode(m),
            ).pack(side="left", padx=(0, 10))
        inner = self._settings_card(scroll, self.t("design_color"))
        swatch_row = ctk.CTkFrame(inner, fg_color="transparent")
        swatch_row.pack(anchor="w")
        for key, hexval in ACCENT_PALETTE.items():
            border = 3 if key == self.accent_key else 0
            ctk.CTkButton(
                swatch_row, text="", width=40, height=40, corner_radius=20,
                fg_color=hexval, hover_color=hexval,
                border_width=border, border_color="white",
                command=lambda k=key: self._pick_accent(k),
            ).pack(side="left", padx=(0, 10))
        inner = self._settings_card(scroll, self.t("section_security"))
        ctk.CTkLabel(inner, text=self.t("auto_lock"), font=FONT_LABEL,
                     text_color=COL_TEXT_DIM).pack(anchor="w", pady=(0, 6))
        lock_frame = ctk.CTkFrame(inner, fg_color="transparent")
        lock_frame.pack(fill="x", pady=(0, 16))
        current_minutes = getattr(self.controller.config, "auto_lock_minutes", 2)
        lock_slider = ctk.CTkSlider(
            lock_frame, from_=1, to=30, number_of_steps=29,
            button_color=self.accent, button_hover_color=self.accent_hover,
            progress_color=self.accent, fg_color=COL_BORDER,
            command=lambda v: lock_label.configure(text=f"{int(v)} min"))
        lock_slider.set(current_minutes)
        lock_slider.pack(side="left", fill="x", expand=True, padx=(0, 12))
        lock_label = ctk.CTkLabel(lock_frame, text=f"{int(lock_slider.get())} min",
                                  font=FONT_BODY, text_color=COL_TEXT, width=60)
        lock_label.pack(side="left")
        lock_slider.bind("<ButtonRelease-1>",
                         lambda e: self.controller.set_auto_lock_minutes(int(lock_slider.get())))
        ctk.CTkLabel(inner, text=self.t("windows_hello_label"), font=FONT_LABEL,
                     text_color=COL_TEXT_DIM).pack(anchor="w", pady=(0, 6))
        hello_var = tk.BooleanVar(value=getattr(self.controller.config, "use_windows_hello", True))
        ctk.CTkSwitch(inner, text="", variable=hello_var,
                      progress_color=self.accent, button_color=COL_CARD_HOVER,
                      button_hover_color=COL_BORDER,
                      command=lambda: self.controller.set_use_windows_hello(hello_var.get()),
                      ).pack(anchor="w", pady=(0, 18))
        ctk.CTkLabel(inner, text=self.t("recovery_key_settings"), font=FONT_LABEL,
                     text_color=COL_TEXT_DIM).pack(anchor="w", pady=(0, 6))
        recovery_btn = self._accent_button(inner, self.t("create_recovery_key"),
                                           self.controller.request_create_recovery_key,
                                           height=42, corner_radius=14)
        recovery_btn.configure(width=280)
        recovery_btn.pack(anchor="w", pady=(0, 18))
        ctk.CTkLabel(inner, text=self.t("change_master_pw"), font=FONT_LABEL,
                     text_color=COL_TEXT_DIM).pack(anchor="w", pady=(0, 6))
        old_pw = self._round_field(inner, self.t("old_master_pw"))
        old_pw.configure(show="•")
        old_pw.pack(fill="x", pady=4)
        new_pw = self._round_field(inner, self.t("new_master_pw"))
        new_pw.configure(show="•")
        new_pw.pack(fill="x", pady=4)
        confirm_pw = self._round_field(inner, self.t("confirm_master_pw"))
        confirm_pw.configure(show="•")
        confirm_pw.pack(fill="x", pady=4)

        def change_pw() -> None:
            if new_pw.get() != confirm_pw.get():
                self.show_error(self.t("error_password_mismatch"))
                return
            self.controller.change_master_password(old_pw.get(), new_pw.get())

        change_btn = self._accent_button(inner, self.t("change_master_pw"), change_pw,
                                         height=42, corner_radius=14)
        change_btn.configure(width=280)
        change_btn.pack(anchor="w", pady=(10, 0))

    def _refresh_keep_settings(self) -> None:
        overlay = self._begin_skeleton()
        try:
            self._clear_content()
            self.show_main_screen(self._all_entries)
            self._switch_view("settings")
        finally:
            self._end_skeleton(overlay)

    def _pick_theme_mode(self, mode: str) -> None:
        self.theme_mode = mode
        apply_theme(mode)
        self.controller.set_theme_mode(mode)
        self.root.configure(fg_color=COL_BG)
        self._refresh_keep_settings()

    def _pick_accent(self, key: str) -> None:
        self.accent_key = key
        self.controller.set_accent_color(key)
        self._refresh_keep_settings()

    # -- Toast / Dialogs -----------------------------------------------------------------------

    def show_toast(self, message: str) -> None:
        if self._toast_label is not None:
            self._toast_label.destroy()
        if self.theme_mode == "light":
            bg_color = COL_CARD
            text_color = COL_TEXT
        else:
            bg_color = self.accent
            text_color = "white"
        self._toast_label = ctk.CTkLabel(
            self.root, text=message, font=FONT_LABEL, text_color=text_color,
            fg_color=bg_color, corner_radius=24, padx=20, pady=10,
            border_width=1, border_color=COL_BORDER,
        )
        self._toast_label.place(relx=0.5, rely=0.95, anchor="s")
        self._toast_label.bind("<Button-1>", lambda e: self._clear_toast())
        self.root.after(3000, self._clear_toast)

    def _clear_toast(self) -> None:
        if self._toast_label is not None:
            self._toast_label.destroy()
            self._toast_label = None

    def confirm_delete(self, entry: "PasswordEntry", on_confirm: Callable[[], None]) -> None:
        answer = messagebox.askyesno(
            self.t("delete_confirm_title"),
            self.t("delete_confirm_body", site=entry.site),
            parent=self.root,
        )
        if answer:
            on_confirm()

    def show_error(self, message: str) -> None:
        messagebox.showerror("MangoSafe", message, parent=self.root)
