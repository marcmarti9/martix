# Martix Security Model & Specifications

Martix holds read and write permissions across the user's home directory and automatically processes files downloaded from untrusted network sources. This document outlines the system threat model, implemented security controls, and accepted design trade-offs.

> For vulnerability reporting guidelines, see [SECURITY.md](../SECURITY.md).

---

## 1. Protected Assets

| Asset | Security Relevance |
|---|---|
| Personal User Documents | Martix processes sensitive files including tax records, contracts, and financial statements |
| Filesystem Integrity | File modification and deletion permissions require strict protection against data loss |
| Network Confidentiality | System invariant: zero sensitive data exfiltration to external networks |
| Sensitive Credentials | User credentials (`~/.ssh`, `~/.aws`, `~/.gnupg`) reside within accessible storage paths |

## 2. Threat Model & Adversaries

1. **Malicious Downloaded Files (Primary Threat Vector):** Downloaded archives, PDFs, or image files crafted to exploit parser vulnerabilities. Martix processes files automatically upon creation without requiring user interaction.
2. **Cross-Origin Web Requests:** Untrusted websites open in browser tabs attempting to interact with `127.0.0.1:5000` via CSRF or DNS-rebinding attacks.
3. **Local Multi-User & Process Attacks:** Untrusted local processes or users on shared local systems attempting unauthorized API access.
4. **Misconfiguration:** Misconfigured cleanup rules or environment settings.

**Out of Scope:** An adversary with arbitrary shell access running under the user's local account.

---

## 3. Defense Mechanisms per Attack Vector

### 3.1 Path Traversal & Directory Containment

All user-supplied directory inputs pass through `browser.resolve_safe_path()`, which **resolves symbolic links prior to evaluating boundary containment**. Symlinks inside the home directory pointing outside `HOME_DIR` (e.g., to `/etc`) are rejected.

Rule destination targets are processed via `security.clean_destination()`, which rejects absolute paths, Windows drive letters (`C:`), path traversal segments (`..`), reserved device names (`CON`, `LPT1`), trailing dots/spaces, and path segments exceeding 255 characters.

Symbolic links are excluded from organization sweeps, maintenance cleanups, and deduplication tasks.

### 3.2 Archive Processing Defenses

| Threat | Defense Mechanism |
|---|---|
| Zip-Slip (`../../.bashrc`) | Validates target extraction path for every archive entry |
| Absolute Paths | Rejects absolute target paths (POSIX and Windows) |
| Symlink Escapes | Validates symlink target destinations (CVE-2007-4559) |
| Device Nodes / FIFOs | Rejects device nodes and FIFO special files |
| Archive Bombs | Enforces limits on total extracted size (4 GB), expansion ratio (200x), entry count (20,000), and free disk space |
| Dangerous File Permissions | Uses `extractall(filter="data")` on Python 3.12+ |

### 3.3 Document Extraction Controls

| Threat | Defense Mechanism |
|---|---|
| XXE / Billion Laughs in `.docx` | Uses `defusedxml` when available; explicitly disables DTD processing across XML streams |
| Archive Bombs in `.docx` | Caps uncompressed XML stream reading to 8 MB |
| Image Decompression Bombs | Enforces `MAX_IMAGE_PIXELS` (64 Mpx) and converts decompression warnings to exceptions |
| Hostile PDFs | Enforces a 256 MB file size cap prior to opening files |
| OCR Hangs | Applies a 10-second execution timeout on `pytesseract` operations |

### 3.4 Web Application Hardening (XSS)

`escapeHtml()` explicitly escapes `& < > " ' \``. Escaping quotes is mandatory as values are interpolated into HTML attribute strings (e.g. `title="..."`).

> **Past Vulnerability:** Previous releases used DOM text node conversion (`textContent → innerHTML`), which omitted quote escaping. Malicious directory names such as `x" onmouseover="..."` could break out of HTML attributes to execute JavaScript with local API privileges. See [audit-2026-07.md](audit-2026-07.md).

Martix enforces a restrictive **Content-Security-Policy (CSP)**: `default-src 'self'`, no external network origins, `frame-ancestors 'none'`, `object-src 'none'`. Dynamic UI values are sanitized (`safeNumber`, `safeColor`) before insertion into CSS style attributes.

### 3.5 REST API Hardening

