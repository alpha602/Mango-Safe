# 🥭 MangoSafe 0.5.0

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

Login: <img width="1152" height="802" alt="Screenshot 2026-10-13 231157" src="https://github.com/user-attachments/assets/87476f2c-ac55-492b-8ade-98e95b28b361" />

Settings: <img width="1149" height="799" alt="Screenshot 2026-10-13 231440" src="https://github.com/user-attachments/assets/b693c05a-81d6-4a55-99fb-a5a9de1d8f20" />
          <img width="1149" height="801" alt="Screenshot 2026-10-13 231525" src="https://github.com/user-attachments/assets/0e71ae36-970b-436f-ab79-c75e0e12c78e" />

Main: <img width="1148" height="803" alt="Screenshot 2026-10-13 231813" src="https://github.com/user-attachments/assets/96b5a659-2d19-4ff9-a5f9-467b88e6b576" />

# 🚀 Installation:

**Prerequisites:**

**Python 3.10 or newer (if you are running the source files).**

**Windows 10/11 is required for Windows Hello integration.**

- - -

# 🏗️ Build/Install instructions (for Windows executable):

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

**Created with ❤️ by [Mango / https://github.com/alpha602] and partly by AI [Deepseek, Claude, Qwen]  – for questions or suggestions, you can reach me at [DC: Fiddlesticksz].**

# MangoSafe – Your data. Your fruit. Your security. 🥭🔒
