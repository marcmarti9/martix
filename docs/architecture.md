# Martix System Architecture

This document provides a technical overview of Martix's internal design: component interactions, file lifecycle processing pipelines, and system invariants.

> For architectural design trade-offs and rationale, see [decisions.md](decisions.md).
> For API endpoint specifications, see [api.md](api.md).

---

## 1. System Overview

Martix operates as a single Python process running three concurrent components:

```
┌──────────────────────────────────────────────────────────────────┐
│                      Martix Unified Process                      │
│                                                                   │
│  ┌────────────────┐  ┌─────────────────┐  ┌───────────────────┐  │
│  │   Flask Web    │  │  Watchdog       │  │ Task Scheduler    │  │
│  │   Server       │  │  Patrol Daemon  │  │ Background Thread │  │
│  │                │  │                 │  │                   │  │
│  │ Serves UI &    │  │ Real-time file  │  │ Periodic sweeps & │  │
│  │ REST API on    │  │ event monitoring│  │ maintenance jobs  │  │
│  │ 127.0.0.1      │  │                 │  │                   │  │
│  └───────┬────────┘  └────────┬────────┘  └─────────┬─────────┘  │
│          │                    │                     │             │
│          └────────────────────┴─────────────────────┘             │
│                               │                                   │
│                    ┌──────────▼──────────┐                        │
│                    │   organizer.py      │  ← Central file move  │
│                    │  (Archiving Engine) │    decision pipeline   │
│                    └──────────┬──────────┘                        │
│                               │                                   │
│         ┌─────────────────────┼─────────────────────┐             │
│         ▼                     ▼                     ▼             │
│   classifier.py         security.py            db.py              │
│  (Classification)    (Security Policies)    (SQLite Storage)      │
└──────────────────────────────────────────────────────────────────┘
```

Three core invariants govern system architecture:

1. **Zero External Data Exfiltration:** The only permitted outbound HTTP request is to a local LLM instance, validated on every call to resolve strictly to loopback addresses.
2. **Non-Destructive Deletions:** All file deletions route through a restorable trash system.
3. **Home Directory Boundary Enforcement:** All user-supplied directory paths are resolved and validated against `HOME_DIR` prior to file operations.

---

## 2. Core Modules

### `config/settings.py` — Configuration & Environment Discovery

Centralized reader for `.env`, project directory paths, and `categories.json`. It intentionally relies solely on Python standard library modules to run cleanly across minimal environments.

Exposes two critical file system predicates:

- `is_temporary_download_file(path)` — Filters incomplete download artifacts (`.crdownload`, `.part`, Chrome/Drive download prefixes). It inspects **exact file extensions and known prefix patterns**, avoiding naive substring matches that misidentify legitimate files (e.g. `movie.part1.rar`).
- `is_file_in_use(path)` — Verifies whether another process holds an active write handle on a file. Uses POSIX `flock` with a **read** descriptor, or attempts open handles on Windows. Read-only files are correctly handled as available rather than locked.

### `app/security.py` — Security Policies & Validation

Enforces system security boundaries and input validation:

| Function | Responsibility |
|---|---|
| `clean_destination(raw)` | Sanitizes user-defined destination strings into relative paths. Rejects absolute paths, Windows drive letters, `..` traversal segments, and reserved device names |
| `safe_destination_dir(rel)` | Final containment check before file move operations; converts to absolute path and re-validates against `HOME_DIR` |
| `valid_extension` / `valid_conditions` | Validates API parameters prior to database interaction |
| `is_protected_path(path)` | Protects sensitive system directories (`~/.ssh`, `~/.config`, SQLite database) |
| `is_loopback_url(url)` | Asserts network endpoints resolve strictly to local loopback (SSRF defense) |
| `check_request(request)` | Enforces HTTP security headers: local `Host` header validation, trusted `Origin` validation, and API token validation |

**Path Protection Distinctions:**

