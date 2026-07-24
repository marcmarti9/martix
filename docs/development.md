# Development Guide

## Local Setup

```bash
git clone https://github.com/marcmarti9/martix.git
cd martix/backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Access the UI at `http://127.0.0.1:5000`. For standalone desktop window mode: `python desktop.py` (requires `requirements-desktop.txt`).

## Repository Directory Structure

```
backend/
├── app/
│   ├── browser.py        Secure directory navigation (resolve_safe_path)
│   ├── classifier.py     Classification engine — Topics, OCR, EXIF/ID3
│   ├── db.py             SQLite database management, schema, and migrations
│   ├── disk_analyzer.py  Disk space analyzer engine & treemap data generator
│   ├── llm.py            Local Ollama integration (optional)
│   ├── organizer.py      Core archiving engine: rules, moves, undo, maintenance
│   ├── scheduler.py      Background task scheduler
│   ├── security.py       Security policy enforcement: path validation, HTTP guards
│   ├── server.py         Flask REST API endpoints
│   ├── trash.py          Trash & quarantine engine
│   └── watcher.py        Real-time multi-folder watchdog patrol daemon
├── config/
│   ├── categories.json   Default categories, extensions, and subcategories
│   └── settings.py       Environment variables, base paths, file predicates
├── deploy/               Platform system service templates
├── tests/
│   ├── test_all.py         Integration test suite
│   ├── test_regressions.py Audit regression probes
│   └── test_security.py    Security attack probes
├── main.py               Application entry point
└── desktop.py            pywebview desktop window entry point

frontend/                 HTML + CSS + Vanilla JS UI (no external frameworks or CDNs)
database/scripts/         schema.sql initialization script
docs/                     Technical documentation suite
```

## Running Test Suites

```bash
cd backend
.venv/bin/python tests/test_all.py          # Integration test suite
.venv/bin/python tests/test_regressions.py  # Audit regression probes (exits 1 on error)
.venv/bin/python tests/test_security.py     # Security attack probes (exits 1 on error)
```

All three test suites execute inside temporary `HOME` and SQLite database fixtures, ensuring **zero side effects on personal user files**.

### Testing Principles

**Execute active attack payloads rather than asserting static constants.** Tests verifying string constants provide minimal security assurance; tests executing hostile payloads against active application components provide empirical verification.

`test_security.py` spawns a live HTTP server to verify SSRF defenses, creates symlink trees to test home directory containment, and executes `escapeHtml()` with Node to verify script escaping.

When fixing a bug, add a corresponding regression test case to `test_regressions.py`.

## Development Conventions

- **Code Comments:** Write clear technical comments explaining the **rationale** behind non-obvious code paths rather than restating self-evident code statements.
- **Path Validation:** All user-supplied directory inputs must pass through `browser.resolve_safe_path`.
- **Trash Operations:** File deletions must route through `trash.move_to_trash`. **Never** call `unlink()` or `rmtree()` directly on user files.
- **HTML Sanitization:** All values rendered into HTML contexts must pass through `escapeHtml`.
- **SQL Security:** Always use parameterized database queries.

## Database Management & Migrations

SQLite database located at `database/martix.db` (git-ignored). Initial schema defined in `database/scripts/schema.sql`; runtime migrations handled in `db._migrate()`.

To implement a new schema migration: check existing table metadata (`PRAGMA table_info`), apply idempotent schema updates if absent. Migrations execute once per process on initial database connection.

To reset local databases: stop the server and remove `database/martix.db`. It regenerates automatically on startup.

## Desktop Packaging

```bash
cd backend
python build_desktop.py     # Standalone binary generated under backend/dist/
```

## Logging & Debugging

```bash
tail -f ~/.local/share/martix/*.log          # Application log files
journalctl --user -u martix.service -f       # systemd user service logs
```

Python modules use standard `logging` loggers (`martix.organizer`, `martix.server`, `martix.scheduler`, `martix.trash`, `martix.llm`).

To test organization logic without modifying disk state, use **Simulation Mode** (`POST /api/simulate` or UI "Simulate" button).
