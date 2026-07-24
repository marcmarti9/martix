<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python Version" />
  <img src="https://img.shields.io/badge/Flask-3.0%2B-black?style=for-the-badge&logo=flask&logoColor=white" alt="Flask" />
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey?style=for-the-badge" alt="Platforms" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License" />
</p>

<h1 align="center">Martix</h1>
<p align="center"><strong>An intelligent, privacy-first, real-time file organizer for your desktop.</strong></p>
<p align="center">Martix runs quietly in the background, monitoring your Downloads and custom folders. It automatically classifies and files incoming documents, media, and archives using visual Scratch-like rules, content OCR, EXIF/ID3 metadata, or an optional 100% local LLM.</p>

---

## 💡 Why Martix?

Let’s be honest: your Downloads folder is probably an endless dumping ground of PDFs, invoices, screenshots, zip files, and music downloads. Manually moving them takes time, and cloud-based file organizers compromise your privacy.

Martix handles sensitive personal files (tax returns, bank statements, contracts, photos) right on your machine. It is designed **privacy-first from day one**:

* **100% Local Execution:** Zero cloud dependencies, zero telemetry, and zero external API calls. Your documents never leave your localhost.
* **Smart Content Classification:** Deep scans text in PDF, DOCX, and TXT files, and performs local OCR on images using Tesseract.
* **Strict Security Controls:** Safe path resolution strictly confined to your home directory (`~`), built-in anti-loop guards, anti-Zip-Slip protections for archives, and local API token protection.

---

## ✨ Features at a Glance

### 🚀 Real-Time Automation & Multi-Folder Patrol
* **Multi-Folder Real-Time Monitoring:** Monitors your Downloads directory and any active custom folders simultaneously in real-time. Safely waits for active downloads (`.crdownload`, `.part`) to complete before filing.
* **Background Task Scheduler:** Automatically runs periodic folder sweeps and scheduled auto-trash cleanups in the background without blocking the UI.
* **Native Desktop Notifications:** Sends non-intrusive system notifications whenever a file is filed or organized.

### 🧠 Smart Classification & Learning
* **Visual Scratch-Style Rule Builder:** Combine filename, extension, file size, age (`age_days`), and content conditions with AND logic.
* **Smart Learning from Corrections:** Corrected a file placement manually? Martix analyzes the correction (via heuristic patterns or your optional local Ollama LLM) and suggests a new rule with a single click.
* **Archive Handling (.zip / .tar):** Safely unpacks compressed archives in temporary sandboxes with Zip-Slip protection to analyze and organize internal contents.
* **EXIF & ID3 Tag Metadata:** Filter and rename files using photo EXIF data (camera model, capture date) and audio ID3 tags (artist, album, song title, year).
* **Dynamic Placeholders:** Custom file renaming templates using tags like `{YYYY}`, `{Topic}`, `{ARTIST}`, `{ALBUM}`, `{EXIF_DATE}`, and `{OriginalName}`.

### 🛠️ Utilities & Desktop Experience
* **📊 WizTree-Style Disk Space Visualizer:** Scan drives or folders to visualize space usage. Includes folder tree hierarchy (% of parent bars), file extension breakdown, and an interactive HTML5 Canvas treemap visualizer with 1-click file deletion.
* **⚡ 1-Click Installer & System Integration:** Run `./install.sh` to install Martix, register desktop app launchers, configure login autostart, enable background systemd services, and install the `martix` CLI terminal command.
* **Fast 2-Step Deduplication:** Quickly detects duplicate files across any selected directory using a lightweight 2-pass hashing approach (64KB fast-hash + full SHA256 verification).
* **Export & Import Rules:** Export your custom classification and maintenance rules to JSON files to share or backup.
* **Dry-Run Simulation:** Test how your rules will handle existing files before committing any actual moves.
* **1-Level Undo:** Accidental move? Undo filing actions directly from your History log.
* **Standalone Desktop App & 1-Click Packaging:** Run as a native desktop window via `pywebview` or package into a standalone binary using the built-in PyInstaller builder script.

