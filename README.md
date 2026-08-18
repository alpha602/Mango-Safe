# 🥭 MangoSafe
MangoSafe ist ein lokaler, verschlüsselter Passwort-Manager mit Fokus auf Privatsphäre und Benutzerfreundlichkeit.
Alle deine Zugangsdaten bleiben ausschließlich auf deinem Gerät – keine Cloud, kein Sync, keine Kompromisse.
# ✨ Features
🔒 Ende-zu-Ende-Verschlüsselung – AES-256 mit PBKDF2 (480.000 Iterationen) und HMAC-Integritätsschutz.

👤 Master-Passwort & Windows Hello – Entsperre per Master-Passwort oder optional per PIN, Fingerabdruck oder Gesichtserkennung.

⏱️ Auto-Sperre – Tresor sperrt sich nach einstellbarer Inaktivität (Standard: 2 Minuten).

🛡️ Sicherheits-Wipe – Nach 3 fehlgeschlagenen Anmeldeversuchen wird der Tresor sicher gelöscht (Schutz vor Diebstahl).

🔍 Intelligente Suche – Durchsucht Websites und Benutzernamen, inkl. automatischer Indexierung.

⭐ Favoriten – Markiere wichtige Einträge für den schnellen Zugriff.

🖼️ Website-Icons – Lädt automatisch Favicons herunter und zeigt sie als Erkennungsbild an.

🔑 Passwort-Generator – Erstellt sichere Passwörter (16 Zeichen, Sonderzeichen inklusive).

📊 Passwortstärke – Visuelle Bewertung der eingegebenen Passwörter.

🌍 Mehrsprachig – Deutsch, Englisch und Russisch (automatische Erkennung der Systemsprache).

🎨 Modernes UI – Dunkel-/Hellmodus und 10 verschiedene Akzentfarben (CustomTkinter).
# 📸 Screenshots:
Login: <img width="2871" height="1658" alt="Screenshot 2026-08-18 153821" src="https://github.com/user-attachments/assets/43cfd06b-c323-4cb4-8850-605b2420dc14" />
Settings: <img width="2879" height="1642" alt="Screenshot 2026-08-18 153904" src="https://github.com/user-attachments/assets/2df9fda9-c8cf-4c33-97ed-44b98077b2a9" />
Main: <img width="2879" height="1664" alt="Screenshot 2026-08-18 153854" src="https://github.com/user-attachments/assets/5e0dd2f0-b8d3-43bb-86f8-1003a0888af9" />
# 🚀 Installation:
Voraussetzungen:
Python 3.10 oder neuer (falls du die Quelldateien ausführst)
Für die Windows Hello-Integration wird Windows 10/11 benötigt.
- - -
Aus dem Quellcode starten:<img width="459" height="250" alt="Screenshot 2026-08-18 154620" src="https://github.com/user-attachments/assets/2f89e7ec-61d4-4ca2-b045-4813f18cca8d" />

- - - 
Als eigenständige .exe (nur Windows):
Führe einfach die mitgelieferte "build.bat" aus.
Sie installiert alle Abhängigkeiten und erstellt eine einzelne MangoSafe.exe im Ordner dist/.
# 📦 Abhängigkeiten:
customtkinter – moderne GUI
cryptography – Verschlüsselung
pywin32 & winsdk – Windows Hello-Integration (nur Windows)
pillow – Bildverarbeitung für Icons
pyinstaller – zum Erstellen der .exe (nur Build)
Die vollständige Liste findest du in der requirements.txt.

# 🏗️ Build-Anleitung (für Windows-Executable):
1. Stelle sicher, dass du dich im Projektordner befindest.
2. Doppelklicke auf build.bat oder führe sie in der Kommandozeile aus.
3. Die fertige MangoSafe.exe liegt anschließend im Unterordner dist/.
4. Hinweis: Die .exe ist portabel – du kannst sie auf jeden beliebigen Ordner kopieren und direkt starten.
# ⚙️ Technische Details:
Verschlüsselung: Fernet (AES-256-CBC) mit HMAC-SHA256 zur Integrität.
Schlüsselableitung: PBKDF2-HMAC-SHA256 mit 480.000 Iterationen und 16-Byte-Salt.
Speicherort: depends on where you open the .bat
Windows: %APPDATA%\MangoSafe\vault.dat
Linux/macOS: ~/.mangosafe/vault.dat
Konfiguration: config.json im selben Verzeichnis.
# 📄 Lizenz:
Dieses Projekt steht unter der MIT-Lizenz – du darfst es frei nutzen, ändern und verbreiten.
Siehe LICENSE für Details. Ich nehme KEINERLEI Verantwortung.
# ❗ Sicherheitshinweis:
Master-Passwort vergessen? Es gibt KEINE Wiederherstellungsmöglichkeit – deine Daten sind dann verloren.
Der Tresor wird nur im Arbeitsspeicher entschlüsselt; bei Sperrung wird der Schlüssel sicher gelöscht.
Verwende ein starkes Master-Passwort (mindestens 8 Zeichen, am besten 12+ mit Sonderzeichen).
Notiere dir am besten dein Passwort.

# 🤝 Mitwirken:
Du hast einen Fehler gefunden oder eine Idee für ein neues Feature?
Öffne gerne ein Issue oder melde dich auf Discord. Beiträge sind willkommen!

🧑‍💻 Autor:
Erstellt mit ❤️ von [Dein Name/GitHub-Name] – bei Fragen oder Anregungen erreichst du mich unter [deine E-Mail oder Twitter].

MangoSafe – Deine Daten. Deine Frucht. Deine Sicherheit. 🥭🔒
