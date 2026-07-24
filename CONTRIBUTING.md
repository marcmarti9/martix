# Contributing to Martix

Thank you for your interest in contributing to Martix! This guide highlights essential conventions for contributing to the repository. A complete development overview is available in [docs/development.md](docs/development.md).

## Core Principles

Martix operates with elevated read and write permissions across the user's home directory and processes untrusted files downloaded from the internet. Three non-negotiable architectural rules govern all development:

1. **100% Local Processing:** Zero telemetry, analytics, or external web API calls. The only outbound HTTP request permitted in the codebase is to a locally hosted LLM endpoint, which is validated on every execution to ensure target addresses resolve strictly to loopback (`127.0.0.1` / `localhost`).
2. **Non-Destructive Deletions:** Direct calls to `unlink()` or `rmtree()` on user files are strictly prohibited. All deletion operations must route through `trash.move_to_trash()`.
3. **Strict Path Validation:** Inputs from the user interface or web API must be validated via `browser.resolve_safe_path()`. Rule destination targets must be sanitized via `security.clean_destination()`.

Furthermore, the `main` branch is protected—all changes must be submitted via Pull Requests.

## Local Environment Setup

```bash
cd backend
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/python main.py        # Web portal available at http://127.0.0.1:5000
```

## Running Tests

All test suites are completely self-contained and run against isolated temporary `HOME` and SQLite database fixtures to ensure zero impact on personal files.

```bash
cd backend
./.venv/bin/python tests/test_all.py           # Integration test suite
./.venv/bin/python tests/test_regressions.py   # Audit regression probes
./.venv/bin/python tests/test_security.py      # Security attack probes
```

All three test suites must pass clean before submitting a Pull Request.

### Testing Methodology

**Execute active attack payloads rather than asserting static constants.** A test asserting constant string definitions provides minimal security assurance; a test executing hostile payloads against running application components provides empirical verification.

- **Fixing a bug?** Add a corresponding test probe to `tests/test_regressions.py`.
- **Adding a defense mechanism?** Add a corresponding bypass probe to `tests/test_security.py`.

## Coding & Style Guidelines

- **Code Comments:** Write clear technical comments explaining the **rationale** behind non-obvious code paths (e.g. race condition handling, backwards compatibility constraints, or past regression fixes) rather than restating self-evident code statements.
- **SQL Security:** Always use parameterized queries for database interactions. Never concatenate untrusted parameters into SQL strings.
- **XSS Prevention:** Ensure all dynamic variables rendered into HTML contexts are sanitized via `escapeHtml()`.

## Pull Request Guidelines

- Focus each Pull Request on a single logical change or feature.
- Provide clear context and rationale in the Pull Request description.
- Update `CHANGELOG.md` when introducing user-facing behavioral changes.
- Record significant architectural changes in [docs/decisions.md](docs/decisions.md) via an Architecture Decision Record (ADR).

## Security Reporting

Do not open public GitHub issues for suspected security vulnerabilities. Follow the security reporting process in [SECURITY.md](SECURITY.md).
