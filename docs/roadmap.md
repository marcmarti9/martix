# Martix — Status & Project Roadmap

> Living document. Architecture decisions reference: [decisions.md](decisions.md).

Last updated: 2026-07-25.

---

## 1. Executive Overview

Martix is a real-time smart file organizer and visual disk space analyzer (Python/Flask + vanilla JS) tailored for user Downloads and directory management. It monitors directories in real time, classifies incoming files via visual rules, EXIF/ID3 metadata, keyword text extraction (with local OCR), or local LLM instances, and visualizes disk storage utilization using interactive tree views and canvas treemaps. 100% local: zero telemetry, zero analytics, and zero external network calls. Public repository: https://github.com/marcmarti9/martix (MIT License).

---

## 2. Implemented Core Features

### Classification Engine

1. Custom user rules with block-style conditions (filename, extension, file size, `age_days`, text content; combined with `AND`) configured via UI condition builder.
2. Topic keyword classification: scans filenames and PDF/DOCX/TXT text content, with local Tesseract OCR support for images.
3. Subcategory pattern matching (screenshots, invoices, receipts, resumes, etc.).
4. Safe archive extraction (`.zip`, `.tar`, `.tar.gz`) with Zip-Slip protection to classify internal archive contents.
5. Optional local LLM classification (Ollama, `MARTIX_LLM=1`) for fallback classification when preceding rules do not match. Disabled by default. Strictly bounded to `127.0.0.1`.
6. Base extension category fallback.

### Automation & Systems

- **Multi-Folder Real-Time Monitoring Daemon:** Watchdog monitoring across `DOWNLOADS_DIR` and custom monitored folders with dynamic thread pool allocation.
- **Background Task Scheduler:** Background execution thread for periodic maintenance sweeps and scheduled folder cleanups (`/api/scheduler/config`).
- Native desktop notifications (Linux `notify-send`, macOS `osascript`, Windows `powershell`).
- Dynamic pattern-based renaming with placeholders (`{YYYY}`, `{MM}`, `{DD}`, `{Topic}`, `{Category}`, `{OriginalName}`, `{ext}`).
- Scheduled maintenance cleanups: automated age-based folder retention rules routing directly to restorable trash.
- Fast two-phase duplicate detection (64 KB Fast-Hash + full SHA256) across arbitrary directories.
- **Visual Disk Space Analyzer:** Interactive directory tree showing parent folder percentages, extension breakdown tables, and interactive squarified canvas treemaps.
- Rule set export and import in JSON format (`/api/rules/export` and `/api/rules/import`).
- Single-level move undo support from execution history logs.
- Dry-run simulation mode (`/api/simulate`): preview organization outcomes without modifying files.
- Metrics dashboard: total organized count, top categories, 30-day activity metrics.

### Distribution & Integration

- **Unified 1-Click Installer & Uninstaller:** `install.sh` and `uninstall.sh`.
- Desktop application wrapper (`backend/desktop.py`): pywebview window mode.
- Single-click desktop build packaging: PyInstaller script (`backend/build_desktop.py`) producing standalone binaries under `backend/dist/`.
- System service integrations: systemd (Linux), LaunchAgent (macOS), Task Scheduler (Windows).
- Bilingual interface (English / Spanish) with dark/light themes.

### Security (see [security.md](security.md))

- Anti path-traversal safeguards: containment validated within `HOME_DIR`, with symlinks resolved prior to containment checks.
- Zip-Slip, escape link, absolute path, and archive bomb protection.
- CSRF and DNS-rebinding guards: Host and Origin header validation.
- Restrictive Content-Security-Policy and `X-Frame-Options: DENY` headers.
- SSRF prevention: outbound network calls strictly validated as loopback targets.
- Protected system paths (`~/.ssh`, `~/.config`, etc.) protected and hidden from UI browser listings.
- Mandatory non-destructive deletions: all deletions route to restorable trash.
- Optional API token authentication locally; **mandatory** when binding outside loopback.
- Auto-regenerating SQLite database with WAL journaling.

### Test Suites

- `backend/tests/test_all.py` — Integration test suite.
- `backend/tests/test_regressions.py` — 27 audit regression test cases.
- `backend/tests/test_security.py` — 12 active security attack test cases.