- `EXACT_PROTECTED_PATHS` — Exact path matches (`~`, root directory). Paths cannot be moved or deleted, but their internal child items may be organized.
- `PROTECTED_SUBTREES` — Directories and all internal sub-trees (`~/.ssh`, `~/.gnupg`, `~/.config`, Martix data directories). Access and modification are completely blocked.

### `app/browser.py` — Secure Directory Navigation

`resolve_safe_path(raw)` serves as the validation gateway for all user interface directory requests. It resolves symbolic links *prior* to containment validation, ensuring symlinks pointing outside `HOME_DIR` (e.g., `/etc`) are rejected. `list_directory` automatically hides protected paths from UI views.

### `app/classifier.py` — Document Classification Engine

Evaluates file categories and target destination paths without executing file moves. Implements the priority cascade:

```
1. User Topics           → Filename matching, followed by text content extraction (PDF/DOCX/TXT/OCR)
2. Subcategories         → Pattern matching on filenames (screenshots, invoices, CVs)
3. Local LLM (Optional)  → Invoked only when MARTIX_LLM=1 and preceding rules do not match
4. Base Category         → Extension fallback (final default)
```

Extraction bounds:

- **PDF:** Bounded to 6 pages, 20,000 characters, and file sizes ≤ 256 MB.
- **DOCX:** Stream-parsed using incremental XML parsers, capped at 8 MB uncompressed text, with DTD processing disabled.
- **Images (OCR):** Image resolution capped at 64 Mpx (`MAX_IMAGE_PIXELS`), treating decompression warnings as exceptions.

`content_is_extractable(ext)` differentiates unreadable binary data from empty text files, preventing `content not_contains` operators from matching arbitrary binary files.

### `app/organizer.py` — File Archiving & Operations Engine

Executes file organization tasks:

- **`resolve_destination_folder(path, rules)`** — Evaluates user rules in priority order; falls back to `classify()`.
- **`check_conditions(path, ext, conditions, facts)`** — Evaluates `AND` rule conditions. `FileFacts` caches expensive file metadata (stat results, extracted text, EXIF data) to prevent duplicate reads across multiple rule conditions.
- **`format_rename_pattern(...)`** — Substitutes string placeholders and sanitizes filenames. Preserves original names if template evaluations result in empty strings.
- **`unpack_archive(...)`** — Extracts archives with Zip-Slip protection, symlink checks, device node rejection, and resource bounds (size, expansion ratio, entry limits, free disk space).
- **`organize_file` / `organize_folder`** — Performs atomic file moves within `_move_lock` critical sections across concurrent worker threads.
- **`run_maintenance_cleanup()`** — Executes age-based retention rules, routing deleted files to trash, skipping dotfiles/protected directories, and pruning empty parent folders.

### `app/trash.py` — Non-Destructive Deletion Engine

Implements restorable file deletion:

1. **Native Desktop Trash:** Uses desktop trash services via `Send2Trash` when available.
2. **Local Quarantine Store:** Fallback restorable quarantine store managed under application data directories with JSON indexing and REST API restoration endpoints.

### `app/watcher.py` — Real-Time Directory Monitoring

`PatrolManager` handles watchdog event monitoring. `_DownloadEventHandler` pushes filesystem events into a bounded queue processed by up to 4 concurrent worker threads.

`_wait_until_stable` monitors file size stability (5 consecutive stable checks up to 5 minutes) and verifies process file locks prior to processing.

### `app/scheduler.py` — Periodic Maintenance & Sweeps

Runs periodic folder sweeps and retention cleanups at configured intervals. Employs efficiency sleep intervals rather than busy-wait loops.

### `app/db.py` — Data Persistence

SQLite database configured in WAL mode. Database schema validation occurs once per process execution and re-initializes automatically if the database file is deleted.

### `app/disk_analyzer.py` — Disk Space Analyzer

Traverses directory hierarchies. For depth levels above `max_depth`, it constructs tree node structures for UI rendering; for deeper levels, it uses an iterative accumulator. Enforces time budgets, returning `"truncated": true` when limits are reached.

