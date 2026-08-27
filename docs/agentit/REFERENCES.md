# Design reference ledger

This file records durable external influences that materially changed Martix design decisions. References are inspiration, not templates; no source assets, copy, or distinctive layouts are reproduced.

## 2026-08-27 — Solid Workbench UI redesign

| Source | Role | Extracted principle | Martix decision | Affected paths | Verified |
| --- | --- | --- | --- | --- | --- |
| https://www.awwwards.com/sites/electronic-materials-office | inspiration | Technology UI can feel distinctive with an extremely short palette; Awwwards records black, white and `#DF6C4F`. | Warm neutral light/dark canvases plus one oxide accent reserved for primary/active states. | `frontend/styles.css` | 2026-08-27 |
| https://www.awwwards.com/sites/infini | inspiration | A two-colour system can carry hierarchy through typography, spacing and composition instead of effects. | Remove decorative gradients/glass and let type, rules and spacing carry most visual hierarchy. | `frontend/styles.css` | 2026-08-27 |
| https://www.awwwards.com/inspiration/asymmetrical-layout-marga-navarro | inspiration | Asymmetry works when it remains anchored to a legible grid and responsive structure. | Keep the explorer shell strongly aligned while allowing unequal information weight between title, status, sidebar and content regions. | `frontend/styles.css` | 2026-08-27 |
| https://www.awwwards.com/inspiration/matthew-fisher-menu | inspiration | Clean black navigation relies on type, spacing and contrast rather than ornamental containers. | Flatten toolbar/sidebar controls; active navigation uses a narrow accent rule and restrained fill instead of glass capsules. | `frontend/styles.css` | 2026-08-27 |
| https://www.awwwards.com/inspiration/form-1440-reserve | inspiration | Minimal form systems benefit from clear input boundaries, strong spacing and low decorative noise. | Settings fields use solid surfaces, compact radii, explicit borders and clear focus states. | `frontend/styles.css` | 2026-08-27 |
| https://www.awwwards.com/inspiration/impronta-homepage-impronta | inspiration | Clean typography and transitions can establish identity without background imagery. | Keep motion short and functional; use scale/weight/measure rather than wallpaper or blur to create presence. | `frontend/styles.css` | 2026-08-27 |

## Synthesis

### Strongest signals
- Very short palettes are more memorable than a collection of translucent materials.
- Strong typography and rules can provide depth without shadow-heavy cards.
- A grid can be visually expressive without sacrificing scanability.
- Product controls should remain compact and obvious even when the surrounding art direction is distinctive.

### Cliche radar
Rejected for Martix: wallpaper-as-brand, glassmorphism everywhere, floating rounded cards, blue/indigo tech glow, ornamental gradients, hover lift on repeated controls, oversized empty whitespace, and marketing-site motion inside frequent product actions.

### Selected direction — Local Workbench
Martix should feel like a well-made local instrument: a warm solid work surface, precise ink, visible structure, small industrial geometry and one oxide marker for active/primary actions. Files are working objects arranged in a ruled grid, not floating SaaS cards. Light and dark modes share the same material logic.