---

## 🛠️ Getting Started

### Prerequisites
* **Python 3.10+**
* (Optional) **Tesseract OCR** for image text scanning.
* (Optional) **Ollama** (`MARTIX_LLM=1`) for local AI fallback suggestions.

### ⚡ 1-Click Installation & Desktop Integration
```bash
git clone https://github.com/marcmarti9/martix.git
cd martix
./install.sh
```
This automatically sets up Python dependencies, registers the desktop app launcher, configures auto-start on login, enables the background service, and installs the `martix` CLI command.

To uninstall at any time:
```bash
./uninstall.sh
```

### Quick Manual Run
```bash
cd martix/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```
Open your browser at `http://127.0.0.1:5000` to access the dashboard.

To launch in desktop app window mode:
```bash
python desktop.py
```

---

## 📦 Building a 1-Click Desktop Executable

Want a standalone executable binary without needing a Python setup?

```bash
cd backend
python build_desktop.py
```
The compiled binary will be placed inside `backend/dist/`.

---

## 🖥️ Native Desktop App & Autostart Setup

Martix can run as a **native standalone desktop application** (in its own dedicated window without any web browser UI) and start automatically whenever you log into your PC:

### Automatic Desktop & Startup Installation (Linux)
```bash
cd backend/deploy
./install_autostart_desktop.sh
```
This registers Martix in your desktop application menu (`~/.local/share/applications/martix.desktop`) and sets it to auto-launch on startup (`~/.config/autostart/martix.desktop`).

### Linux Service (Headless systemd user service)
```bash
cd backend/deploy
./install_linux.sh
```

### macOS (LaunchAgent)
```bash
cd backend/deploy
./install_macos.sh
```

### Windows (Scheduled Task)
```powershell
cd backend\deploy
powershell -ExecutionPolicy Bypass -File install_windows.ps1
```

*(To uninstall services, run the corresponding `./uninstall_...` script in `backend/deploy/`.)*


---

## 🧪 Testing

Martix features a comprehensive, isolated integration test suite:

```bash
cd backend
.venv/bin/python tests/test_all.py
```

---

## 📁 Project Structure

```
backend/
├── app/
│   ├── classifier.py      # Classification engine (Scratch rules, OCR, EXIF/ID3 tags)
│   ├── organizer.py       # File moves, renaming templates, zip unpacking, fast-hash dedup
│   ├── watcher.py         # Real-time multi-folder Watchdog patrol & desktop notifications
│   ├── scheduler.py       # Background TaskScheduler for cron cleanups & sweeps
│   ├── llm.py             # Local Ollama LLM integration & Smart Learning
│   ├── server.py          # REST API endpoints & rule import/export
│   ├── browser.py         # Safe path resolution (HOME_DIR restriction)
│   └── security.py        # Host/Origin validation, CSRF & privacy headers
├── build_desktop.py       # PyInstaller desktop packaging script
├── main.py                # Server entry point
├── desktop.py             # pywebview Desktop wrapper
└── tests/test_all.py      # Integration test suite (32 test blocks)

frontend/
├── index.html             # Web dashboard template
├── app.js                 # Dashboard UI logic, rule builder, duplicate tool, i18n
└── styles.css             # Responsive styling & themes
├── install.sh              # 1-Click installer wrapper
├── uninstall.sh            # 1-Click uninstaller wrapper
├── installer.py            # Unified cross-platform installer script
├── uninstaller.py          # Unified cross-platform uninstaller script
├── DECISIONS.md            # Architecture Decision Records (ADR)
├── ROADMAP.md              # Project status & backlog
```

---

## 📜 Architecture Decisions

All major design and architectural decisions (ADRs) are documented in [DECISIONS.md](DECISIONS.md).

---

## 🤝 Contributing

Contributions, bug reports, and feature suggestions are welcome! Please check out [CONTRIBUTING.md](CONTRIBUTING.md).

## 📄 License

Martix is open-source software licensed under the [MIT License](LICENSE).
Created with ❤️ by Marc Martí Torralba.