| Threat Vector | Security Control |
|---|---|
| DNS Rebinding | Enforces local `Host` header validation |
| CSRF Attacks | Validates `Origin` headers on state-changing requests |
| Network Exposure | Default binding to `127.0.0.1`; server refuses to start on external hosts without `MARTIX_TOKEN` |
| Token Comparisons | Constant-time comparisons using `hmac.compare_digest` |
| Memory Exhaustion | Enforces a 2 MB `MAX_CONTENT_LENGTH` request body limit |
| Clickjacking | Enforces `X-Frame-Options: DENY` and `frame-ancestors 'none'` |
| Cache Exfiltration | Enforces `Cache-Control: no-store` across API responses |

### 3.6 Server-Side Request Forgery (SSRF) & Privacy Enforcement

The only outbound network request permitted in Martix is to a local LLM endpoint. `security.is_loopback_url()` requires:

- HTTP or HTTPS scheme,
- Literal loopback IP addresses (`127.0.0.1`, `::1`) or `localhost`.

External domain names are explicitly rejected to prevent DNS rebinding attacks.

This mechanism enforces two security objectives:

1. **SSRF Prevention:** `/api/llm/test` cannot be used to probe localhost or internal network ports.
2. **Privacy Enforcement:** `llm.suggest_subfolder()` sends file text snippets to the configured LLM endpoint. Loopback address verification runs on every request to prevent document exfiltration.

### 3.7 Restorable Deletions

No file deletion in Martix is permanent:

- All deletions route through `trash.move_to_trash()` (native desktop trash or local quarantine store).
- `security.is_protected_path()` protects `~/.ssh`, `~/.gnupg`, `~/.config`, Martix databases, and `.git` repositories.
- Deleting folders containing >25 files requires explicit user confirmation.
- Maintenance cleanups skip hidden files (dotfiles) and directories.

### 3.8 Command Execution Security

System notifications launch external processes using explicit argument arrays without `shell=True`. Linux `notify-send` invocations prepend `--` argument separators before user input parameters to prevent argument injection attacks.

### 3.9 Database Access Controls

Database operations use parameterized SQL queries exclusively. Column names constructed dynamically in internal queries are validated against strict whitelist arrays defined in source code.

---

## 4. Accepted Security Trade-offs

1. **API Tokens Stored in `localStorage`:**
   - **Risk:** Cross-Site Scripting could access stored tokens.
   - **Rationale:** Cookies (`HttpOnly`) introduce session management overhead for non-browser clients (desktop window wrapper, CLI). Mitigated by strict CSP enforcement and HTML output sanitization.
   - **Note:** Tokens are only required when exposing Martix outside loopback interfaces.

2. **Acceptance of Requests Without `Origin` Headers:**
   - **Risk:** Local processes can issue API requests when no token is set.
   - **Rationale:** Standard design for unauthenticated local APIs, enabling `curl` and desktop wrapper access. Browsers include `Origin` headers on cross-origin requests, mitigating browser CSRF.
   - **Mitigation:** Set `MARTIX_TOKEN` in `backend/.env` for multi-user environments.

3. **Local LLM Document Processing:**
   - Document text snippets are transmitted to the configured local LLM endpoint when `MARTIX_LLM=1` is explicitly enabled. Endpoint targets are strictly validated as local loopback addresses.

---

## 5. Security Verification & Test Suite

Security controls are empirically verified by running live attack probes against active application components:

```bash
cd backend
.venv/bin/python tests/test_security.py    # 12 live attack probes; exits code 1 on failure
.venv/bin/python tests/test_regressions.py # 27 audit regression test cases
.venv/bin/python tests/test_all.py         # Integration test suite
```

If a security defense is modified or regressed, `test_security.py` flags the issue as EXPLOTABLE. These test suites run automatically in CI pipelines on every commit.

---

## 6. Recommended Deployment Practices

- **Keep default `127.0.0.1` binding.** Local loopback binding provides robust security isolation.
- If exposing Martix over a local network (LAN), set a strong, random `MARTIX_TOKEN`.
- Install `Send2Trash` (`pip install Send2Trash`) so deletions route to your native desktop trash folder.
- Always review maintenance cleanup rules using **Simulation Mode** before enabling automated schedules.
- Keep `MARTIX_LLM=0` unless local Ollama classification is actively required.
