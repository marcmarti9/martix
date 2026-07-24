# REST API Reference

Base URL: `http://127.0.0.1:5000`. All responses are formatted in JSON.

**Authentication:** None required when Martix is bound exclusively to `127.0.0.1`. If `MARTIX_TOKEN` is specified in `backend/.env`, all `/api/*` endpoints require the `X-Martix-Token` request header. Setting an explicit API token is **mandatory** when `HOST` is changed from local loopback; the server will refuse to start without it.

**Request Guards** (`app/security.py:check_request`): The `Host` header must be local (`127.0.0.1` or `localhost`). For state-changing methods, if an `Origin` header is sent by the browser, it must match trusted origins. Maximum HTTP request body size is 2 MB.

---

## Status & Control

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/status` | Patrol daemon status, total organized count, and active downloads folder |
| `POST` | `/api/patrol/toggle` | Enable/disable active monitoring. Body: `{"active": true}` (optional; toggles if omitted) |
| `POST` | `/api/organize-now` | Trigger immediate scan and organization sweep |
| `POST` | `/api/simulate` | Perform dry-run simulation without moving files |
| `GET` | `/api/statistics` | Metrics summary: total organized, top categories, and 30-day activity history |

## Rule Management

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/rules` | Fetch rules **in evaluation order** (first matching rule wins) |
| `POST` | `/api/rules` | Create a rule. Multiple rules can share the same file extension |
| `PATCH`/`PUT` | `/api/rules/<id>` | Update specific rule fields |
| `POST` | `/api/rules/reorder` | Update rule ordering. Body: `{"ids": [3, 1, 2]}` |
| `DELETE` | `/api/rules/<id>` | Delete rule |
| `GET` | `/api/rules/export` | Export rules and maintenance rules as JSON |
| `POST` | `/api/rules/import` | Import rule set (invalid rules are silently skipped) |

```jsonc
// POST /api/rules
{
  "extension": "pdf",              // or "*" for wildcard
  "destination": "Documents/Invoices",  // relative to home directory
  "rename_pattern": "{FILE_YYYY}-{OriginalName}",   // optional
  "conditions": [                  // optional, combined with logical AND
    { "field": "content", "operator": "contains", "value": "invoice" }
  ]
}
```

**Supported Fields:** `name`, `stem`, `extension`, `size_kb`, `age_days`, `content`, `artist`, `album`, `title`, `year`, `camera`, `exif_date`.

**Supported Operators:** `contains`, `not_contains`, `equals`, `starts_with`, `ends_with`, `gt`, `lt`, `gte`, `lte`.

