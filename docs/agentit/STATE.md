# Agentit state

**Updated:** 2026-08-27
**Status:** solid-workbench redesign implemented and in PR; automated CI green
**Branch:** `redesign/solid-workbench`
**PR:** https://github.com/marcmarti9/martix/pull/5

## Goal
Replace the merged Apple Liquid Glass visual direction with a durable repeated-use desktop UI for Martix. The new interface must use solid backgrounds, preserve the existing product behavior, remove random wallpaper imagery and avoid generic AI/SaaS visual tropes.

## Confirmed intent
- Surface: **Operate** — a local desktop file explorer/organizer used repeatedly, not a marketing page.
- Audience: users who need to scan folders, files, rules, status and disk information quickly.
- Preserve: all existing product behavior, DOM hooks/IDs, privacy model, light/dark themes, CSP, vanilla CSS/JS architecture and accessibility semantics already present.
- Replace: Liquid Glass material language, image wallpaper, pervasive translucency/blur, floating rounded cards and capsule-heavy navigation.
- Explicit user constraint: no random background images; use a solid canvas.
- Non-goals: backend changes, new features, workflow changes, deployment or unrelated bug fixes.

## Agentit route
- Dispatch: `agentit` (explicit request + material redesign/research/repository work).
- Packs: `design` + `frontend`.
- Selected skills: `design-inspiration-research`, `design-taste-frontend`, `impeccable-design`, `emil-design-eng`, `frontend-ui-engineering`.
- Research surface: live Awwwards references plus existing Martix visual truth.
- Implementation topology: direct single-writer CSS redesign; no `app.js` edits.
- Verification: source audit + GitHub CI. No rendered-browser claim is made in this environment.

## Inspiration synthesis
Durable source-to-decision provenance lives in `docs/agentit/REFERENCES.md`.

Strongest signals:
- Extremely short palettes can create identity through hierarchy rather than effects.
- Editorial/industrial grids and visible rules give structure without cardification.
- Clean navigation and forms depend on typography, spacing, boundaries and state contrast.
- Awwwards-level visual discipline is useful; Awwwards-style cinematic behavior is not appropriate for repeated Martix actions.

## Design direction
- Thesis: **Local Workbench** — Martix feels like a well-made local instrument: quiet work surface, precise ink, visible structure and one oxide marker.
- Dials: variance 5 / motion 2 / density 7.
- Light canvas: warm bone; dark canvas: charcoal.
- Accent: oxide/orange-red, used for primary and active state emphasis rather than decoration.
- Typography: self-contained system stack with monospace for metadata/status labels; no remote fonts.
- Geometry: 0–6px radii for most product surfaces; pills only where their semantics warrant them.
- Depth: borders, tonal steps and a single modal/toast shadow hierarchy. No active blur, glass sheen, glow, wallpaper or decorative gradients.
- File presentation: ruled workbench grid with shared borders instead of individually floating cards.
- Navigation: active sidebar/settings state uses a narrow accent rule plus restrained fill.
- Motion: roughly 130ms functional state feedback; no hover lift or cinematic repeated-use transitions.
- Responsive: sidebar becomes a compact horizontal navigation strip; workbench grid becomes one column on narrow screens.

## Implementation
Changed:
- `frontend/styles.css` — complete visual-system replacement while retaining existing class/ID contracts.
- removed `frontend/wallpaper-light.jpg`.
- removed `frontend/wallpaper-dark.jpg`.
- added `docs/agentit/REFERENCES.md`.
- updated `docs/agentit/STATE.md`.

Intentionally unchanged:
- `frontend/app.js`.
- `frontend/index.html` DOM/IDs and functional flows.
- backend/database behavior.

The existing `.desktop-scene` DOM node remains only for compatibility and is forced to `display: none`; the active CSS contains no image-backed scene.

## Verification
- Branch is based directly on current `main` (`125b60b...`), with no divergence/behind commits when the PR was opened.
- Diff scope: CSS, two removed wallpaper assets and Agentit docs only.
- Source audit: no `url(` references and no gradient backgrounds in the new stylesheet.
- The only `backdrop-filter` declarations explicitly set the legacy `.glass` helper to `none`; there is no active blur material.
- Focus-visible, responsive breakpoints and `prefers-reduced-motion` remain defined.
- GitHub Actions CI run `33094070723`: **success**.
- CI includes server boot/API response plus integration, regression and security suites on Python 3.10, 3.12 and 3.13.
- Rendered browser QA was not available through the current execution surface, so visual success is not claimed from code inspection alone.

## Superseded state
The previous `facelift/liquid-glass` direction and merged PR #4 are historical only. Its UI bug fixes remain valuable, but its visual material language is intentionally superseded by this redesign.

## Next action
Review PR #5 visually in the desktop app at wide/narrow viewport and light/dark mode before merge; functional CI is green.
