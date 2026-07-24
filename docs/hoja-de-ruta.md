# Martix — Estado y Hoja de Ruta

> Documento vivo. Léelo entero antes de tocar el proyecto en una sesión nueva.
> Decisiones de arquitectura: [decisiones.md](decisiones.md).
> Formato de las entradas de historial: `AAAA-MM-DD — qué pasó`.

Última actualización: 2026-07-25.

---

## 1. Qué es Martix

Martix es un organizador inteligente de archivos en tiempo real y analizador visual de espacio de disco (Python/Flask + JS vanilla), enfocado en Descargas y carpetas de usuario. Vigila directorios, clasifica cada archivo nuevo por reglas Scratch, metadatos EXIF/ID3, palabras clave de contenido (con OCR local) o un LLM local, y visualiza el tamaño de carpetas y archivos mediante un árbol interactivo y treemap visual. 100% local: sin telemetría, sin llamadas a internet ni para la IA. Repo público: https://github.com/marcmarti9/martix (MIT).

---

## 2. Funcionalidades implementadas

### Motor de clasificación (cascada de prioridad, ver `backend/app/classifier.py` y `organizer.py`)
1. Reglas personalizadas con condiciones tipo bloques Scratch (nombre, extensión,
   tamaño, antigüedad `age_days`, contenido; combinables con AND) — `condition-builder` en el frontend.
2. Temas por palabra clave: escanea nombre y contenido de PDF/DOCX/TXT, y OCR
   local (tesseract) en imágenes si está instalado.
3. Subcategorías por patrón en el nombre (capturas de pantalla, facturas, CVs...).
4. Extracción segura de comprimidos (`.zip`, `.tar`, `.tar.gz`) con protección anti Zip-Slip para clasificar su contenido interno.
5. LLM local opcional (Ollama, `MARTIX_LLM=1`) para sugerir carpeta cuando nada
   más encaja. Apagado por defecto. Nunca sale de `127.0.0.1`.
6. Categoría base por extensión (fallback final).

### Automatización
- **Patrulla Activa Multi-Carpeta**: watchdog en tiempo real sobre `DOWNLOADS_DIR` y todas las carpetas vigiladas activas, con sincronización dinámica y pool de hilos.
- **Programador de tareas (Task Scheduler)**: ejecutor en segundo plano para mantenimientos periódicos y barridos a intervalos configurables (`/api/scheduler/config`).
- Notificaciones nativas de escritorio (Linux `notify-send`, macOS `osascript`, Win `powershell`).
- Renombrado dinámico con placeholders (`{YYYY}`, `{MM}`, `{DD}`, `{Topic}`, `{Category}`, `{OriginalName}`, `{ext}`).
- Mantenimiento / auto-trash: reglas de borrado por antigüedad, por carpeta, ejecutable manualmente desde la UI o automáticamente por el Scheduler.
- Deduplicación optimizada en 2 pasos (Fast-Hash de 64KB + SHA256 completo) en cualquier directorio arbitrario del sistema.
- **Analizador Visual de Espacio de Disco**: árbol interactivo con % del padre, desglose por extensiones y mapa treemap squarified con eliminación segura de archivos.
- Exportación e importación de reglas en formato JSON (`/api/rules/export` e `/api/rules/import`).
- Undo de un nivel desde el Historial.
- Simulación / dry-run (`/api/simulate`): previsualiza sin mover nada.
- Panel de estadísticas: total organizado, top categorías, actividad 30 días.

### Producto / distribución
- **Instalador y desinstalador unificado 1-clic**: `install.sh` y `uninstall.sh`.
- App de escritorio (`backend/desktop.py`): pywebview o navegador en modo `--app`.
- Empaquetado en 1-clic: script `backend/build_desktop.py` (PyInstaller) que genera binario standalone en `backend/dist/`.
- Instaladores de servicio en segundo plano: systemd (Linux), LaunchAgent (macOS), Task Scheduler (Windows).
- UI bilingüe ES/EN, tema claro/oscuro con View Transitions API.

### Seguridad (ver [seguridad.md](seguridad.md))
- Anti path-traversal: todo destino se resuelve dentro de `HOME_DIR`, con los
  enlaces simbólicos resueltos **antes** de comprobar la contención.
- Anti Zip-Slip, enlaces que escapan, rutas absolutas y bombas de compresión.
- Anti CSRF / DNS-rebinding: comprobación de Host/Origin.
- Content-Security-Policy restrictiva y `X-Frame-Options: DENY`.
- Anti-SSRF: la única petición saliente posible se valida como loopback.
- Rutas protegidas (`~/.ssh`, `~/.config`…) intocables y ocultas del explorador.
- Papelera obligatoria: ningún borrado es definitivo.
- Token de API opcional en local, **obligatorio** si se expone `HOST`.
- Cabeceras de privacidad (`no-store`, `nosniff`, `no-referrer`).
- BD SQLite autorregenerable en caliente (WAL).

### Tests
- `backend/tests/test_all.py` — integración (37 bloques).
- `backend/tests/test_regressions.py` — 27 casos, uno por bug de la auditoría.
- `backend/tests/test_security.py` — 12 ataques reales contra la aplicación.

Las tres en verde y ejecutándose en CI en cada push.

---

## 3. Comparativa con la competencia