### `frontend/` — Web Interface

Vanilla JavaScript implementation without external frameworks or CDN dependencies, ensuring compliance with strict Content Security Policies.

`escapeHtml()` escapes `& < > " ' \``. Numerical values and colors are validated (`safeNumber`, `safeColor`) before insertion into CSS style attributes.

---

## 3. End-to-End File Processing Lifecycle

Step-by-step processing workflow when `electric_bill_march.pdf` lands in `~/Downloads`:

```
1. watchdog          on_created event → _schedule()
                     Filter check: temporary file (.crdownload)? protected path?
                          │
2. Bounded Queue     Worker thread picks up event (max 4 parallel workers)
                          │
3. _wait_until_stable Wait for size stability across 5 checks; confirm no file lock
                          │
4. organize_file     Verify existence, symlink status, zero-byte status, protected paths
                          │
5. Archive Check?    If archive → unpack_archive() with safety bounds, extract contents,
                          and proceed (original archive preserved)
                          │
6. resolve_destination_folder
                     │
                     ├─ User rules evaluated in priority order
                     │  (First matching rule wins; FileFacts caches file attributes)
                     │
                     └─ Fallback to classifier.classify()
                        ├─ Topics (filename → text content/OCR)
                        ├─ Subcategories via pattern matching
                        ├─ Local LLM (if enabled)
                        └─ Base category by file extension
                          │
7. safe_destination_dir  Re-validate target path containment within ~
                          │
8. format_rename_pattern  Apply renaming pattern if configured; fallback to original name
                          │
9. [_move_lock]      Execute filename collision check and shutil.move in critical section
                     If target exists → apply setting: suffix / skip / overwrite-to-trash
                          │
10. db.log_move      Record move event in database history log
                          │
11. Notification     Trigger desktop notification toast
```

---

## 4. Database Schema & Data Model

```sql
rules            -- User defined rules. Multiple rules permitted per extension.
                 -- 'priority' defines evaluation order (lower value = higher priority).

topics           -- Topic categories matched via keywords and text content.

moves_log        -- History log. 'undoable' flag marks reversible moves vs
                 -- non-reversible events (archive extractions, maintenance cleanups).

settings         -- Key/value settings store (patrol state, duplicate handling, etc).

maintenance_rules -- Age-based directory cleanup rules.

watched_folders  -- Additional monitored directories outside Downloads.
```

**Rule Evaluation Order (`db._RULES_ORDER`):**

1. User-assigned `priority` value.
2. Specific file extensions evaluated before wildcard `*` rules.
3. Conditional rules evaluated before unconditional rules.
4. Rule `id` tie-breaker for deterministic evaluation.

---

## 5. Concurrency Model

| Thread / Component | Count | Purpose |
|---|---|---|
| Flask Web Server | Request-bound | Handles API endpoints and serves web interface assets |
| Watchdog Observer | 1 | Monitors filesystem kernel events |
| Patrol Workers | Up to 4 | Processes file stability checks and organization tasks |
| Scheduler | 1 | Executes periodic maintenance sweeps |
| Notifications | Ephemeral | Asynchronous desktop notification dispatch |

Synchronization primitives:

- **`organizer._move_lock`** — Synchronizes filename availability verification and move operations across concurrent workers.
- **`db._schema_lock`** — Ensures thread-safe database schema initialization.
- **`trash._lock`** — Ensures atomic updates to local quarantine JSON indices.
- **`PatrolManager._lock`** — Synchronizes monitoring directory updates.

---

## 6. System Extensibility

**Adding a new condition field (e.g. "page_count"):**

1. Register field in `security._VALID_CONDITION_FIELDS`.
2. Implement calculation and caching in `organizer.FileFacts.value_for()`.
3. Add dropdown options and i18n keys (`cond_field_*`) in `frontend/app.js`.
4. Add corresponding test coverage in `backend/tests/test_regressions.py`.
