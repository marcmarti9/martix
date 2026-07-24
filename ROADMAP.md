# Martix — Estado y Hoja de Ruta

> Documento vivo. Léelo entero antes de tocar el proyecto en una sesión nueva.
> Registro de decisiones de arquitectura detallado en [DECISIONS.md](DECISIONS.md).
> Formato de las entradas de historial: `AAAA-MM-DD — qué pasó`.

Última actualización: 2026-07-24.

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

### Seguridad (ver `backend/app/security.py`, `browser.py`)
- Anti path-traversal: todo destino se resuelve dentro de `HOME_DIR`.
- Anti Zip-Slip: validación estricta de descompresión dentro del directorio objetivo.
- Anti CSRF / DNS-rebinding: comprobación de Host/Origin.
- Token de API opcional (`MARTIX_TOKEN`).
- Cabeceras de privacidad (`no-store`, `nosniff`, `no-referrer`).
- BD SQLite autorregenerable en caliente (WAL).

### Tests
`backend/tests/test_all.py` — 34 bloques de prueba (100% en verde).

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

---

## 5. Historial de sesiones

- **2026-07-19 (sesiones 1-3)**: PR #1, hardening, simulación, carpetas vigiladas, estadísticas y creación del ROADMAP.md.
- **2026-07-22 (sesión 4)**: Orquestación completa de Fases 1 a 5.
- **2026-07-24 (sesión 5)**:
  - Desinstalación completa de la versión previa (Sortix) del sistema del usuario.
  - Implementación del **Analizador de Espacio de Disco** (`backend/app/disk_analyzer.py`, `/api/disk/drives`, `/api/disk/scan`, `/api/disk/delete`, panel visual de Árbol, Desglose por Extensión y Canvas Treemap Squarified Interactivo).
  - Creación del **Instalador y Desinstalador Unificado** de Martix (`install.sh`, `uninstall.sh`, `installer.py`, `uninstaller.py`) con accesos de escritorio, autostart, servicio systemd y comando `martix`.
  - Creación del Registro de Decisiones de Arquitectura ([DECISIONS.md](DECISIONS.md)).



