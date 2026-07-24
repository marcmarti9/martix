# System Configuration Guide

## Environment Variables (`backend/.env`)

Copy `backend/.env.example` to `backend/.env`. All environment variable configuration values are optional.

| Environment Variable | Default Value | Description |
|---|---|---|
| `HOST` | `127.0.0.1` | Network listening interface. **Changing this value requires setting `MARTIX_TOKEN`** |
| `PORT` | `5000` | HTTP port |
| `DOWNLOADS_DIR` | `~/Downloads` | Primary monitored directory |
| `MARTIX_TOKEN` | *(empty)* | REST API authentication token. **Mandatory if `HOST` is non-local** |
| `MARTIX_DATA_DIR` | Platform specific | Application data directory (local trash quarantine location) |
| `MARTIX_TRASH_RETENTION_DAYS` | `30` | Retention period (in days) for items in local quarantine storage |
| `MARTIX_LLM` | `0` | Enable local LLM-based classification (`1` to activate) |
| `MARTIX_LLM_URL` | `http://127.0.0.1:11434` | Ollama endpoint URL. **Must resolve to local loopback** |
| `MARTIX_LLM_MODEL` | `llama3.2` | Ollama model name |

> Legacy `SORTIX_*` environment variable names remain supported for backwards compatibility.

### Interface Binding & Security

Binding Martix exclusively to `127.0.0.1` provides robust local isolation. If `HOST` is modified to listen on non-loopback interfaces, `main.py` will **refuse to start** without a configured `MARTIX_TOKEN`.

Generate a secure token using Python:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Application Data Storage

When `Send2Trash` is unavailable, Martix uses a local quarantine store inside platform data directories:

| Operating System | Default Quarantine Directory Path |
|---|---|
| Linux | `$XDG_DATA_HOME/martix` or `~/.local/share/martix` |
| macOS | `~/Library/Application Support/Martix` |
| Windows | `%LOCALAPPDATA%\Martix` |

---

## Category Definitions (`backend/config/categories.json`)

Defines primary categories, file extensions, target directories, and subcategories:

```jsonc
{
  "categories": {
    "documents": {
      "label": "Documents",
      "icon": "document",
      "folder": "Documents/Unclassified",   // relative to user home directory
      "extensions": ["pdf", "docx", "txt", "odt"],
      "subcategories": [
        {
          "label": "Invoices and Receipts",
          "folder": "Documents/Invoices and receipts",
          "patterns": ["factura", "recibo", "invoice", "receipt"]
        }
      ]
    }
  },
  "topic_matching": {
    "content_extensions": ["pdf", "docx", "txt"]
  }
}
```

Subcategory pattern matching evaluates against normalized filenames (lowercased, diacritics removed, punctuation converted to spaces).

Category definitions are loaded **at module import time**; restart Martix after editing `categories.json`.

---

## System Settings (Web UI & REST API)

Stored in the `settings` SQLite table and configurable via the web UI Settings panel or REST API (`POST /api/settings`).

| Setting Key | Default Value | Description |
|---|---|---|
| `duplicate_action` | `suffix` | Defines behavior when target files exist: `suffix` appends `(1)`, `skip` skips file move, `delete_source` moves source to trash |
| `unpack_archives` | `true` | Automatically unpack `.zip` / `.tar` archives. Compressed archives are **preserved** |
| `watch_recursive` | `false` | Enable recursive monitoring of subdirectories |
| `onboarded` | `false` | Tracks completion of initial onboarding wizard |

### Recursive Folder Monitoring (`watch_recursive`)

When disabled, nested files inside subdirectories (e.g. `~/Downloads/album/photo.jpg`) do not trigger individual file events; the entire directory is processed as a unit. Enabling `watch_recursive` archives internal nested files individually, disassembling subfolder structures.

---

## Scheduled Maintenance Rules

Executes age-based automated directory cleanups recursively. Processed files are routed to **trash**, preventing permanent data loss.

Maintenance operations skip hidden files/directories (dotfiles), protected paths, and symbolic links. Empty parent directories remaining after cleanups are removed automatically.

> Always utilize **Simulation Mode** before activating maintenance rules on custom directories.

---

## Optional Dependencies

Core features function independently without external packages; installing optional packages enables advanced capabilities:

| Package / Integration | Added Functionality | Fallback Behavior |
|---|---|---|
| `Send2Trash` | Native desktop trash integration | Local quarantine store in data directory |
| `defusedxml` | Hardened XML stream parsing | Standard XML parser with explicit DTD rejection |
| **Tesseract OCR** (binary) | Image text extraction & classification | Image files classified by file extension |
| **Ollama** (local service) | Local AI document classification | Rule and topic priority cascade |

Installing Tesseract via system package managers:

```bash
sudo dnf install tesseract          # Fedora / RHEL
sudo apt install tesseract-ocr      # Debian / Ubuntu
brew install tesseract              # macOS
```
