# Security Policy

Martix operates with read and write permissions across the user's home directory and automatically processes files downloaded from external network sources. Security report disclosures are treated with high priority.

## Supported Versions

| Version | Supported | Notes |
|---|---|---|
| `main` | ✅ | Active support |
| Pre-July 2026 Audit | ❌ | Contains an exploitable XSS flaw with local API access. Update immediately. |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Use [GitHub Private Vulnerability Reporting](https://github.com/marcmarti9/martix/security/advisories/new), which is the preferred disclosure channel.

When reporting, please include:

- The specific commit or version under test.
- Step-by-step reproduction steps or a minimal Proof of Concept (PoC).
- Impact assessment (e.g. file read, file deletion, remote code execution).
- Required attack prerequisites (e.g., downloading a malicious file, visiting a web page, or local machine access).

You will receive an acknowledgment within a few days. As an open-source project maintained by an individual developer, there is no formal bug bounty program, but researchers will be credited in published advisories and release changelogs unless anonymity is requested.

## Scope & Vulnerability Definitions

Eligible Security Issues:

- Path traversal or directory escape vulnerabilities (e.g. symbolic link bypasses).
- Cross-Site Scripting (XSS) in the web UI—since local API requests run without token authentication by default, script execution under Martix's origin permits full local control.
- Unauthorized file deletion, file relocation, or bypass of protected paths.
- Server-Side Request Forgery (SSRF) or exfiltration of document content to remote network hosts.
- Process crashes or denial of service induced by untrusted files (ZIP bombs, hostile PDFs, image decompression bombs).
- Code execution vectors triggered by downloaded file ingestion.

Non-Eligible Security Issues (unless demonstrating direct security impact):

- Unauthenticated local access to the REST API from local processes. This is an explicit design trade-off for local desktop tools; binding outside loopback requires `MARTIX_TOKEN` authentication, as documented in [docs/security.md](docs/security.md#4-accepted-risks).
- Storage of API tokens in `localStorage`. This trade-off is accepted and mitigated by a restrictive Content-Security-Policy (CSP).
- Attacks assuming an adversary already holds arbitrary local shell access under the target user account.
- Automated scanner outputs lacking a demonstrated, actionable exploitation path.

## Verification & Test Probes

Security mechanisms are verified by running active attack probes against live application components:

```bash
cd backend
.venv/bin/python tests/test_security.py    # Exits with status 1 if any vulnerability probe succeeds
```

This test suite runs automatically in CI on every commit. When submitting security fixes, include a corresponding regression probe verifying the defense.

The complete threat model and security specifications are documented in [docs/security.md](docs/security.md).
