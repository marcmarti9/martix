# Changelog

All notable changes to Martix will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

### Changed

- Replaced the indigo/glass SaaS look with an Apple Liquid Glass interface: system blue, optical layers, no neon.

### Fixed

- Settings button no longer loses its label on load.
- Disk analyzer dialog no longer stays visible when closed (`display: flex` overrode the native `<dialog>` hide).
- Deduplicate tab no longer starts a full scan just by opening Settings.
- Selecting a disk item no longer throws `formatBytes is not defined`.
- English copy no longer refers to the old Sortix name.
- Analyzer delete confirmation now says trash, matching the actual backend behavior.
- Places, folders and files are keyboard-accessible buttons.
- Missing favicon no longer 404s.

### Security

- **Fixed an exploitable XSS flaw with local API access.** `escapeHtml()` failed to escape quotes and was interpolated inside HTML attribute strings. A downloaded directory named with malicious attributes could break out of the HTML attribute context and execute arbitrary JavaScript under Martix's origin, exposing local API deletion endpoints. **Upgrade immediately.**
- **Fixed SSRF vulnerability in `POST /api/llm/test`.** Server made HTTP requests to arbitrary user-supplied target URLs and returned response bodies, allowing network probing of localhost and internal LAN services. Endpoints now strictly enforce loopback IP literal checks.
- **Restricted `/api/browse` from listing sensitive user directories.** Blocked listing of `~/.ssh`, `~/.aws`, and `~/.gnupg` directory structures.
- **Removed side-effect deletions during `create_app()` initialization.** Creating the Flask application previously launched background maintenance cleanup threads that could delete user files on module import or startup.
- **Restricted `/api/disk/delete` from performing arbitrary `rmtree` calls.** Protected system paths now return HTTP 403, deletions route to system trash, and folders containing >25 files require explicit user confirmation.
- **Enforced Loopback Restriction on Document Processing:** `MARTIX_LLM_URL` target address is validated strictly as a loopback endpoint on every API invocation to prevent document content exfiltration.
- **Added restrictive Content-Security-Policy (CSP) and `X-Frame-Options: DENY` headers.**
- **Enforced safety limits against archive bombs (`.zip`, `.docx`) and image decompression bombs.** Implemented a strict 256 MB file size cap prior to opening files for inspection.
- **Hardened `notify-send` execution.** Prepended `--` flags before user data arguments to prevent argument injection attacks from filenames beginning with `-`.

### Added

- **Trash Module (`app/trash.py`):** Mandatory safe deletion engine using native desktop trash (`Send2Trash`) or a local restorable quarantine store. Added REST API endpoints `GET /api/trash`, `POST /api/trash/<id>/restore`, and `DELETE /api/trash/<id>`.
- **Rule Priorities:** Multiple rules can now share file extensions, with evaluation order controlled by priority. Added UI drag-and-drop reordering, plus `PATCH /api/rules/<id>` and `POST /api/rules/reorder` API endpoints.
- **Supported `gte` and `lte` condition operators** across rule API validation schemas.
- **Added `watch_recursive` setting** to toggle recursive subfolder monitoring (disabled by default).
- **Added partial scan warnings** in Disk Space Analyzer when scan operations reach time budgets.
- **Added comprehensive test suites:** `tests/test_regressions.py` (27 cases) and `tests/test_security.py` (12 live attack vectors), alongside GitHub Actions CI workflows.
- **Expanded documentation suite in `docs/`.**

### Fixed

- **Fixed `UNIQUE(extension)` schema constraint issue.** Previously, adding a second rule for the same extension silently overwrote existing rules, breaking key multi-rule use cases (e.g. distinct handling for invoice vs. contract PDFs).
- **Fixed unorganized file edge cases:** Addressed false positives in `is_temporary_download_file` caused by `.part` appearing in middle of filenames (e.g., `movie.part1.rar`) and resolved false "file in use" locks on read-only files.
- **Fixed DOCX text extraction failure:** Corrected XML stream truncation at 20 KB that previously broke document parsing across real-world files.
- **Fixed archive extraction undo:** Archives are no longer unlinked during extraction; archive moves are fully reversible in history logs.
- **Hidden non-functional Undo buttons** in UI history rows for non-reversible operations (extractions, maintenance cleanups).
- **Fixed `content not_contains` operator behavior** on binary file types.
- **Fixed dynamic renaming patterns** with empty placeholders producing hidden or empty file names.
- **Prevented self-organizing directory loops** where Martix could move a directory currently under active monitoring.
- **Hardened maintenance cleanup** to ignore dotfiles and purge empty folder remnants cleanly.
- **Fixed uninstaller self-termination bug.** `pkill -f martix` previously matched the uninstaller's own command line argument, causing process termination before desktop shortcuts, autostart entries, and systemd services were cleaned up.
- **Fixed Windows notifications** opening blocking modal dialogs per organized file.
- **Fixed race conditions** during duplicate file checks in target directories.
- **Excluded symbolic links** from organization sweeps, maintenance operations, and deduplication tasks.

### Performance

- Reduced SQL statements required to read application settings from 10 to 3 query executions via process-level schema verification caching.
- Optimized rule loading to fetch once per sweep cycle rather than per file.
- Refactored Disk Analyzer hierarchy traversal to use an iterative stack accumulator, reducing stack frame overhead from 60 levels to 4 frames on deep directory trees.
- Refactored background scheduler to eliminate 0.5-second polling loops, reducing CPU wakeups by 172,800 daily cycles.
- Optimized watcher worker thread allocation to spawn on demand rather than on module import.
- Enforced execution bounds on duplicate scanning (max 200,000 files, 120-second timeout budget).

### Migration

- Automatic database schema migration on application launch. The `rules` table removes unique extension constraints and adds `priority`; `moves_log` adds `undoable`. Zero data loss on existing rule sets.
- Added optional dependencies: `Send2Trash` (native desktop trash support) and `defusedxml` (hardened XML parsing).

---

## [2026-07-24]

### Added

- **Visual Disk Space Analyzer:** Interactive tree view displaying parent folder utilization percentages, file extension distribution tables, and interactive HTML5 Canvas squarified treemaps.
- **Unified 1-Click Installer & Uninstaller:** `install.sh` / `uninstall.sh` managing desktop launcher registration, session autostart entries, user systemd services, and `martix` CLI setup.
- **Full Folder & Directory Organization:** Support for organizing entire directories and subfolders as atomic units.
- **Enhanced Notifications:** System notifications now display full destination folder paths.

### Changed

- Project rebranding from Sortix to **Martix**.

---

## [2026-07-22]

### Added

- Real-time multi-folder monitoring watchdog across Downloads and custom user directories.
- Background task scheduler for periodic maintenance cleanups and folder sweeps.
- PyInstaller single-click desktop build script (`build_desktop.py`).
- Two-phase duplicate file detection engine (64 KB fast-hash + SHA256).
- Metadata extraction support (EXIF image data & ID3 audio tags) for conditions and dynamic renaming patterns.

---

## [2026-07-19]

### Added

- Initial project release: Rule-based and Topic classification engine, watchdog patrol daemon, simulation dry-runs, history log with undo support, usage metrics, and initial security hardening (path traversal protection, Zip-Slip prevention, Host/Origin guards, optional API token authentication).
