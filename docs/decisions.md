# Architecture Decision Records (ADR)

This document records key architecture, design, and product decisions made during the development of Martix, capturing context, decision rationale, and trade-offs.

> Current system architecture overview: [architecture.md](architecture.md).
> Audit findings and resolutions: [audit-2026-07.md](audit-2026-07.md).

---

## Decision Records

### [2026-07-25] — ADR-009: Mandatory Non-Destructive File Deletions

* **Context:** Maintenance cleanups, duplicate cleanups, and Disk Space Analyzer delete actions called `unlink()` or `rmtree()` directly on user files. In an automated directory management tool, misconfigured rules could cause irreversible data loss.
* **Decision:** Introduced a central restorable deletion engine (`app/trash.py`). Deletions use desktop trash integration via `Send2Trash` when available, falling back to a restorable local quarantine store with JSON metadata indexing. Direct `unlink()` or `rmtree()` calls on user files are forbidden across the codebase.
* **Consequences:** Misconfiguration risks shift from irreversible data loss to manageable file restoration. Quarantine storage consumes disk space until purged (default 30-day retention).

---

### [2026-07-25] — ADR-008: Priority Rule Ordering Over Extension Overwriting

* **Context:** The `rules` schema previously enforced a `UNIQUE` index on `extension`, with insertion logic executing `ON CONFLICT DO UPDATE`. Adding a new rule for an existing extension silently replaced previous rules, breaking critical multi-rule use cases (e.g., distinct destination rules for invoice vs. contract PDFs).
* **Decision:** Removed unique extension constraints, added a `priority` database column, and established deterministic rule evaluation ordering: user priority → specific file extensions over wildcards → conditional rules over unconditional rules → rule ID. Updated UI to support visual drag-and-drop reordering, alongside `PATCH /api/rules/<id>` and `POST /api/rules/reorder` endpoints.
* **Consequences:** Rule ordering becomes explicit domain logic: an unconditional `.pdf` rule placed above conditional `.pdf` rules will shadow conditional rules below it. Database migration rebuilds tables cleanly without rule loss.

---

### [2026-07-25] — ADR-007: Explicit Execution Bounds on Disk & Input Operations

* **Context:** The Disk Space Analyzer recursively traversed directory structures synchronously inside HTTP request handlers (risking `RecursionError` on deep trees), archive extractions lacked expansion caps (exposing ZIP bomb vulnerabilities), and duplicate detection performed un-bounded hashing operations.
* **Decision:** Enforced execution bounds across disk traversal operations: Disk Space Analyzer uses an iterative stack accumulator below `max_depth` alongside time budgets returning `"truncated": true`; archive extractions enforce size, ratio, entry count, and free space checks; duplicate scanning caps file counts and execution timeouts.
* **Consequences:** Partial scan results are preferred over process hangs or server timeouts, provided UI indicators clearly signal partial scan status.

---

### [2026-07-25] — ADR-006: Code-Level Verification of Privacy Guarantees

* **Context:** Project documentation guaranteed "zero external network calls," yet `LLM_URL` was read directly from environment variables without loopback validation, and `/api/llm/test` allowed outbound HTTP requests to arbitrary user-supplied target URLs (SSRF).
* **Decision:** Implemented `security.is_loopback_url()`, requiring HTTP/HTTPS schemes and loopback IP literals (`127.0.0.1`, `::1`) or `localhost`. External domain names are rejected to prevent DNS rebinding attacks. Validated on test endpoints and on every local LLM invocation.
* **Consequences:** Local LLM instances must reside on the same machine. Remote LLM setups are intentionally disallowed to ensure privacy bounds remain empirically verifiable.

---

### [2026-07-25] — ADR-005: Live Attack Verification Over Static Assertion Testing

* **Context:** Previous test coverage asserted happy-path execution and static constants, failing to catch 16 logic defects and 2 security vulnerabilities discovered during audit.
* **Decision:** Implemented live attack verification test suites: `tests/test_regressions.py` (27 bug regression probes) and `tests/test_security.py` (12 live attack probes executing local HTTP servers, symlink escapes, and frontend script escaping). Test suites exit with code 1 if a defense is weakened.
* **Consequences:** Test suite execution takes longer and depends on system binaries (e.g. Node for frontend escaping tests). In return, regressions cannot pass silently.

---

### [2026-07-24] — ADR-001: Legacy System Cleanup & Unified Rebranding

* **Context:** Legacy application instances (Sortix) coexisted alongside the unified project codebase (Martix).
* **Decision:** 
  1. Cleanly uninstalled legacy Sortix processes, autostart entries (`~/.config/autostart/sortix.desktop`), desktop entries (`~/.local/share/applications/sortix.desktop`), and systemd user services.
  2. Migrated configuration and branding to **Martix**.
* **Consequences:** Martix operates as the sole smart file organizer and space analyzer on the system, preventing resource duplication, port collisions, and overlapping directory monitoring daemon conflicts.

---

### [2026-07-24] — ADR-002: Integrated Disk Space Analyzer

* **Context:** Martix operated primarily as a background daemon. Users required visual tools to inspect storage distribution and clear heavy files interactively.
* **Decision:**
  1. **Analysis Engine (`backend/app/disk_analyzer.py`):** High-performance recursive scanning calculating directory sizes, parent folder percentages, item counts, and file extension breakdowns.
  2. **REST API Endpoints:** `/api/disk/drives`, `/api/disk/scan`, and `/api/disk/delete`.
  3. **User Interface (`frontend/`):** Summary statistics bar, directory tree view with progress bars, extension breakdown table, and interactive HTML5 Canvas squarified treemap.
* **Consequences:** Expands Martix from a passive daemon to an interactive storage manager.

---

### [2026-07-24] — ADR-003: Unified 1-Click Installer & Uninstaller

* **Context:** Automated installation and clean removal scripts were needed for cross-platform deployment.
* **Decision:** Created root scripts `install.sh` / `installer.py` and `uninstall.sh` / `uninstaller.py` managing Python virtual environments, desktop entry registration, session autostart configuration, user systemd service setup, and global `martix` CLI installation.
* **Consequences:** Simplifies system integration to a single command execution.

---

### [2026-07-24] — ADR-004: Atomic Directory & Subfolder Organization

* **Context:** Martix organized individual files but ignored whole subdirectories downloaded or copied into monitored folders.
* **Decision:**
  1. **Folder Classification (`classify_folder`):** Evaluates folder names against user topics and subcategories; falls back to analyzing internal file extension distributions.
  2. **Atomic Move Engine (`organize_folder`):** Moves entire directories as single atomic units while enforcing reserved directory and monitoring loop guards.
  3. **Folder Stability Verification:** Extends watcher stability checks to directory trees.
* **Consequences:** Supports atomic organization of photo albums, multi-file downloads, and subdirectories.

---

### [2026-07-22] — ADR-000: System Foundation & Priority Cascade Classification

* **Context:** Initial system design for 100% local smart file organization.
* **Decision:**
  - Cascading priority classification: Custom Rules > Advanced Conditions > Topic Keywords/OCR > Local LLM > Extension Fallback.
  - Multi-folder watchdog patrol daemon and background task scheduler.
  - Two-phase duplicate file detection (64 KB Fast-Hash + SHA256).