> Rule ordering is significant: an unconditional `.pdf` rule placed above conditional `.pdf` rules will shadow the conditional rules below it. See [architecture.md](architecture.md#4-data-model).

**Dynamic Rename Placeholders:** `{YYYY}`, `{MM}`, `{DD}` (current date), `{FILE_YYYY}`, `{FILE_MM}`, `{FILE_DD}` (file modification date), `{OriginalName}`, `{Topic}`, `{Category}`, `{ext}`, `{ARTIST}`, `{ALBUM}`, `{TITLE}`, `{CAMERA}`, `{EXIF_DATE}`, `{YEAR}`. If a pattern evaluates to an empty string, the original filename is preserved.

## Topic Management

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/topics` | List topics |
| `POST` | `/api/topics` | Create topic: `{"name", "destination", "keywords": [...], "rename_pattern"}` |
| `DELETE` | `/api/topics/<id>` | Delete topic |

## History Logs

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/log?limit=50` | Retrieve recent move history (max limit 500) |
| `POST` | `/api/log/<id>/undo` | Revert file move to original path |

Each record contains an `undoable` boolean flag. This flag is `false` for archive extractions and maintenance cleanups, as they are non-reversible events. Undo requests on non-reversible items return HTTP `409 Conflict`.

## Trash Management

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/trash` | List trash contents: `{"native": bool, "items": [...]}` |
| `POST` | `/api/trash/<id>/restore` | Restore item to original directory path |
| `DELETE` | `/api/trash/<id>` | Permanently purge item |

When `native` is `true`, desktop trash integration (`Send2Trash`) is active, and item restoration is managed via the operating system's native file manager.

## Directory Explorer

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/tree` | Sidebar folder tree structure |
| `GET` | `/api/browse?path=Documents` | Directory contents listing |

Protected system paths (`~/.ssh`, `~/.config`, etc.) are hidden from directory listings and return HTTP `403 Forbidden` if accessed directly.

## Monitored Folders

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/watched-folders` | List monitored directories |
| `POST` | `/api/watched-folders` | Add directory: `{"folder_path": "Desktop/Scans"}` |
| `DELETE` | `/api/watched-folders/<id>` | Remove directory monitoring |

## Maintenance Cleanup Rules

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/maintenance/rules` | List maintenance rules (alias: `/api/maintenance`) |
| `POST` | `/api/maintenance/rules` | Create rule: `{"directory_path", "max_age_days", "active"}` |
| `DELETE` | `/api/maintenance/rules/<id>` | Delete rule |
| `POST` | `/api/maintenance/run` | Execute maintenance sweep immediately |

Files processed by maintenance rules are moved to **trash**, never permanently deleted. Hidden files (dotfiles) and protected system paths are strictly skipped.

## Duplicate Detection

| Method | Endpoint | Description |
|---|---|---|
| `GET`/`POST` | `/api/duplicates` | Search duplicates. `POST {"directories": [...]}` to bound search scope |
| `POST` | `/api/duplicates/clean` | Move selected duplicate files to trash: `{"files": [...]}` |

Two-phase detection pipeline: Group by exact size → 64 KB fast-hash → SHA256 full digest verification. Scans are bounded to a maximum of 200,000 files and a 120-second timeout budget.

## Disk Space Analyzer

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/disk/drives` | Fetch target storage locations |
| `POST` | `/api/disk/scan` | Scan directory structure: `{"path": "Documents"}` |
| `POST` | `/api/disk/delete` | Delete path: `{"path": "...", "confirm": false}` |

`POST /api/disk/scan` returns `"truncated": true` if the scan reached execution time limits, signaling that totals reflect a partial scan.

`POST /api/disk/delete` returns HTTP `409 Conflict` with `needs_confirmation: true` and `file_count` if a target directory contains >25 files. Resubmit with `"confirm": true` to proceed. Protected paths return HTTP `403 Forbidden`. Deletions route to trash.

## System Settings

| Method | Endpoint | Description |
|---|---|---|
| `GET`/`POST` | `/api/settings` | Read or update configuration settings |

```jsonc
{
  "duplicate_action": "suffix",  // "suffix" | "skip" | "delete_source"
  "onboarded": true,
  "unpack_archives": true,
  "watch_recursive": false,      // recursive subfolder monitoring (see note below)
  "native_trash": true           // read-only: indicates Send2Trash availability
}
```

> `watch_recursive` archives internal nested files independently, which disassembles downloaded directory structures. It is disabled by default.

## Scheduler Configuration

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/scheduler/config` | Fetch scheduler configuration |
| `POST`/`PUT` | `/api/scheduler/config` | Update scheduler: `{"enabled": true, "interval_minutes": 60}` |
| `POST` | `/api/scheduler/run` | Execute scheduled tasks immediately (alias: `/run-now`) |

## Local AI Integration (LLM)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/llm/status` | Return local LLM status, model name, and target URL |
| `POST` | `/api/llm/test` | Test connectivity with local Ollama endpoint |
| `POST` | `/api/learn-correction` | Generate rule suggestions from manual user file moves |

`/api/llm/test` **strictly validates that target endpoints resolve to loopback addresses** (literal IP addresses or `localhost`). Remote target addresses return HTTP `400 Bad Request` to ensure privacy and prevent SSRF vectors.

---

## Status & Error Codes

| HTTP Code | Meaning |
|---|---|
| `400 Bad Request` | Invalid input data (disallowed path, invalid condition operator) |
| `401 Unauthorized` | Missing or invalid API authentication token |
| `403 Forbidden` | Unrecognized Host/Origin header or access attempt on protected path |
| `404 Not Found` | Requested resource does not exist |
| `409 Conflict` | Operation conflict (non-reversible undo request or explicit confirmation required) |
| `413 Payload Too Large` | Request body exceeds 2 MB limit |
| `500 Internal Server Error` | Application exception (detailed trace logged locally, omitted from response) |
