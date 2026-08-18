# 🥭 MangoSafe

**MangoSafe is a local, encrypted password manager focused on privacy and user-friendliness.**

**All your credentials remain exclusively on your device – no cloud, no sync, no compromises.**

# ✨ Features

- 🔒 **End‑to‑end encryption** – AES‑256 with PBKDF2 (480,000 iterations) and HMAC integrity protection.

- 👤 **Master password & Windows Hello** – Unlock with your master password, or optionally with PIN, fingerprint, or facial recognition.

- ⏱️ **Auto‑lock** – The vault locks itself after a configurable period of inactivity (default: 2 minutes).

- 🛡️ **Security wipe** – After 3 failed login attempts, the vault is securely deleted (protection against theft).

- 🔍 **Smart search** – Searches through websites and usernames, including automatic indexing.

- ⭐ **Favorites** – Mark important entries for quick access.

- 🖼️ **Website icons** – Automatically downloads favicons and displays them as visual identifiers.

- 🔑 **Password generator** – Creates secure passwords (16 characters, including special characters).

- 📊 **Password strength** – Visual assessment of the passwords you enter.

- 🌍 **Multilingual** – German, English, and Russian (automatic detection of system language).

- 🎨 **Modern UI** – Dark/light mode and 10 different accent colors (CustomTkinter).

# 📸 Screenshots:

Login: <img width="2871" height="1658" alt="Screenshot 2026-08-18 153821" src="https://github.com/user-attachments/assets/43cfd06b-c323-4cb4-8850-605b2420dc14" />

Settings: <img width="2879" height="1642" alt="Screenshot 2026-08-18 153904" src="https://github.com/user-attachments/assets/2df9fda9-c8cf-4c33-97ed-44b98077b2a9" />

Main: <img width="2879" height="1664" alt="Screenshot 2026-08-18 153854" src="https://github.com/user-attachments/assets/5e0dd2f0-b8d3-43bb-86f8-1003a0888af9" />

# 🚀 Installation:

**Prerequisites:**

**Python 3.10 or newer (if you are running the source files).**

**Windows 10/11 is required for Windows Hello integration.**

- - -

**Run from source:**

<img width="459" height="250" alt="Screenshot 2026-08-18 154620" src="https://github.com/user-attachments/assets/2f89e7ec-61d4-4ca2-b045-4813f18cca8d" />

- - -

**As a standalone .exe (Windows only):**

**Simply run the included "build.bat".**

**It installs all dependencies and creates a single MangoSafe.exe in the dist/ folder.**

# 📦 Dependencies:

- customtkinter – modern GUI

- cryptography – encryption

- pywin32 & winsdk – Windows Hello integration (Windows only)

- pillow – image processing for icons

- pyinstaller – for building the .exe (build only)

**The full list can be found in requirements.txt.**



# 🏗️ Build instructions (for Windows executable):

**1. Make sure you are in the project folder.**

**2. Double-click build.bat or run it from the command line.**

**3. The finished MangoSafe.exe will then be located in the dist/ subfolder.**

**4. Note: The .exe is portable – you can copy it to any folder and run it directly.**

# ⚙️ Technical details:

- Encryption: Fernet (AES‑256‑CBC) with HMAC‑SHA256 for integrity.

- Key derivation: PBKDF2‑HMAC‑SHA256 with 480,000 iterations and a 16‑byte salt.

- Storage location: depends on where you open the .bat

- Windows: %APPDATA%\MangoSafe\vault.dat

- Linux/macOS: ~/.mangosafe/vault.dat

- Configuration: config.json in the same directory.

# 📄 License:

This project is licensed under the MIT License – you are free to use, modify, and distribute it.

See LICENSE for details. I assume NO liability.

# ❗ Security notice:

**Forgot your master password? There is NO recovery option – your data will be lost.**

**The vault is decrypted only in RAM; when locked, the key is securely erased.**

**Use a strong master password (at least 8 characters, preferably 12+ with special characters).**

**It is best to write down your password.**

# 🛡️ Virus scan

Virustotal: https://www.virustotal.com/gui/file/3b921f5671c35251c8ce7ef1993d0324654828b73c0fa24760fa6baca61c1002?nocache=1

This is the scan of the .exe itself.

- - -

**Reason for some flags:**

- The .exe contains a compressed Python interpreter

- When launched, it extracts these data to a temporary folder and runs the Python code from there.

- This „self‑extracting“ behaviour resembles that of many trojans, which is why it gets flagged.

- API calls are considered potentially malicious by some antivirus vendors because they are often abused.

- The .exe is not signed by a trusted certificate (I don’t want to pay annually lol)

# 🤝 Contributing:

**Found a bug or have an idea for a new feature?**

**Feel free to open an issue or reach out on Discord. Contributions are welcome!**

# 🧑‍💻 Author:

**Created with ❤️ by [Mango / https://github.com/alpha602] – for questions or suggestions, you can reach me at [DC: Fiddlesticksz].**

# MangoSafe – Your data. Your fruit. Your security. 🥭🔒
