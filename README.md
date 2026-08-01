<h1 align="center">Martix</h1>

<p align="center"><strong>Real-time, private, and 100% local smart file organizer and disk space analyzer.</strong></p>

<p align="center">
  Martix runs silently in the background, monitors your Downloads folder, and automatically archives incoming files—powered by visual rules, content extraction, local OCR, or an optional local LLM running directly on your machine. Nothing leaves your computer. No file deletion is ever permanent.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python&logoColor=white" alt="Python 3.10+" />
  <img src="https://img.shields.io/badge/Flask-3.0%2B-black?style=flat-square&logo=flask&logoColor=white" alt="Flask 3" />
  <img src="https://img.shields.io/badge/Linux%20%7C%20macOS%20%7C%20Windows-lightgrey?style=flat-square" alt="Platforms" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" alt="MIT License" />
  <img src="https://img.shields.io/badge/telemetry-zero-success?style=flat-square" alt="Zero Telemetry" />
</p>

---

## Why Martix?

Your Downloads folder is often a chaotic dump: invoices, screenshots, ZIP archives, bank statements, and audio files. Manual organization is tedious and time-consuming, while cloud-based file management tools require uploading private documents to external servers.

Martix performs all organization locally on your device. No user accounts, no external servers, and zero telemetry.

**Strict Core Guarantee: No file deletion is permanent.** Everything deleted by Martix is safely dispatched to your system trash (or a local quarantine directory if unavailable). An application with permissions over your personal user directory must never perform irreversible actions.

---

## Key Features

### Automated Real-Time Archiving

Monitors your Downloads and user-selected folders in real time. Martix waits until downloads are fully settled—verifying file size stability and confirming no process holds an active write lock—before processing. Full directories (e.g., downloaded photo albums) are organized atomically as single units.

### Intelligent Content Classification

Martix evaluates incoming files using a priority cascade:

```
1. Custom User Rules     → e.g., "PDF containing 'invoice' → Documents/Invoices"
2. User Topics           → Keyword matching on filename and full text content
                           (PDF, DOCX, TXT, plus images via local Tesseract OCR)
3. Subcategories         → Pattern matching (screenshots, receipts, resumes, etc.)
4. Local LLM (Optional)  → Ollama running locally suggests an appropriate folder
5. Base Category         → Extension fallback as final resort
```

### Flexible Priority Rules

Multiple rules per extension with combined `AND` conditions over file name, size, age, text content, and metadata (EXIF/ID3). Drag-and-drop rule ordering ensures the highest-priority rule wins.

```
.pdf  +  content contains "invoice"       →  Documents/Invoices
.pdf  +  content contains "contract"      →  Documents/Contracts
.jpg  +  camera equals "NIKON Z6"        →  Photos/Reflex/{EXIF_DATE}
 *    +  age > 365 days                  →  Archive/{FILE_YYYY}
```

### Additional System Capabilities

- **Pattern-Based Dynamic Renaming** — Placeholders including `{YYYY}`, `{Topic}`, `{ARTIST}`, `{EXIF_DATE}`, `{OriginalName}`, and more.
- **Visual Disk Space Analyzer** — Interactive tree hierarchy with parent percentage utilization, extension breakdown, and an interactive HTML5 Canvas squarified treemap.
- **Fast Two-Phase Deduplication** — High-performance 64 KB fast-hash filtering followed by SHA256 verification to prevent unnecessary multi-gigabyte disk scans.
- **Safe Archive Extraction** — Automatic ZIP/TAR extraction with strict Zip-Slip protection, expansion limits, and path traversal guards. Original archives are preserved.
- **Scheduled Maintenance & Auto-Trash** — Automated age-based cleanup policies that route directly to trash.
- **Dry-Run Simulation Mode** — Preview rule evaluations and destination paths before applying changes.
- **One-Click Undo** — Revert moves directly from execution history logs.
- **Adaptive Rule Suggestions** — Suggests new rules when manual file corrections are detected.
- **Bilingual Interface** — English and Spanish UI with dark and light themes.

---

## Installation

### Windows: aplicación de escritorio

La distribución para usuarios no técnicos es `Martix.exe`. Al abrirlo se
inicia una ventana nativa y la patrulla funciona en segundo plano desde la
bandeja del sistema. No hay que abrir `localhost`, instalar Python ni usar
Chrome/Edge. El ejecutable usa un puerto efímero de loopback únicamente como
canal interno entre la ventana y el motor local; esa URL no se expone al
usuario ni acepta conexiones de red.

