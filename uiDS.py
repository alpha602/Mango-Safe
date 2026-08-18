from __future__ import annotations

import io
import os
import secrets
import hashlib
import threading
import contextlib
import urllib.request
import concurrent.futures
import random
import string
from vault import WindowsHello
from pathlib import Path
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from typing import Callable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from main import MangoSafeApp, PasswordEntry

try:
    from PIL import Image, ImageDraw, ImageFont
    _PIL_OK = True
except ImportError:
    _PIL_OK = False


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")



THEMES = {
    "dark": {
        "bg": "#0E0D13",
        "sidebar": "#151319",
        "card": "#1B1922",
        "card_hover": "#242130",
        "border": "#2A2733",
        "text": "#F2F1F5",
        "text_dim": "#9A97A6",
    },
    "light": {
        "bg": "#D9D6E6",
        "sidebar": "#CCC8DC",
        "card": "#F8F7FB",
        "card_hover": "#E8E5F1",
        "border": "#8E88A3",
        "text": "#0D0C13",
        "text_dim": "#3E3949",
    },
}

COL_BG = THEMES["dark"]["bg"]
COL_SIDEBAR = THEMES["dark"]["sidebar"]
COL_CARD = THEMES["dark"]["card"]
COL_CARD_HOVER = THEMES["dark"]["card_hover"]
COL_BORDER = THEMES["dark"]["border"]
COL_TEXT = THEMES["dark"]["text"]
COL_TEXT_DIM = THEMES["dark"]["text_dim"]

COL_DANGER = "#E14F4F"
COL_DANGER_HOVER = "#B93E3E"


def apply_theme(mode: str) -> None:
    global COL_BG, COL_SIDEBAR, COL_CARD, COL_CARD_HOVER, COL_BORDER, COL_TEXT, COL_TEXT_DIM
    palette = THEMES.get(mode, THEMES["dark"])
    COL_BG = palette["bg"]
    COL_SIDEBAR = palette["sidebar"]
    COL_CARD = palette["card"]
    COL_CARD_HOVER = palette["card_hover"]
    COL_BORDER = palette["border"]
    COL_TEXT = palette["text"]
    COL_TEXT_DIM = palette["text_dim"]
    ctk.set_appearance_mode("light" if mode == "light" else "dark")


ACCENT_PALETTE = {
    "purple": "#8B5CF6",
    "blue": "#3B82F6",
    "green": "#10B981",
    "red": "#EF4444",
    "orange": "#F59E0B",
    "pink": "#EC4899",
    "teal": "#14B8A6",
    "yellow": "#EAB308",
    "indigo": "#6366F1",
    "rose": "#F43F5E",
}
ACCENT_HOVER = {
    "purple": "#7C3AED",
    "blue": "#2563EB",
    "green": "#059669",
    "red": "#DC2626",
    "orange": "#FF8800",
    "pink": "#DB2777",
    "teal": "#0D9488",
    "yellow": "#FFFF00",
    "indigo": "#4F46E5",
    "rose": "#E20E91",
}

FONT_LOGO = ("Segoe UI", 20, "bold")
FONT_TITLE = ("Segoe UI", 22, "bold")
FONT_SITE = ("Segoe UI", 16, "bold")
FONT_BODY = ("Segoe UI", 14)
FONT_LABEL = ("Segoe UI", 13)
FONT_NAV = ("Segoe UI", 14, "bold")

WINDOW_SIZE = "1140x760"
SIDEBAR_WIDTH = 250
AVATAR_SIZE = 42
ICON_PIXELS = 42

