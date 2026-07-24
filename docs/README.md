# Martix Documentation

## Quick Start Guide

| Goal | Reference Document |
|---|---|
| Install and run Martix | [Project README](../README.md) |
| Understand internal system architecture | [architecture.md](architecture.md) |
| Review threat models and security defenses | [security.md](security.md) |
| Configure system settings and environment variables | [configuration.md](configuration.md) |
| Integrate with the REST API | [api.md](api.md) |
| Contribute code or test suites | [development.md](development.md) and [CONTRIBUTING.md](../CONTRIBUTING.md) |

## Document Index

### Architecture & Operations

- **[architecture.md](architecture.md)** — Modular design, complete file processing pipeline from monitoring to archiving, data models, concurrency controls, and extensibility patterns.
- **[api.md](api.md)** — Complete specification of the 40+ REST API endpoints, payload formats, and status codes.
- **[configuration.md](configuration.md)** — Environment variables, category definitions, user settings, and optional system dependencies.

### Security

- **[security.md](security.md)** — Threat model, defense mechanisms per attack vector, accepted risks, and deployment security recommendations.
- **[SECURITY.md](../SECURITY.md)** — Vulnerability reporting policy and disclosure process.

### History & Design Decisions

- **[decisions.md](decisions.md)** — Architecture Decision Records (ADR): design decisions, context, trade-offs, and historical context.
- **[audit-2026-07.md](audit-2026-07.md)** — July 2026 Security & Bug Audit Report: 16 confirmed bugs, 2 exploitable security vulnerabilities, and implemented resolutions.
- **[CHANGELOG.md](../CHANGELOG.md)** — Version release history.
- **[roadmap.md](roadmap.md)** — Project status, competitive landscape evaluation, and prioritized backlog.

### Development

- **[development.md](development.md)** — Local environment setup, directory structure, test suite execution, and coding conventions.

---

## Core Invariants for Developers

1. **All UI-supplied file paths must pass through `browser.resolve_safe_path()`.** Symbolic links are resolved prior to checking boundary containment within the user's home directory.
2. **File deletions must never call `unlink()` or `rmtree()` directly.** All deletions must route through `trash.move_to_trash()`.
3. **Tests must execute live attack vectors rather than checking static constants.** When adding defenses, include corresponding attack probes that actively attempt to bypass them.