All suites passing cleanly in GitHub Actions CI workflows.

---

## 3. Competitive Landscape Comparison

| Feature | Martix | Hazel (macOS) | DropIt (Windows) | File Juggler (Windows) |
|---|---|---|---|---|
| Cross-Platform Support | ✅ | ❌ macOS only | ❌ Windows only | ❌ Windows only |
| Pricing Model | Free / Open Source | ~$42 USD | Free | ~$25 USD |
| Text Extraction + OCR | ✅ | ❌ | ❌ | Paid edition |
| Multi-Folder Monitoring | ✅ | ✅ | ✅ | ✅ |
| Metadata Rules (EXIF/ID3) | Partial (`age_days`, EXIF) | ✅ | Partial | Partial |
| Archive Extraction (.zip/.rar) | ✅ | ❌ | ✅ | ❌ |
| Local AI Classification | ✅ (Unique in segment) | ❌ | ❌ | ❌ |
| Integrated Deduplication | ✅ (Fast-Hash) | ❌ | Partial | ❌ |
| Automated Age Maintenance | ✅ | ✅ | ❌ | ✅ |
| Scheduled Task Engine (Cron) | ✅ | ✅ | ❌ | ✅ |
| Integrated Disk Space Analyzer | ✅ | ❌ | ❌ | ❌ |

---

## 4. Prioritized Feature Backlog

### Completed Milestone Features

- [x] **Real-time multi-folder monitoring daemon.** (2026-07-22) Real-time watchdog patrol across Downloads and custom monitored directories.
- [x] **Background task scheduler.** (2026-07-22) Background `TaskScheduler` thread for maintenance sweeps.
- [x] **Single-click desktop build packaging.** (2026-07-22) PyInstaller build script (`backend/build_desktop.py`).
- [x] **Visual Disk Space Analyzer.** (2026-07-24) Interactive directory tree, extension breakdown, and squarified canvas treemap.
- [x] **Unified 1-click installer and uninstaller.** (2026-07-24) Root scripts `install.sh` and `uninstall.sh`.
- [x] **Comprehensive security and quality audit.** (2026-07-25) Fixed 16 logic bugs and 2 security vulnerabilities; implemented regression and security test suites. See [audit-2026-07.md](audit-2026-07.md).
- [x] **Re-orderable rule priorities.** (2026-07-25) Support for multiple rules per file extension with drag-and-drop priority ordering.
- [x] **Mandatory restorable trash engine.** (2026-07-25) Implemented `app/trash.py`.
- [x] **Frontend Trash Management UI.** (2026-08-03) Full UI tab for viewing, restoring, purging individual or all quarantined items with active mode status.
- [x] **Batch Operation Reversal.** (2026-08-03) Multi-selection checkboxes in history log with `/api/log/undo-batch` endpoint.

### Pending Backlog Items

- [ ] **Logical OR & Nested Rule Condition Groups.** Expand rule conditions to support `{"any": [...]}` condition structures.
- [ ] **Incremental SSE Disk Scanning.** Replace POST scan requests with real-time Server-Sent Events progress reporting.
- [ ] **Rule Profile Presets.** Switchable rule profiles (e.g., "Work" vs "Personal").
- [ ] **Tax & Identifier Pattern Detection.** Add specialized financial rule condition extractors (tax IDs, invoice totals).
- [ ] **Pytest Runner Migration.** Refactor assertions into standard pytest test functions.

---

## 5. Development History

- **2026-07-19**: Initial release, security hardening, dry-run simulations, folder monitoring, usage statistics, and roadmap creation.
- **2026-07-22**: Multi-folder watchdog monitoring, task scheduler, PyInstaller build script, fast-hash deduplication.
- **2026-07-24**: Legacy Sortix cleanup, Visual Disk Space Analyzer implementation, unified installer/uninstaller scripts, Architecture Decision Records (ADR).
- **2026-07-25**: Comprehensive software and security audit. Resolved 16 logic bugs and 2 security vulnerabilities. Implemented mandatory trash module, rule priority ordering, automated test suites, documentation rewrite in English, and CI workflows.
