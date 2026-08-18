🥭 MangoSafe
MangoSafe ist ein lokaler, verschlüsselter Passwort-Manager mit Fokus auf Privatsphäre und Benutzerfreundlichkeit.
Alle deine Zugangsdaten bleiben ausschließlich auf deinem Gerät – keine Cloud, kein Sync, keine Kompromisse.

✨ Features
🔒 Ende-zu-Ende-Verschlüsselung – AES-256 mit PBKDF2 (480.000 Iterationen) und HMAC-Integritätsschutz.

👤 Master-Passwort & Windows Hello – Entsperre per Master-Passwort oder optional per PIN, Fingerabdruck oder Gesichtserkennung.

⏱️ Auto-Sperre – Tresor sperrt sich nach einstellbarer Inaktivität (Standard: 2 Minuten).

🛡️ Sicherheits-Wipe – Nach 3 fehlgeschlagenen Anmeldeversuchen wird der Tresor sicher gelöscht (Schutz vor Diebstahl).
<img width="1894" height="816" alt="image" src="https://github.com/user-attachments/assets/9dab3ad7-0d62-4f22-97bb-a564dd406f13" />

🔍 Intelligente Suche – Durchsucht Websites und Benutzernamen, inkl. automatischer Indexierung.

⭐ Favoriten – Markiere wichtige Einträge für den schnellen Zugriff.

🖼️ Website-Icons – Lädt automatisch Favicons herunter und zeigt sie als Erkennungsbild an.

🔑 Passwort-Generator – Erstellt sichere Passwörter (16 Zeichen, Sonderzeichen inklusive).

📊 Passwortstärke – Visuelle Bewertung der eingegebenen Passwörter.

🌍 Mehrsprachig – Deutsch, Englisch und Russisch (automatische Erkennung der Systemsprache).

🎨 Modernes UI – Dunkel-/Hellmodus und 10 verschiedene Akzentfarben (CustomTkinter).

📸 Screenshots:
(Hier kannst du später Screenshots einfügen – z. B. Login, Hauptansicht, Einstellungen)

🚀 Installation:
Voraussetzungen:
Python 3.10 oder neuer (falls du die Quelldateien ausführst)
Für die Windows Hello-Integration wird Windows 10/11 benötigt.

Aus dem Quellcode starten:
bash
# Repository klonen
git clone https://github.com/dein-benutzername/mangosafe.git
cd mangosafe

# Requirements
pip install -r requirements.txt

# Programm ausführen
python main.py

Als eigenständige .exe (nur Windows):
Führe einfach die mitgelieferte build.bat aus.
Sie installiert alle Abhängigkeiten und erstellt eine einzelne MangoSafe.exe im Ordner dist/.

📦 Abhängigkeiten:
customtkinter – moderne GUI
cryptography – Verschlüsselung
pywin32 & winsdk – Windows Hello-Integration (nur Windows)
pillow – Bildverarbeitung für Icons
pyinstaller – zum Erstellen der .exe (nur Build)
Die vollständige Liste findest du in der requirements.txt.

🏗️ Build-Anleitung (für Windows-Executable):
Stelle sicher, dass du dich im Projektordner befindest.
2. Doppelklicke auf build.bat oder führe sie in der Kommandozeile aus.
3. Die fertige MangoSafe.exe liegt anschließend im Unterordner dist/.
4. Hinweis: Die .exe ist portabel – du kannst sie auf jeden beliebigen Ordner kopieren und direkt starten.

⚙️ Technische Details:
Verschlüsselung: Fernet (AES-256-CBC) mit HMAC-SHA256 zur Integrität.
Schlüsselableitung: PBKDF2-HMAC-SHA256 mit 480.000 Iterationen und 16-Byte-Salt.
Speicherort: depends on where you open the .bat
Windows: %APPDATA%\MangoSafe\vault.dat
Linux/macOS: ~/.mangosafe/vault.dat
Konfiguration: config.json im selben Verzeichnis.

📄 Lizenz:
Dieses Projekt steht unter der MIT-Lizenz – du darfst es frei nutzen, ändern und verbreiten.
Siehe LICENSE für Details. Ich nehme KEINERLEI Verantwortung.

❗ Sicherheitshinweis:
Master-Passwort vergessen? Es gibt KEINE Wiederherstellungsmöglichkeit – deine Daten sind dann verloren.
Der Tresor wird nur im Arbeitsspeicher entschlüsselt; bei Sperrung wird der Schlüssel sicher gelöscht.
Verwende ein starkes Master-Passwort (mindestens 8 Zeichen, am besten 12+ mit Sonderzeichen).
Notiere dir am besten dein Passwort.

🤝 Mitwirken:
Du hast einen Fehler gefunden oder eine Idee für ein neues Feature?
Öffne gerne ein Issue oder melde dich auf Discord. Beiträge sind willkommen!

🧑‍💻 Autor:
Erstellt mit ❤️ von [Dein Name/GitHub-Name] – bei Fragen oder Anregungen erreichst du mich unter [deine E-Mail oder Twitter].

MangoSafe – Deine Daten. Deine Frucht. Deine Sicherheit. 🥭🔒