Para generar el ejecutable desde el código en Windows:

```powershell
cd backend
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pip install -r requirements-desktop.txt
.venv\Scripts\python.exe build_desktop.py
```

El resultado queda directamente en `Martix.exe`, en la carpeta principal del
proyecto. `backend\dist\Martix.exe` se conserva solo como copia técnica de
PyInstaller. Para instalarlo con arranque opcional al iniciar sesión:

```powershell
powershell -ExecutionPolicy Bypass -File backend\deploy\install_windows.ps1
```

### Automatic Installation (Linux)

```bash
git clone https://github.com/marcmarti9/martix.git
cd martix
./install.sh
```

`install.sh` builds the virtual environment, installs dependencies, registers application shortcuts, configures autostart/systemd services, and installs the global `martix` CLI command. To clean uninstall: `./uninstall.sh`.

### Manual Setup (Cross-Platform / desarrollo)

```bash
git clone https://github.com/marcmarti9/martix.git
cd martix/backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

For development, `python main.py` exposes the local web UI at
<http://127.0.0.1:5000>. The desktop entry point is `python desktop.py`; it
requires the desktop dependencies and opens only the native PyQt6 window (it
does not fall back to an external browser).

### Optional Integrations

| Feature | Requirement |
|---|---|
| Image OCR Content Extraction | Tesseract OCR (`sudo apt install tesseract-ocr`) |
| Local AI Classification | [Ollama](https://ollama.com) + `MARTIX_LLM=1` |
| Native Desktop Window / Windows `.exe` | `pip install -r requirements-desktop.txt` |

---

## Privacy Architecture

Privacy in Martix is enforced directly by codebase constraints:

- **Single Outbound Network Path:** The only permitted HTTP request across the entire repository is to a local LLM instance. Every outbound call validates that the target URL resolves strictly to a loopback address (`127.0.0.1` / `localhost`). Setting `MARTIX_LLM_URL` to a remote host causes Martix to reject the request and log a warning.
- **Local Host Binding:** Server binds strictly to `127.0.0.1`. Binding to external interfaces requires setting an explicit `MARTIX_TOKEN`.
- **Zero Telemetry:** No analytics, tracking code, user accounts, automatic update checks, or runtime Git/network calls.
- **Isolated Frontend Assets:** Interface assets are self-contained with no external CDN or remote font dependencies, enforced by a restrictive Content-Security-Policy (CSP).

Detailed threat models and security bounds are available in [docs/security.md](docs/security.md).

---

## Documentation

| Document | Description |
|---|---|
| [Architecture](docs/architecture.md) | Internal modular architecture and execution flow |
| [Security Model](docs/security.md) | Threat model, defense mechanisms, and bounds |
| [Configuration](docs/configuration.md) | Environment variables, categories, and settings |
| [REST API Reference](docs/api.md) | Endpoint reference specification |
| [Development Guide](docs/development.md) | Local environment setup, test suites, and conventions |
| [Architecture Decisions (ADR)](docs/decisions.md) | Architecture Decision Records (ADRs) |
| [July 2026 Audit Report](docs/audit-2026-07.md) | Comprehensive audit report and vulnerability fixes |
| [Project Roadmap](docs/roadmap.md) | Project status and prioritized feature backlog |

---

## Testing & Verification

```bash
cd backend
.venv/bin/python tests/test_all.py           # Integration test suite
.venv/bin/python tests/test_regressions.py   # Audit regression probes (27 test cases)
.venv/bin/python tests/test_security.py      # Live security attack probes (12 test cases)
```

The security and regression test suites do not merely check code constants; **they actively execute attack payloads against the running application**. Test execution isolated inside temporary `HOME` and SQLite database fixtures ensures zero side effects on user data.

---

## Current Status

Fully functional and in active daily production. The July 2026 security audit verified and resolved 16 logic bugs and 2 exploitable security vulnerabilities; comprehensive details are in [docs/audit-2026-07.md](docs/audit-2026-07.md).

Martix is an open-source personal software project. Always maintain independent backups of critical data before running automated file operations, and utilize **Simulation Mode** to verify rule outcomes.

---

## Contributing

Contributions and issue reports are welcome! Please review [CONTRIBUTING.md](CONTRIBUTING.md) and [docs/development.md](docs/development.md).

To report security concerns, please consult [SECURITY.md](SECURITY.md).

---

## License

Distributed under the [MIT License](LICENSE).