| | Martix | Hazel (macOS) | DropIt (Win, gratis) | File Juggler (Win) |
|---|---|---|---|---|
| Multiplataforma | ✅ | ❌ solo Mac | ❌ solo Win | ❌ solo Win |
| Precio | Gratis/OSS | ~42$ | Gratis | ~25$ |
| Clasificación por contenido + OCR | ✅ | ❌ | ❌ | de pago |
| Varias carpetas vigiladas en tiempo real | ✅ | ✅ | ✅ | ✅ |
| Reglas por fecha/metadatos (EXIF...) | Parcial (`age_days`) | ✅ | parcial | parcial |
| Extracción de comprimidos (.zip/.rar) | ✅ | ❌ | ✅ | ❌ |
| Clasificación con LLM local | ✅ (único en el sector) | ❌ | ❌ | ❌ |
| Deduplicación integrada | ✅ (Fast-hash) | ❌ | parcial | ❌ |
| Auto-trash por antigüedad | ✅ | ✅ | ❌ | ✅ |
| Programación por horario (cron) | ✅ | ✅ | ❌ | ✅ |
| Analizador visual de espacio integrado | ✅ | ❌ | ❌ | ❌ |

---

## 4. Backlog priorizado

Marca `[x]` cuando esté commiteado y añade la fecha entre paréntesis.

### Impacto alto
- [x] **Patrulla multi-carpeta real.** (2026-07-22) Watchdog en tiempo real sobre Descargas + carpetas vigiladas activas.
- [x] **Programación (cron/scheduler) para mantenimiento y carpetas vigiladas.** (2026-07-22) Hilo de segundo plano `TaskScheduler`.
- [x] **Empaquetado de un clic.** (2026-07-22) Script `backend/build_desktop.py` con PyInstaller.
- [x] **Analizador de Espacio de Disco.** (2026-07-24) Árbol de espacio, desglose por extensiones y mapa treemap squarified en Canvas.
- [x] **Instalador y desinstalador 1-clic.** (2026-07-24) Scripts `install.sh` y `uninstall.sh`.
- [x] **Auditoría completa de bugs y seguridad.** (2026-07-25) 16 bugs + 2
  vulnerabilidades explotables corregidos; suites de regresión y de seguridad.
  Ver [auditoria-2026-07.md](auditoria-2026-07.md).
- [x] **Reglas con prioridad reordenable.** (2026-07-25) Varias reglas por
  extensión, que es lo que hace útiles las condiciones.
- [x] **Papelera en todos los borrados.** (2026-07-25) `app/trash.py`.

### Pendiente

- [ ] **Interfaz de la papelera.** La API (`/api/trash`) ya permite listar y
  restaurar; falta el panel en el frontend para quienes no tengan `send2trash`.
- [ ] **Condiciones con OR y grupos anidados.** Hoy solo AND. El motor está a un
  refactor de soportar `{"any": [...]}`.
- [ ] **Deshacer por lote.** "Revertir todo lo de la última hora": `moves_log`
  ya tiene las marcas de tiempo necesarias.
- [ ] **Escaneo de disco incremental por SSE.** Sustituir el POST que bloquea
  por progreso en vivo.
- [ ] **Perfiles de reglas.** Conjuntos "trabajo" / "personal" conmutables.
- [ ] **Detección de facturas por importe/NIF** además de por palabra clave.
- [ ] **Migrar los tests a pytest.** Hoy son asserts a nivel de módulo, así que
  `pytest tests/test_all.py` no recoge nada.

---

## 5. Historial de sesiones

- **2026-07-19 (sesiones 1-3)**: PR #1, hardening, simulación, carpetas vigiladas, estadísticas y creación de esta hoja de ruta.
- **2026-07-22 (sesión 4)**: Orquestación completa de Fases 1 a 5.
- **2026-07-25 (sesión 6)**: Auditoría completa en dos tandas.
  - **Bugs**: 16 confirmados y 10 avisos, reproducidos con una sonda de 27
    casos. Entre ellos: XSS por nombre de archivo con acceso a la API local,
    `create_app()` borrando archivos como efecto secundario, el desinstalador
    matándose a sí mismo, el índice único que inutilizaba las condiciones de las
    reglas, la clasificación por contenido de `.docx` que no funcionaba nunca, y
    archivos que no se archivaban jamás (`.part` como subcadena, solo lectura).
  - **Seguridad**: 2 explotables (SSRF en `/api/llm/test`, `/api/browse`
    listando `~/.ssh`) y 8 debilidades. Añadidas CSP, papelera obligatoria,
    rutas protegidas y presupuestos en toda operación sobre disco.
  - Documentación reorganizada en `docs/` y CI en GitHub Actions.
- **2026-07-24 (sesión 5)**:
  - Desinstalación completa de la versión previa (Sortix) del sistema del usuario.
  - Implementación del **Analizador de Espacio de Disco** (`backend/app/disk_analyzer.py`, `/api/disk/drives`, `/api/disk/scan`, `/api/disk/delete`, panel visual de Árbol, Desglose por Extensión y Canvas Treemap Squarified Interactivo).
  - Creación del **Instalador y Desinstalador Unificado** de Martix (`install.sh`, `uninstall.sh`, `installer.py`, `uninstaller.py`) con accesos de escritorio, autostart, servicio systemd y comando `martix`.
  - Creación del Registro de Decisiones de Arquitectura ([decisiones.md](decisiones.md)).



