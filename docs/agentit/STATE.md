# Agentit state

## Goal
Lavado de cara visual de Martix a estética **Apple Liquid Glass** premium, sin AI slop (neón, indigo glow, cards genéricas), y arreglo de bugs reales encontrados al inspeccionar la UI.

## Confirmed intent
- Audience: usuario local que usa Martix como explorador/organizador diario.
- Success: interfaz que se siente como utilidad de escritorio Apple (capas de cristal, especular, tipografía de sistema), no como dashboard SaaS; bugs funcionales de UI corregidos.
- Constraints: CSP `font-src 'self'` (sin Google Fonts); vanilla CSS/JS; no cambiar el producto ni el modelo de privacidad; no preguntar (el usuario lo prohibió).
- Non-goals: rediseño de IA/reglas, features nuevas, deploy, neon/cyberpunk.

## Domain pack
- Pack: design + frontend
- Craft depth: polished (dirección explícita posterior: Liquid Glass Apple)
- Spend: normal
- Topology: direct
- critic_required: false
- Effort: Polished (asumido; entrevista omitida por petición explícita)

## Current status
- complete: Liquid Glass + bugs de UI + tests + verificación browser
- in progress: PR
- not started: merge (queda al usuario)

## Decisions
- Superficie: **Operate** (app de escritorio), no landing.
- Tesis visual: *una lámina de cristal óptico sobre un escritorio quieto; el material hace el trabajo, no la decoración.*
- Dials: variance 4 / motion 3 / density 6.
- Paleta: neutrales cálidos + un solo acento system-blue Apple (`#007AFF` / `#0A84FF`). Cero indigo/violeta/neón.
- Tipo: stack de sistema (SF Pro / Segoe UI Variable / system-ui). Sin Inter remoto.
- Material: `backdrop-filter` + trazo especular + sombra ambiental. Sin glow, pulse ni hover-lift en cada card.
- Interview skipped: el usuario pidió no preguntar; luego fijó Liquid Glass Apple.

## Important files and artifacts
- Branch: `facelift/liquid-glass`
- `frontend/styles.css`, `frontend/index.html`, `frontend/app.js`
- Continuity: `docs/agentit/STATE.md`

## Verification
- `backend/.venv/bin/python tests/test_all.py` — OK
- `tests/test_regressions.py` — 0 bugs / 1 aviso previo (hilos del watcher)
- `tests/test_security.py` — 0 explotables / 1 debilidad previa (S08 CSRF sin Origin)
- Browser 1440 y 390: home, carpeta, settings, simulación, tema oscuro, consola limpia
- Deduplicate ya no escanea al abrir la pestaña

## Next actions
1. Abrir PR.
2. Merge a criterio del usuario.

## Open questions / blockers
Ninguno. Dirección visual confirmada por el usuario.

## Recovery
Checkpoint: dirección Liquid Glass decidida; bugs inventariados (Sortix leftover, `formatBytes` undefined, botón Ajustes se vacía, CSS de `.icon-btn`/simulación/stats ausente, confirmación de borrado dice “permanentemente” pero va a papelera, pestaña Duplicados dispara un scan al abrirla).