_ICON_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="mangosafe-icon")


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
    "xbox": {"domain": "xbox.com", "color": "#107C10", "letter": "X"},
    "wattpad": {"domain": "wattpad.com", "color": "#FF6600", "letter": "W"},
    "goodreads": {"domain": "goodreads.com", "color": "#372213", "letter": "G"},
    "archiveofourown": {"domain": "archiveofourown.org", "color": "#990000", "letter": "A"},
    "fanfiction": {"domain": "fanfiction.net", "color": "#336699", "letter": "F"},
    "grammarly": {"domain": "grammarly.com", "color": "#15C39A", "letter": "G"},
    "medium": {"domain": "medium.com", "color": "#000000", "letter": "M"},
    "substack": {"domain": "substack.com", "color": "#FF6719", "letter": "S"},
    "spotify": {"domain": "spotify.com", "color": "#1DB954", "letter": "S"},
    "applemusic": {"domain": "apple.com", "color": "#FA233B", "letter": "A"},
    "soundcloud": {"domain": "soundcloud.com", "color": "#FF5500", "letter": "S"},
    "bandcamp": {"domain": "bandcamp.com", "color": "#629AA9", "letter": "B"},
    "tidal": {"domain": "tidal.com", "color": "#000000", "letter": "T"},
    "deezer": {"domain": "deezer.com", "color": "#00C7F2", "letter": "D"},
    "shazam": {"domain": "shazam.com", "color": "#0088FF", "letter": "S"},
    "lastfm": {"domain": "last.fm", "color": "#D51007", "letter": "L"},
    "github": {"domain": "github.com", "color": "#181717", "letter": "G"},
    "gitlab": {"domain": "gitlab.com", "color": "#FC6D26", "letter": "G"},
    "bitbucket": {"domain": "bitbucket.org", "color": "#0052CC", "letter": "B"},
    "stackoverflow": {"domain": "stackoverflow.com", "color": "#F48024", "letter": "S"},
    "leetcode": {"domain": "leetcode.com", "color": "#FFA116", "letter": "L"},
    "hackerrank": {"domain": "hackerrank.com", "color": "#00EA64", "letter": "H"},
    "codepen": {"domain": "codepen.io", "color": "#000000", "letter": "C"},
    "replit": {"domain": "replit.com", "color": "#F26207", "letter": "R"},
    "vercel": {"domain": "vercel.com", "color": "#000000", "letter": "V"},
    "netlify": {"domain": "netlify.com", "color": "#00C7B7", "letter": "N"},
    "heroku": {"domain": "heroku.com", "color": "#430098", "letter": "H"},
    "openai": {"domain": "openai.com", "color": "#10A37F", "letter": "O"},
    "anthropic": {"domain": "anthropic.com", "color": "#4F46E5", "letter": "A"},
    "huggingface": {"domain": "huggingface.co", "color": "#FFD21E", "letter": "H"},
    "replicate": {"domain": "replicate.com", "color": "#000000", "letter": "R"},
    "stabilityai": {"domain": "stability.ai", "color": "#5C2D91", "letter": "S"},
    "midjourney": {"domain": "midjourney.com", "color": "#000000", "letter": "M"},
    "runwayml": {"domain": "runwayml.com", "color": "#FF6B00", "letter": "R"},
    "perplexity": {"domain": "perplexity.ai", "color": "#000000", "letter": "P"},
    "poe": {"domain": "poe.com", "color": "#3B82F6", "letter": "P"},
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
    "googledrive": {"domain": "google.com", "color": "#4285F4", "letter": "G"},
    "dropbox": {"domain": "dropbox.com", "color": "#0061FF", "letter": "D"},
    "onedrive": {"domain": "microsoft.com", "color": "#0078D4", "letter": "O"},
    "icloud": {"domain": "icloud.com", "color": "#3693F3", "letter": "I"},
    "box": {"domain": "box.com", "color": "#0061D5", "letter": "B"},
    "mega": {"domain": "mega.nz", "color": "#D9000F", "letter": "M"},
    "netflix": {"domain": "netflix.com", "color": "#E50914", "letter": "N"},
    "disneyplus": {"domain": "disneyplus.com", "color": "#113CCF", "letter": "D"},
    "primevideo": {"domain": "amazon.com", "color": "#00A8E1", "letter": "P"},
    "hbomax": {"domain": "hbomax.com", "color": "#9B4DFF", "letter": "H"},
    "hulu": {"domain": "hulu.com", "color": "#1CE783", "letter": "H"},
    "crunchyroll": {"domain": "crunchyroll.com", "color": "#F47521", "letter": "C"},
    "twitch": {"domain": "twitch.tv", "color": "#9146FF", "letter": "T"},
    "amazon": {"domain": "amazon.com", "color": "#FF9900", "letter": "A"},
    "ebay": {"domain": "ebay.com", "color": "#E53238", "letter": "E"},
    "etsy": {"domain": "etsy.com", "color": "#F16522", "letter": "E"},
    "aliexpress": {"domain": "aliexpress.com", "color": "#FF4747", "letter": "A"},
    "zalando": {"domain": "zalando.com", "color": "#E40046", "letter": "Z"},
    "shopify": {"domain": "shopify.com", "color": "#7AB55C", "letter": "S"},
    "booking": {"domain": "booking.com", "color": "#003580", "letter": "B"},
    "airbnb": {"domain": "airbnb.com", "color": "#FF5A5F", "letter": "A"},
    "expedia": {"domain": "expedia.com", "color": "#0066B3", "letter": "E"},
    "tripadvisor": {"domain": "tripadvisor.com", "color": "#34E0A1", "letter": "T"},
    "skyscanner": {"domain": "skyscanner.com", "color": "#F05A28", "letter": "S"},
    "notion": {"domain": "notion.so", "color": "#000000", "letter": "N"},
    "trello": {"domain": "trello.com", "color": "#0052CC", "letter": "T"},
    "asana": {"domain": "asana.com", "color": "#F06A6A", "letter": "A"},
    "monday": {"domain": "monday.com", "color": "#FF5252", "letter": "M"},
    "slack": {"domain": "slack.com", "color": "#4A154B", "letter": "S"},
    "teams": {"domain": "microsoft.com", "color": "#6264A7", "letter": "T"},
    "zoom": {"domain": "zoom.us", "color": "#2D8CFF", "letter": "Z"},
    "googleworkspace": {"domain": "google.com", "color": "#4285F4", "letter": "G"},
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


TR = {
    "de": {
        "app_name_a": "Mango", "app_name_b": "Safe",
        "all_entries": "Alle Einträge", "favorites": "Favoriten", "settings": "Einstellungen",
        "local_secure_title": "100% lokal & sicher",
        "local_secure_body": "Deine Daten bleiben nur auf deinem Gerät.",
        "search_placeholder": "Suchen...",
        "found_results": "Gefundene Ergebnisse:",
        "no_entries": "Noch keine Einträge gespeichert.",
        "no_favorites": "Noch keine Favoriten.",
        "no_matches": "Keine Treffer für '{q}'.",
        "new_entry": "Neuer Eintrag",
        "edit_entry": "Eintrag bearbeiten",
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
        "windows_hello": "🔑 Mit Windows Hello entsperren",
        "language": "Sprache", "design_color": "Design-Farbe",
        "appearance": "Erscheinungsbild", "mode_dark": "Dunkel", "mode_light": "Hell",
        "lang_de": "Deutsch", "lang_en": "Englisch", "lang_ru": "Russisch",
        "error_site_required": "Bitte einen Website-/Programmnamen angeben.",
        "error_password_required": "Bitte ein Passwort angeben.",
        "auto_lock": "Auto-Sperre (Minuten)",
        "windows_hello_label": "Windows Hello verwenden",
        "password_strength": "Passwortstärke",
        "weak": "Schwach",
        "medium": "Mittel",
        "strong": "Stark",
        "generate_password": "Passwort generieren",
        "windows_hello_disabled": "Windows Hello ist in den Einstellungen deaktiviert.",
    },
    "en": {
        "app_name_a": "Mango", "app_name_b": "Safe",
        "all_entries": "All Entries", "favorites": "Favorites", "settings": "Settings",
        "local_secure_title": "100% Local & secure",
        "local_secure_body": "Your data stays only on your device.",
        "search_placeholder": "Search...",
        "found_results": "Results found:",
        "no_entries": "No entries saved yet.",
        "no_favorites": "No favorites yet.",
        "no_matches": "No matches for '{q}'.",
        "new_entry": "New Entry",
        "edit_entry": "Edit Entry",
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
        "windows_hello": "🔑 Unlock with Windows Hello",
        "language": "Language", "design_color": "Accent color",
        "appearance": "Appearance", "mode_dark": "Dark", "mode_light": "Light",
        "lang_de": "German", "lang_en": "English", "lang_ru": "Russian",
        "error_site_required": "Please enter a website/program name.",
        "error_password_required": "Please enter a password.",
        "auto_lock": "Auto-lock (minutes)",
        "windows_hello_label": "Use Windows Hello",
        "password_strength": "Password strength",
        "weak": "Weak",
        "medium": "Medium",
        "strong": "Strong",
        "generate_password": "Generate password",
        "windows_hello_disabled": "Windows Hello is disabled in the settings.",
    },
    "ru": {
        "app_name_a": "Mango", "app_name_b": "Safe",
        "all_entries": "Все записи", "favorites": "Избранное", "settings": "Настройки",
        "local_secure_title": "100% локально и безопасно",
        "local_secure_body": "Ваши данные остаются только на вашем устройстве.",
        "search_placeholder": "Поиск...",
        "found_results": "Найденные результаты:",
        "no_entries": "Пока нет сохранённых записей.",
        "no_favorites": "Пока нет избранного.",
        "no_matches": "Нет совпадений для '{q}'.",
        "new_entry": "Новая запись",
        "edit_entry": "Редактировать запись",
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
        "windows_hello": "🔑 Разблокировать через Windows Hello",
        "language": "Язык", "design_color": "Акцентный цвет",
        "appearance": "Оформление", "mode_dark": "Тёмный", "mode_light": "Светлый",
        "lang_de": "Немецкий", "lang_en": "Английский", "lang_ru": "Русский",
        "error_site_required": "Пожалуйста, укажите сайт/программу.",
        "error_password_required": "Пожалуйста, укажите пароль.",
        "auto_lock": "Автоблокировка (минуты)",
        "windows_hello_label": "Использовать Windows Hello",
        "password_strength": "Сложность пароля",
        "weak": "Слабый",
        "medium": "Средний",
        "strong": "Сильный",
        "generate_password": "Сгенерировать пароль",
        "windows_hello_disabled": "Windows Hello отключен в настройках.",
    },
}


class MangoSafeUI:
    def __init__(self, controller: "MangoSafeApp"):
        self._cached_entries: list["PasswordEntry"] = []
        self._entries_loaded = False
        self._icon_cache: dict[str, object] = {}
        self._icon_pending: dict[str, list[ctk.CTkLabel]] = {}

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
        self.root.minsize(860, 620)
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

        self._active_list_mode: Optional[str] = None
        self._last_page_kind: Optional[str] = None
        self._list_shell_built = False
        self._badge_wrap: Optional[ctk.CTkFrame] = None
        self._results_badge: Optional[ctk.CTkLabel] = None
        self._list_container: Optional[ctk.CTkScrollableFrame] = None
        self._search_field_widget: Optional[ctk.CTkEntry] = None
        self._row_pool: dict[str, tuple[ctk.CTkFrame, Callable]] = {}
        self._sync_generation = 0
        self._CHUNK_THRESHOLD = 20
        self._CHUNK_SIZE = 15
        self._pre_login_screen = "setup"
        self._pending_setup_submit = None
        self._pending_login_submit = None
        self._pending_login_hello = None


    def t(self, key: str, **kwargs) -> str:
        text = TR.get(self.lang, TR["de"]).get(key, key)
        return text.format(**kwargs) if kwargs else text

    @property
    def accent(self) -> str:
        return ACCENT_PALETTE.get(self.accent_key, ACCENT_PALETTE["purple"])

    @property
    def accent_hover(self) -> str:
        return ACCENT_HOVER.get(self.accent_key, ACCENT_HOVER["purple"])

    def run(self) -> None:
        self.root.mainloop()

    def close(self) -> None:
        self.root.destroy()

    def _on_close(self) -> None:
        self.close()

    def _notify_activity(self, _event=None) -> None:
        self.controller.notify_activity()

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
        self._list_shell_built = False
        self._last_page_kind = None
        self._badge_wrap = None
        self._results_badge = None
        self._list_container = None
        self._search_field_widget = None
        self._active_list_mode = None
        self._row_pool = {}
        for widget in self.content.winfo_children():
            widget.destroy()
        try:
            self.root.update_idletasks()
        except Exception:
            pass

    def _clear_page(self) -> None:
        try:
            self.root.update_idletasks()
        except Exception:
            pass
        self._close_open_menu()
        if self.page is not None:
            for widget in self.page.winfo_children():
                widget.destroy()
            self.page.update_idletasks()
        self._active_list_mode = None
        self._list_shell_built = False
        self._results_badge = None
        self._badge_wrap = None
        self._list_container = None
        self._search_field_widget = None
        self._row_pool = {}
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

    def _resolve_bg(self, parent, fallback: str) -> str:
        bg = parent.cget("fg_color")
        if isinstance(bg, (list, tuple)):
            bg = bg[1] if len(bg) > 1 else bg[0]
        if not bg or bg == "transparent":
            return fallback
        return bg

    def _logo(self, parent) -> ctk.CTkFrame:
        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        canvas = tk.Canvas(wrap, width=32, height=32, bg=self._resolve_bg(parent, COL_SIDEBAR),
                           highlightthickness=0)
        canvas.pack(side="left", padx=(0, 10))
        canvas.create_polygon(
            16, 1, 30, 7, 30, 17, 16, 31, 2, 17, 2, 7,
            fill="", outline=self.accent, width=2, smooth=True,
        )
        canvas.create_oval(9, 10, 24, 24, fill=self.accent, outline="")
        canvas.create_line(19, 10, 23, 5, fill=self.accent, width=2)
        a = ctk.CTkLabel(wrap, text=self.t("app_name_a"), font=FONT_LOGO, text_color=COL_TEXT)
        a.pack(side="left")
        b = ctk.CTkLabel(wrap, text=self.t("app_name_b"), font=FONT_LOGO, text_color=self.accent)
        b.pack(side="left")
        return wrap

    def _logo_stacked(self, parent) -> ctk.CTkFrame:
        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        canvas = tk.Canvas(wrap, width=56, height=56, bg=self._resolve_bg(parent, COL_BG), highlightthickness=0)
        canvas.pack(pady=(0, 12))
        canvas.create_polygon(
            28, 2, 52, 13, 52, 30, 28, 54, 4, 30, 4, 13,
            fill="", outline=self.accent, width=3, smooth=True,
        )
        canvas.create_oval(16, 18, 42, 42, fill=self.accent, outline="")
        canvas.create_line(33, 18, 40, 8, fill=self.accent, width=3)
        text_row = ctk.CTkFrame(wrap, fg_color="transparent")
        text_row.pack()
        ctk.CTkLabel(text_row, text=self.t("app_name_a"), font=("Segoe UI", 26, "bold"),
                     text_color=COL_TEXT).pack(side="left")
        ctk.CTkLabel(text_row, text=self.t("app_name_b"), font=("Segoe UI", 26, "bold"),
                     text_color=self.accent).pack(side="left")
        return wrap

    def _round_field(self, parent, placeholder: str, on_change=None) -> ctk.CTkEntry:
        entry = ctk.CTkEntry(
            parent, placeholder_text=placeholder, fg_color=COL_CARD,
            border_color=COL_BORDER, border_width=1, corner_radius=22,
            height=46, font=FONT_BODY, text_color=COL_TEXT,
            placeholder_text_color=COL_TEXT_DIM,
        )
        if on_change:
            entry.bind("<KeyRelease>", lambda e: on_change(entry.get()))
        return entry

    def _bind_debounced_search(self, entry: ctk.CTkEntry, callback, delay_ms: int = 400) -> None:
        def on_key(event=None) -> None:
            if event and event.keysym == "Escape":
                entry.delete(0, "end")
                self.controller.handle_search("")
                return
            if event and event.keysym == "BackSpace" and (event.state & 0x4):
                text = entry.get()
                pos = entry.index(tk.INSERT)
                if pos > 0:
                    start = text.rfind(' ', 0, pos)
                    if start == -1:
                        start = 0
                    else:
                        start += 1
                    entry.delete(start, pos)
                return
            if self._search_after_id is not None:
                try:
                    self.root.after_cancel(self._search_after_id)
                except Exception:
                    pass
            query = entry.get()
            self._search_after_id = self.root.after(delay_ms, lambda: callback(query))
        entry.bind("<KeyRelease>", on_key)

    def invalidate_cache(self) -> None:
        self._entries_loaded = False

    def _accent_button(self, parent, text: str, command, height=46, corner_radius=22) -> ctk.CTkButton:
        return ctk.CTkButton(
            parent, text=text, height=height, corner_radius=corner_radius,
            fg_color=self.accent, hover_color=self.accent_hover, font=FONT_BODY,
            command=command,
        )

    def show_setup_screen(self, on_submit: Callable[[str], None]) -> None:
        self._pre_login_screen = "setup"
        self._pending_setup_submit = on_submit
        self._clear_content()
        self._language_picker_corner()
        self._theme_picker_corner()
        card = ctk.CTkFrame(self.content, fg_color="transparent")
        card.place(relx=0.5, rely=0.5, anchor="center")
        self._logo_stacked(card).pack(pady=(0, 18))
        ctk.CTkLabel(card, text=self.t("welcome"), font=FONT_TITLE, text_color=COL_TEXT).pack(pady=(0, 8))
        ctk.CTkLabel(card, text=self.t("setup_hint"), font=FONT_LABEL, text_color=COL_TEXT_DIM).pack(pady=(0, 22))
        pw_entry = self._round_field(card, self.t("master_pw_placeholder"))
        pw_entry.configure(show="•", width=380, justify="center")
        pw_entry.pack(pady=(0, 16))
        pw_entry.bind("<Return>", lambda e: on_submit(pw_entry.get()))
        self._accent_button(card, self.t("create_vault"), lambda: on_submit(pw_entry.get())).pack(fill="x")
        self._bring_to_front_centered()
        pw_entry.focus_set()

    def show_login_screen(
        self, on_submit: Callable[[str], None], on_windows_hello: Callable[[], None],
        error: Optional[str] = None,
    ) -> None:
        self._pre_login_screen = "login"
        self._pending_login_submit = on_submit
        self._pending_login_hello = on_windows_hello
        self._clear_content()
        self._language_picker_corner()
        self._theme_picker_corner()
        card = ctk.CTkFrame(self.content, fg_color="transparent")
        card.place(relx=0.5, rely=0.5, anchor="center")
        self._logo_stacked(card).pack(pady=(0, 22))
        if error:
            ctk.CTkLabel(card, text=error, font=FONT_LABEL, text_color=COL_DANGER,
                         wraplength=380, justify="center").pack(pady=(0, 10))
        pw_entry = self._round_field(card, self.t("login_pin_placeholder"))
        pw_entry.configure(show="•", width=380, justify="center")
        pw_entry.pack(pady=(4, 16))
        pw_entry.bind("<Return>", lambda e: on_submit(pw_entry.get()))
        self._accent_button(card, self.t("unlock"), lambda: on_submit(pw_entry.get())).pack(fill="x", pady=(0, 12))
        ctk.CTkButton(
            card, text=self.t("windows_hello"), height=42, corner_radius=21,
            fg_color=COL_CARD, hover_color=COL_CARD_HOVER, text_color=COL_TEXT, font=FONT_LABEL,
            border_width=1, border_color=COL_BORDER,
            command=on_windows_hello,
        ).pack(fill="x")
        self._bring_to_front_centered()
        pw_entry.focus_set()

    def _language_picker_corner(self) -> None:
        wrap = ctk.CTkFrame(self.content, fg_color="transparent")
        wrap.place(relx=0.97, rely=0.04, anchor="ne")
        for code, label in (("de", "DE"), ("en", "EN"), ("ru", "RU")):
            active = self.lang == code
            ctk.CTkButton(
                wrap, text=label, width=38, height=30, corner_radius=8,
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
                wrap, text=self.t(label_key), width=64, height=30, corner_radius=8,
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

    def _ensure_shell(self) -> None:
        if self._shell_built:
            return
        self._clear_content()
        self.sidebar = ctk.CTkFrame(self.content, fg_color=COL_SIDEBAR, width=SIDEBAR_WIDTH, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        self._logo(self.sidebar).pack(anchor="w", padx=20, pady=(24, 28))
        self._add_nav_button("all", self.t("all_entries"))
        self._add_nav_button("favorites", self.t("favorites"))
        self._add_nav_button("settings", self.t("settings"), show_badge=False)
        spacer = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        spacer.pack(fill="both", expand=True)
        info = ctk.CTkFrame(self.sidebar, fg_color="#241E33", corner_radius=16)
        info.pack(fill="x", padx=16, pady=18, side="bottom")
        ctk.CTkLabel(info, text="🛡", font=("Segoe UI", 18), text_color=self.accent).pack(
            anchor="w", padx=16, pady=(14, 2))
        ctk.CTkLabel(info, text=self.t("local_secure_title"), font=("Segoe UI", 13, "bold"),
                     text_color=self.accent).pack(anchor="w", padx=16)
        ctk.CTkLabel(info, text=self.t("local_secure_body"), font=("Segoe UI", 11),
                     text_color=COL_TEXT_DIM, wraplength=190, justify="left").pack(
            anchor="w", padx=16, pady=(2, 14))
        self.page = ctk.CTkFrame(self.content, fg_color=COL_BG)
        self.page.pack(side="left", fill="both", expand=True)
        self._shell_built = True
        self._update_nav_active()

    def _add_nav_button(self, view: str, label: str, show_badge: bool = True) -> None:
        row = ctk.CTkButton(
            self.sidebar, text=f"  {label}", anchor="w", height=42, corner_radius=12,
            font=FONT_NAV, command=lambda: self._switch_view(view),
        )
        row.pack(fill="x", padx=16, pady=5)
        self._nav_buttons[view] = row
        if show_badge:
            active = self._current_view == view
            badge = ctk.CTkLabel(
                row, text="0", font=("Segoe UI", 11, "bold"), text_color="white",
                corner_radius=10, width=22, height=20,
                fg_color=self.accent_hover if active else "#2A2740",
                bg_color=self.accent if active else COL_SIDEBAR,
            )
            badge.place(relx=0.93, rely=0.5, anchor="e")
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
                fg_color=self.accent_hover if active else "#2A2740",
                bg_color=self.accent if active else COL_SIDEBAR,
            )

    def _update_nav_counts(self) -> None:
        n_all = len(self._all_entries)
        n_fav = sum(1 for e in self._all_entries if e.favorite)
        if "all" in self._nav_badges:
            self._nav_badges["all"].configure(text=str(n_all))
        if "favorites" in self._nav_badges:
            self._nav_badges["favorites"].configure(text=str(n_fav))

    def _switch_view(self, view: str) -> None:
        self._current_view = view
        self._update_nav_active()
        self._render_page_for_current_view()

    def _render_page_for_current_view(self) -> None:
        if self._current_view == "settings":
            self._clear_page()
            self._render_settings_page()
            self._last_page_kind = "settings"
            return
        if self._last_page_kind == "settings":
            self._clear_page()
        self._last_page_kind = "list"
        if self._current_view == "favorites":
            entries = [e for e in self._all_entries if e.favorite]
            empty_text = self.t("no_favorites")
        else:
            entries = self._all_entries
            empty_text = self.t("no_entries")
        self._render_list_page(entries, empty_text)

    def show_main_screen(self, entries: list["PasswordEntry"]) -> None:
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

    def _build_top_bar(self) -> ctk.CTkEntry:
        top = ctk.CTkFrame(self.page, fg_color="transparent")
        top.pack(fill="x", padx=28, pady=(28, 18))
        top.grid_columnconfigure(0, weight=1)
        search = self._round_field(top, self.t("search_placeholder"))
        self._bind_debounced_search(search, self.controller.handle_search)
        search.grid(row=0, column=0, sticky="ew", padx=(0, 14))
        ctk.CTkButton(
            top, text="+", width=46, height=46, corner_radius=23,
            fg_color=self.accent, hover_color=self.accent_hover, font=("Segoe UI", 20, "bold"),
            command=self.controller.request_add_entry,
        ).grid(row=0, column=1)
        self._search_field_widget = search
        return search

    def _ensure_list_shell(self) -> None:
        if self._list_shell_built:
            return
        self._build_top_bar()
        self._badge_wrap = ctk.CTkFrame(self.page, fg_color="transparent", height=1)
        self._badge_wrap.pack(fill="x", padx=28)
        self._results_badge = ctk.CTkLabel(
            self._badge_wrap, text=self.t("found_results"), font=FONT_LABEL, text_color=COL_TEXT_DIM,
            fg_color=COL_CARD_HOVER, corner_radius=12, padx=14, pady=5,
        )
        self._list_container = ctk.CTkScrollableFrame(self.page, fg_color="transparent")
        self._list_container.pack(fill="both", expand=True, padx=28, pady=(0, 28))
        self._list_container.configure(
            scrollbar_button_color=self.accent,
            scrollbar_button_hover_color=self.accent_hover
        )
        self._list_container.unbind("<Configure>")
        self._list_container.bind("<Configure>", self._update_scrollregion)
        self._list_shell_built = True

    def _update_scrollregion(self, _event=None) -> None:
        canvas = getattr(self._list_container, "_parent_canvas", None)
        if canvas is not None:
            try:
                canvas.configure(scrollregion=canvas.bbox("all"))
            except Exception:
                pass

    @contextlib.contextmanager
    def _suspend_scrollbar_updates(self):
        container = self._list_container
        if container is None:
            yield
            return
        container.unbind("<Configure>")
        try:
            yield
        finally:
            container.bind("<Configure>", self._update_scrollregion)
            self._update_scrollregion()

    def _apply_list_look(self) -> None:
        if self._results_badge is not None and self._results_badge.winfo_ismapped():
            self._results_badge.pack_forget()
        self._list_container.configure(fg_color="transparent", corner_radius=0)

    def _apply_search_look(self) -> None:
        if self._results_badge is not None and not self._results_badge.winfo_ismapped():
            self._results_badge.pack(anchor="w", pady=(0, 10))
        self._list_container.configure(fg_color=COL_CARD, corner_radius=18)

    def show_search_results(self, query: str, entries: list["PasswordEntry"]) -> None:
        self._ensure_shell()
        self._ensure_list_shell()
        self._apply_search_look()
        self._active_list_mode = "search"
        search = self._search_field_widget
        if search is not None and search.get() != query:
            search.delete(0, "end")
            search.insert(0, query)
        if search is not None:
            search.focus_set()
            search.icursor(len(query))
        self._sync_rows(self._list_container, entries, self.t("no_matches", q=query))

    def _render_list_page(self, entries: list["PasswordEntry"], empty_text: str) -> None:
        self._ensure_list_shell()
        self._apply_list_look()
        self._active_list_mode = "list"
        if self._search_field_widget is not None:
            self._search_field_widget.focus_set()
        self._sync_rows(self._list_container, entries, empty_text)

    def _create_letter_image(self, letter: str, bg_color: str, size: int = AVATAR_SIZE) -> Optional[ctk.CTkImage]:
        """Erzeugt ein quadratisches Bild mit einem zentrierten Buchstaben."""
        if not _PIL_OK:
            return None
        img = Image.new("RGBA", (size, size), bg_color)
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("segoeui.ttf", int(size * 0.55))
        except:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), letter, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (size - tw) // 2 - bbox[0]
        y = (size - th) // 2 - bbox[1]
        draw.text((x, y), letter, fill="white", font=font)
        return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))

    def _build_row(self, parent) -> tuple[ctk.CTkFrame, Callable]:
        row = ctk.CTkFrame(parent, fg_color=COL_CARD, corner_radius=16, height=72)
        row.grid_columnconfigure(1, weight=1)
        row.bind("<Enter>", lambda e: row.configure(fg_color=COL_CARD_HOVER))
        row.bind("<Leave>", lambda e: row.configure(fg_color=COL_CARD))

        avatar = ctk.CTkLabel(
            row, text="", font=("Segoe UI", 14, "bold"), text_color="white",
            fg_color=COL_CARD_HOVER, corner_radius=12, width=AVATAR_SIZE, height=AVATAR_SIZE,
        )
        avatar.grid(row=0, column=0, rowspan=2, padx=(16, 14), pady=16)

        site_label = tk.Label(row, text="", font=FONT_SITE, fg=COL_TEXT, bg=COL_CARD, bd=0)
        site_label.grid(row=0, column=1, sticky="w", pady=(14, 0))
        user_label = tk.Label(row, text="", font=("Segoe UI", 12), fg=COL_TEXT_DIM, bg=COL_CARD, bd=0)
        user_label.grid(row=1, column=1, sticky="w", pady=(0, 14))

        right = tk.Frame(row, bg=COL_CARD, bd=0)
        right.grid(row=0, column=2, rowspan=2, padx=16)

        pw_label = tk.Label(right, text="•" * 8, font=("Consolas", 13),
                           fg=COL_TEXT_DIM, bg=COL_CARD, bd=0, width=9, anchor="w")
        pw_label.pack(side="left", padx=(0, 12))

        state: dict = {"entry": None, "showing_pw": False}

        def toggle_pw() -> None:
            entry = state["entry"]
            if entry is None:
                return
            state["showing_pw"] = not state["showing_pw"]
            if state["showing_pw"]:
                pw = entry.password
                pw_label.configure(text=pw, width=max(9, len(pw)))
            else:
                pw_label.configure(text="•" * 8, width=9)

        def copy_pw() -> None:
            entry = state["entry"]
            if entry is None:
                return
            self.root.clipboard_clear()
            self.root.clipboard_append(entry.password)
            self.root.update_idletasks()
            self.show_toast(self.t("copied_toast", site=entry.site))

        def make_icon(text: str, command, font_size: int = 14) -> tk.Label:
            lbl = tk.Label(right, text=text, font=("Segoe UI", font_size), fg=COL_TEXT,
                           bg=COL_CARD, bd=0, cursor="hand2", width=2)
            lbl.pack(side="left", padx=3)
            lbl.bind("<Button-1>", lambda _e: command())
            lbl.bind("<Enter>", lambda _e: lbl.configure(bg=COL_CARD_HOVER))
            lbl.bind("<Leave>", lambda _e: lbl.configure(bg=COL_CARD))
            return lbl

        make_icon("👁", toggle_pw)
        make_icon("📋", copy_pw)
        menu_lbl = make_icon("⋮", lambda: None, font_size=16)
        menu_lbl.configure(font=("Segoe UI", 16, "bold"))
        menu_lbl.bind("<Button-1>", lambda _e: self._open_entry_menu(menu_lbl, state["entry"]))

        def apply(entry: "PasswordEntry") -> None:
            state["entry"] = entry
            state["showing_pw"] = False
            pw_label.configure(text="•" * 8, width=9)

            color, letter = _brand_for_site(entry.site)
           
            letter_img = self._create_letter_image(letter, color)
            avatar.configure(image=letter_img, text="", fg_color="transparent")
        
            self._load_icon_async(entry.site, avatar)

            star = "★ " if entry.favorite else ""
            site_label.configure(
                text=f"{star}{entry.site}",
                fg="#FFD700" if entry.favorite else COL_TEXT
            )
            user_label.configure(text=entry.username)

        return row, apply

    def _sync_rows(self, container, entries: list["PasswordEntry"], empty_text: str) -> None:
        placeholder = getattr(container, "_mangosafe_placeholder", None)
        if placeholder is not None:
            placeholder.destroy()
            container._mangosafe_placeholder = None

        wanted_ids = [e.entry_id for e in entries]
        wanted_set = set(wanted_ids)

        all_valid_ids = {e.entry_id for e in self._all_entries}
        for stale_id in [eid for eid in self._row_pool if eid not in all_valid_ids]:
            row, _apply = self._row_pool.pop(stale_id)
            row.destroy()
        for eid, (row, _apply) in self._row_pool.items():
            if eid not in wanted_set and row.winfo_ismapped():
                row.pack_forget()

        order_changed = wanted_ids != getattr(container, "_mangosafe_last_order", None)
        container._mangosafe_last_order = wanted_ids

        pending_new = sum(1 for e in entries if e.entry_id not in self._row_pool)

        self._sync_generation += 1
        generation = self._sync_generation

        def show_placeholder_if_empty() -> None:
            if not entries:
                label = ctk.CTkLabel(container, text=empty_text, font=FONT_BODY, text_color=COL_TEXT_DIM)
                label.pack(pady=44)
                container._mangosafe_placeholder = label

        if pending_new < self._CHUNK_THRESHOLD:
            with self._suspend_scrollbar_updates():
                for entry in entries:
                    self._sync_one_row(container, entry, order_changed)
            show_placeholder_if_empty()
            return

        if self._list_container is not None:
            self._list_container.unbind("<Configure>")

        def build_chunk(remaining: list["PasswordEntry"]) -> None:
            if generation != self._sync_generation:
                return
            try:
                if not container.winfo_exists():
                    return
            except Exception:
                return
            batch, rest = remaining[:self._CHUNK_SIZE], remaining[self._CHUNK_SIZE:]
            for entry in batch:
                self._sync_one_row(container, entry, order_changed=True)
            if rest:
                self.root.after(1, lambda: build_chunk(rest))
            else:
                if self._list_container is not None:
                    self._list_container.bind("<Configure>", self._update_scrollregion)
                    self._update_scrollregion()
                show_placeholder_if_empty()

        build_chunk(entries)

    def _sync_one_row(self, container, entry: "PasswordEntry", order_changed: bool) -> None:
        signature = (entry.site, entry.username, entry.password, entry.notes, entry.favorite)
        pooled = self._row_pool.get(entry.entry_id)
        if pooled is None:
            row, apply_fn = self._build_row(container)
            self._row_pool[entry.entry_id] = (row, apply_fn)
            apply_fn(entry)
            row._mangosafe_sig = signature
            row.pack(fill="x", pady=7)
            return
        row, apply_fn = pooled
        if getattr(row, "_mangosafe_sig", None) != signature:
            apply_fn(entry)
            row._mangosafe_sig = signature
        if order_changed:
            row.pack(fill="x", pady=7)

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
                    self.root.after(0, lambda a=avatar, d=domain, i=img: self._apply_icon(a, d, i))
                except Exception:
                    pass

    def _apply_icon(self, avatar: ctk.CTkLabel, domain: str, image) -> None:
        if getattr(avatar, "_mangosafe_pending_domain", None) != domain:
            return
        try:
            avatar.configure(image=image, text="", fg_color="transparent")
        except Exception:
            pass

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
        frame = ctk.CTkFrame(popup, fg_color=COL_CARD, corner_radius=14,
                             border_width=1, border_color=COL_BORDER)
        frame.pack(fill="both", expand=True)

        def item(label: str, command, danger: bool = False) -> None:
            btn = ctk.CTkButton(
                frame, text=label, anchor="w", height=46, corner_radius=10,
                fg_color="transparent", hover_color=COL_CARD_HOVER,
                text_color=COL_DANGER if danger else COL_TEXT, font=FONT_BODY,
                command=lambda: (self._close_open_menu(), command()),
            )
            btn.pack(fill="x", padx=8, pady=4)

        fav_label = self.t("favorite_off") if entry.favorite else self.t("favorite_on")
        item(fav_label, lambda: self.controller.request_toggle_favorite(entry.entry_id))
        item(self.t("edit"), lambda: self.controller.request_edit_entry(entry.entry_id))
        item(self.t("delete"), lambda: self._ask_delete(entry), danger=True)

        popup.update_idletasks()
        menu_w, menu_h = 240, 3 * 54 + 16
        x = widget.winfo_rootx() - menu_w + widget.winfo_width()
        y = widget.winfo_rooty() + widget.winfo_height() + 4
        popup.geometry(f"{menu_w}x{menu_h}+{max(x, 0)}+{y}")
        self._open_menu = popup
        popup.bind("<FocusOut>", lambda e: self._close_open_menu())
        popup.after(60, popup.focus_force)

    def _ask_delete(self, entry: "PasswordEntry") -> None:
        self.confirm_delete(entry, on_confirm=lambda: self.controller.request_delete_entry(entry.entry_id))

    def show_entry_form(self, existing_entry: Optional["PasswordEntry"],
                        on_save: Callable[[str, str, str, str], None]) -> None:
        overlay = ctk.CTkFrame(self.root, fg_color="#000000")
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)

        card = ctk.CTkFrame(overlay, fg_color=COL_CARD, corner_radius=20, width=460, height=540)
        card.place(relx=0.5, rely=0.5, anchor="center")
        card.pack_propagate(False)

        title = self.t("edit_entry") if existing_entry else self.t("new_entry")
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(20, 8))
        ctk.CTkLabel(header, text=title, font=FONT_TITLE, text_color=COL_TEXT).pack(side="left")
        ctk.CTkButton(header, text="✕", width=28, height=28, corner_radius=14, fg_color="transparent",
                      hover_color=COL_CARD_HOVER, text_color=COL_TEXT, command=overlay.destroy).pack(side="right")

        site = self._round_field(card, self.t("site_placeholder"))
        site.pack(fill="x", padx=24, pady=7)
        user = self._round_field(card, self.t("user_placeholder"))
        user.pack(fill="x", padx=24, pady=7)

        pw_row = ctk.CTkFrame(card, fg_color="transparent")
        pw_row.pack(fill="x", padx=24, pady=7)
        pw_row.grid_columnconfigure(0, weight=1)
        password = self._round_field(pw_row, self.t("pw_placeholder"))
        password.configure(show="•")
        password.grid(row=0, column=0, sticky="ew")

        def generate_password() -> None:
            chars = string.ascii_letters + string.digits + "!@#$%^&*()-_=+[]{}|;:,.<>?"
            pw = ''.join(secrets.choice(chars) for _ in range(16))
            password.delete(0, "end")
            password.insert(0, pw)
            update_strength()

        gen_btn = ctk.CTkButton(pw_row, text="🔑", width=38, height=38, corner_radius=19,
                                fg_color=COL_CARD_HOVER, hover_color=COL_BORDER, text_color=COL_TEXT,
                                command=generate_password)
        gen_btn.grid(row=0, column=1, padx=(4, 0))

        def toggle_visibility():
            password.configure(show="" if password.cget("show") else "•")

        eye_btn = ctk.CTkButton(pw_row, text="👁", width=38, height=38, corner_radius=19,
                                fg_color=COL_CARD_HOVER, hover_color=COL_BORDER, text_color=COL_TEXT,
                                command=toggle_visibility)
        eye_btn.grid(row=0, column=2, padx=(4, 0))

        strength_label = ctk.CTkLabel(card, text="", font=FONT_LABEL, text_color=COL_TEXT_DIM)
        strength_label.pack(fill="x", padx=24, pady=(0, 7))

        def update_strength():
            pw = password.get()
            if not pw:
                strength_label.configure(text="")
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
                text, color = self.t("medium"), "#F59E0B"  
            else:
                text, color = self.t("strong"), "#10B981"  
            strength_label.configure(text=f"{self.t('password_strength')}: {text}", text_color=color)

        password.bind("<KeyRelease>", lambda e: update_strength())
        self.root.after(100, update_strength)

        notes = self._round_field(card, self.t("notes_placeholder"))
        notes.pack(fill="x", padx=24, pady=7)

        if existing_entry:
            site.insert(0, existing_entry.site)
            user.insert(0, existing_entry.username)
            password.insert(0, existing_entry.password)
            notes.insert(0, existing_entry.notes)
            self.root.after(200, update_strength)
        def submit():
            on_save(site.get(), user.get(), password.get(), notes.get())
            overlay.destroy()

        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x", padx=24, pady=(20, 22), side="bottom")
        ctk.CTkButton(btn_row, text=self.t("cancel"), height=44, corner_radius=22,
                      fg_color=COL_CARD_HOVER, hover_color=COL_BORDER, text_color=COL_TEXT,
                      command=overlay.destroy).pack(side="left", expand=True, fill="x", padx=(0, 7))
        self._accent_button(btn_row, self.t("save"), submit).pack(side="left", expand=True, fill="x", padx=(7, 0))
        site.focus_set()

    def _render_settings_page(self) -> None:
        wrap = ctk.CTkFrame(self.page, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=36, pady=36)

        ctk.CTkLabel(wrap, text=self.t("settings"), font=FONT_TITLE, text_color=COL_TEXT).pack(
            anchor="w", pady=(0, 28))

        ctk.CTkLabel(wrap, text=self.t("language"), font=("Segoe UI", 14, "bold"),
                     text_color=COL_TEXT).pack(anchor="w", pady=(0, 10))
        lang_options = {"de": self.t("lang_de"), "en": self.t("lang_en"), "ru": self.t("lang_ru")}
        lang_var = tk.StringVar(value=lang_options.get(self.lang, self.t("lang_de")))
        def on_lang_pick(choice: str):
            code = next((k for k, v in lang_options.items() if v == choice), "de")
            self.lang = code
            self.controller.set_language(code)
            self._clear_content()
            self.show_main_screen(self._all_entries)
            self._switch_view("settings")
        ctk.CTkOptionMenu(
            wrap, values=list(lang_options.values()), variable=lang_var,
            command=on_lang_pick, fg_color=COL_CARD, button_color=self.accent,
            button_hover_color=self.accent_hover, dropdown_fg_color=COL_CARD,
            text_color=COL_TEXT, dropdown_text_color=COL_TEXT,
            dropdown_hover_color=COL_CARD_HOVER,
            width=240, height=42, corner_radius=14, font=FONT_BODY,
        ).pack(anchor="w", pady=(0, 28))

        ctk.CTkLabel(wrap, text=self.t("auto_lock"), font=("Segoe UI", 14, "bold"),
                     text_color=COL_TEXT).pack(anchor="w", pady=(0, 10))
        lock_frame = ctk.CTkFrame(wrap, fg_color="transparent")
        lock_frame.pack(anchor="w", fill="x", pady=(0, 28))
        current_minutes = getattr(self.controller.config, "auto_lock_minutes", 2)
        lock_slider = ctk.CTkSlider(lock_frame, from_=1, to=30, number_of_steps=29,
                                    command=lambda v: lock_label.configure(text=f"{int(v)} min"))
        lock_slider.set(current_minutes)
        lock_slider.pack(side="left", fill="x", expand=True, padx=(0, 10))
        lock_label = ctk.CTkLabel(lock_frame, text=f"{int(lock_slider.get())} min", font=FONT_BODY, text_color=COL_TEXT)
        lock_label.pack(side="left")
        lock_slider.bind("<ButtonRelease-1>", lambda e: self.controller.set_auto_lock_minutes(int(lock_slider.get())))

        ctk.CTkLabel(wrap, text=self.t("windows_hello_label"), font=("Segoe UI", 14, "bold"),
                     text_color=COL_TEXT).pack(anchor="w", pady=(0, 10))
        hello_var = tk.BooleanVar(value=getattr(self.controller.config, "use_windows_hello", True))
        hello_switch = ctk.CTkSwitch(wrap, text="", variable=hello_var,
                                     command=lambda: self.controller.set_use_windows_hello(hello_var.get()))
        hello_switch.pack(anchor="w", pady=(0, 28))

        ctk.CTkLabel(wrap, text=self.t("design_color"), font=("Segoe UI", 14, "bold"),
                     text_color=COL_TEXT).pack(anchor="w", pady=(0, 10))
        swatch_row = ctk.CTkFrame(wrap, fg_color="transparent")
        swatch_row.pack(anchor="w", pady=(0, 28))
        for key, hexval in ACCENT_PALETTE.items():
            border = 3 if key == self.accent_key else 0
            ctk.CTkButton(
                swatch_row, text="", width=38, height=38, corner_radius=19,
                fg_color=hexval, hover_color=hexval,
                border_width=border, border_color="white",
                command=lambda k=key: self._pick_accent(k),
            ).pack(side="left", padx=7)

        ctk.CTkLabel(wrap, text=self.t("appearance"), font=("Segoe UI", 14, "bold"),
                     text_color=COL_TEXT).pack(anchor="w", pady=(0, 10))
        mode_row = ctk.CTkFrame(wrap, fg_color="transparent")
        mode_row.pack(anchor="w")
        for mode_key, label_key in (("dark", "mode_dark"), ("light", "mode_light")):
            active = self.theme_mode == mode_key
            ctk.CTkButton(
                mode_row, text=self.t(label_key), width=110, height=40, corner_radius=14,
                fg_color=self.accent if active else COL_CARD,
                hover_color=self.accent_hover if active else COL_CARD_HOVER,
                text_color="white" if active else COL_TEXT, font=FONT_BODY,
                border_width=0 if active else 1, border_color=COL_BORDER,
                command=lambda m=mode_key: self._pick_theme_mode(m),
            ).pack(side="left", padx=(0, 10))

    def _pick_theme_mode(self, mode: str) -> None:
        self.theme_mode = mode
        apply_theme(mode)
        self.controller.set_theme_mode(mode)
        self.root.configure(fg_color=COL_BG)
        self._clear_content()
        self.show_main_screen(self._all_entries)
        self._switch_view("settings")

    def _pick_accent(self, key: str) -> None:
        self.accent_key = key
        self.controller.set_accent_color(key)
        self._clear_content()
        self.show_main_screen(self._all_entries)
        self._switch_view("settings")

    def show_toast(self, message: str) -> None:
        if self._toast_label is not None:
            self._toast_label.destroy()
        if self.theme_mode == "light":
            bg_color = "#E8E5F1"
            text_color = "#0D0C13"
        else:
            bg_color = self.accent
            text_color = "white"
        self._toast_label = ctk.CTkLabel(
            self.root, text=message, font=FONT_LABEL, text_color=text_color,
            fg_color=bg_color, corner_radius=18, padx=18, pady=9,
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