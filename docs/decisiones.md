# Registro de decisiones de arquitectura (ADR)

Decisiones de diseño, arquitectura y producto tomadas durante el desarrollo de
Martix: el contexto, la decisión y sus consecuencias. Las más recientes primero.

> Cómo funciona el sistema hoy: [arquitectura.md](arquitectura.md).
> Qué se rompió y cómo se arregló: [auditoria-2026-07.md](auditoria-2026-07.md).

---

## Historial de decisiones

### [2026-07-25] — ADR-009: Ningún borrado es definitivo

* **Contexto:** Tres caminos del código (mantenimiento por antigüedad, limpieza
  de duplicados y borrado desde el analizador de espacio) usaban `unlink()` o
  `rmtree()` directamente. Martix administra documentos personales, y una regla
  mal configurada bastaba para destruirlos sin recuperación posible.
* **Decisión:** Nuevo módulo `app/trash.py` por el que pasa **todo** borrado.
  Usa la papelera nativa del escritorio si `send2trash` está disponible (el
  usuario recupera desde su gestor de archivos habitual) y, si no, una
  cuarentena propia en la carpeta de datos con índice JSON y restauración desde
  la API. Se prohíbe `unlink()`/`rmtree()` sobre archivos del usuario en el
  resto del código.
* **Consecuencias:** El coste de un fallo de configuración pasa de
  irreversible a molesto. La cuarentena consume espacio hasta la purga
  (30 días por defecto, configurable).

---

### [2026-07-25] — ADR-008: Las reglas se ordenan, no se sobrescriben

* **Contexto:** La tabla `rules` tenía un índice **único** sobre `extension` y
  `add_rule` hacía `ON CONFLICT DO UPDATE`. Crear una segunda regla `.pdf`
  sobrescribía la primera en silencio, así que era imposible tener "pdf que
  contiene *factura* → Facturas" y "pdf que contiene *contrato* → Contratos" a
  la vez. Toda la función de condiciones quedaba sin sentido, justo en el caso
  de uso que anuncia el proyecto.
* **Decisión:** Índice no único, nueva columna `priority` y orden de evaluación
  explícito: prioridad del usuario → extensión concreta antes que comodín →
  reglas con condiciones antes que sin ellas → `id`. La interfaz muestra el
  número de orden y permite reordenar; se añaden `PATCH /api/rules/<id>` y
  `POST /api/rules/reorder`.
* **Consecuencias:** El orden pasa a ser semántica visible: una regla `.pdf` sin
  condiciones colocada arriba deja muertas a las condicionales de debajo. Se
  asume a cambio de la expresividad. La migración rehace la tabla conservando
  las reglas existentes.

---

### [2026-07-25] — ADR-007: Presupuestos explícitos en toda operación sobre disco

* **Contexto:** El analizador de espacio recorría el árbol completo de forma
  recursiva dentro de la petición HTTP (60 niveles = 60 marcos de pila, riesgo
  de `RecursionError`), la descompresión no limitaba el tamaño resultante
  (un `.zip` de 20 KB se expandía ×1023) y la búsqueda de duplicados hasheaba
  sin tope.
* **Decisión:** Toda operación que recorre disco declara sus límites: el
  analizador usa un acumulador iterativo por debajo de `max_depth` y un
  presupuesto de tiempo que marca el resultado como `truncated`; la
  descompresión valida tamaño, ratio, número de entradas y espacio libre; la
  deduplicación acota archivos y tiempo.
* **Consecuencias:** Un resultado parcial es preferible a un proceso colgado,
  siempre que se diga que es parcial. La interfaz avisa cuando lo es.

---

### [2026-07-25] — ADR-006: La promesa de privacidad se respalda con código

* **Contexto:** El README prometía "cero llamadas externas", pero `LLM_URL`
  salía de `.env` sin ninguna comprobación, y `/api/llm/test` solicitaba
  cualquier URL que le pasaran desde el servidor (SSRF). Un `.env` mal copiado
  bastaba para exfiltrar el contenido de un documento.
* **Decisión:** `security.is_loopback_url()` exige esquema `http`/`https` y una
  **IP literal** de loopback. Los nombres de dominio se rechazan a propósito:
  pueden resolver a otra cosa más tarde (DNS rebinding). Se comprueba en el
  endpoint de prueba y **en cada llamada** de `suggest_subfolder`.
* **Consecuencias:** Ollama solo puede vivir en el mismo equipo. Se descarta el
  caso de uso "un Ollama en mi servidor de casa" a cambio de que la promesa de
  privacidad sea verificable.

---

### [2026-07-25] — ADR-005: Las pruebas ejecutan el ataque, no comprueban la mitigación

* **Contexto:** La auditoría de julio encontró 16 bugs y 2 vulnerabilidades
  explotables que la suite existente (32 bloques, toda en verde) no detectaba,
  porque comprobaba caminos felices.
* **Decisión:** Dos suites nuevas que reproducen el fallo contra la aplicación
  real: `tests/test_regressions.py` (un caso por bug) y `tests/test_security.py`
  (levanta un servidor HTTP para verificar el SSRF, crea enlaces simbólicos para
  intentar escapar de `HOME`, ejecuta el `escapeHtml()` real del frontend con
  Node). Ambas salen con código 1 si una defensa se debilita.
* **Consecuencias:** Los tests son más lentos y dependen del entorno (Node para
  una comprobación). A cambio, no pueden pasar por casualidad: si alguien
  revierte un arreglo, la sonda vuelve a marcar el fallo.

---

### [2026-07-24] — ADR-001: Sustitución de Sortix por Martix y desinstalación del sistema
* **Contexto:** Existía en el sistema del usuario la versión previa (Sortix) ejecutándose al mismo tiempo que la nueva aplicación (Martix).
* **Decisión:** 
  1. Desinstalar completamente Sortix del PC del usuario: detener su proceso en segundo plano, eliminar los lanzadores `~/.config/autostart/sortix.desktop` y `~/.local/share/applications/sortix.desktop`, y deshabilitar su servicio systemd.
  2. Migrar la marca y configuración al nuevo proyecto unificado **Martix**.
* **Consecuencias:** Martix queda como el único organizador inteligente y explorador de archivos oficial en el sistema, evitando conflictos de puertos, duplicidad de consumo de RAM y vigilancias superpuestas.

---

### [2026-07-24] — ADR-002: Visualizador de espacio de disco
* **Contexto:** Martix operaba principalmente en segundo plano organizando descargas. Se requería una funcionalidad visual potente para analizar y gestionar el almacenamiento en disco de forma interactiva.
* **Decisión:**
  1. **Motor de Análisis (`backend/app/disk_analyzer.py`):** Algoritmo de escaneo recursivo de alto rendimiento que calcula tamaños acumulados, porcentaje del directorio padre, recuento de carpetas/archivos y clasificación de tipos de archivo por extensiones.
  2. **API REST (`backend/app/server.py`):**
     - `GET /api/disk/drives`: Listado de unidades y carpetas clave.
     - `POST /api/disk/scan`: Escaneo de ruta arbitraria o carpeta predeterminada.
     - `POST /api/disk/delete`: Eliminación segura de archivos/carpetas directamente desde la vista de análisis.
  3. **Interfaz de Usuario del Analizador (`frontend/`):**
     - **Barra de Resumen de Disco:** Espacio total, usado (% y barra azul) y libre (% y barra verde), más tiempo de escaneo.
     - **Vista de Árbol (Panel Izquierdo):** Jerarquía de carpetas con expansión/colapso, barras de progreso de % respecto al padre, tamaños formateados (GB/MB), conteos de elementos y filtro de texto.
     - **Desglose por Extensión (Panel Derecho):** Tabla ordenada por ocupación de espacio según tipo de archivo/extensión con barras de color.
     - **Treemap Interactivo (Panel Inferior):** Mapa visual dibujado en Canvas HTML5 con algoritmo de división squarified, rectángulos de tamaño proporcional, información en hover y vinculación directa de selección con la vista de árbol.
* **Consecuencias:** Martix evoluciona de un daemon pasivo a un explorador/analizador de espacio completo, permitiendo a los usuarios identificar y limpiar archivos pesados visualmente.

---

### [2026-07-24] — ADR-003: Instalador y desinstalador unificado de 1 clic
* **Contexto:** Se necesitaba una forma sencilla, estándar y automatizada de instalar Martix en cualquier equipo (escritorio nativo, servicio en segundo plano, comando CLI) o desinstalarlo limpiamente.
* **Decisión:**
  1. Crear scripts raíz `install.sh` / `installer.py` y `uninstall.sh` / `uninstaller.py`.
  2. **Instalador:**
     - Configura el entorno virtual `.venv` e instala dependencias.
     - Registra el acceso directo en el menú de aplicaciones (`~/.local/share/applications/martix.desktop`).
     - Registra el autostart al iniciar sesión (`~/.config/autostart/martix.desktop`).
     - Genera y activa el servicio systemd de usuario (`~/.config/systemd/user/martix.service`).
     - Instala el comando global `martix` en `~/.local/bin/martix`.
  3. **Desinstalador:** Detiene procesos/servicios y elimina de forma limpia todos los archivos de integración creados en el sistema.
* **Consecuencias:** Distribución e integración en el sistema operativo simplificadas y ejecutables con un solo comando.

---

### [2026-07-24] — ADR-004: Organización de carpetas y subdirectorios completos
* **Contexto:** Martix organizaba automáticamente archivos sueltos, pero ignoraba o dejaba sin mover carpetas o subdirectorios completos cuando los usuarios los descargaban o arrastraban a carpetas vigiladas.
* **Decisión:**
  1. **Clasificación de Carpetas (`backend/app/classifier.py` -> `classify_folder`):** Evalúa el nombre de la carpeta contra Temas activos y subcategorías. Si no coincide, analiza las extensiones de los archivos dentro de la carpeta para determinar la categoría predominante (imágenes, música, vídeos, documentos) o asignarla a `other`.
  2. **Motor de Movimiento Seguro (`backend/app/organizer.py` -> `organize_folder`, `is_destination_or_reserved_dir`):**
     - Mueve la carpeta completa como una unidad atómica usando sufijo único ante colisiones de nombre (`Carpeta (1)`).
     - **Guardas de Seguridad:** Impide explícitamente mover carpetas del sistema, la propia carpeta raíz (`HOME_DIR`, `DOWNLOADS_DIR`), subcarpetas reservadas (`node_modules`, `.venv`, `.git`, `scratch`, `build`), carpetas ocultas (`.`) o las propias carpetas de destino de categorías/temas, previniendo bucles infinitos o corrupción de rutas.
  3. **Patrulla Activa en Tiempo Real (`backend/app/watcher.py`):** Captura eventos de carpetas creadas/movidas y utiliza verificación de estabilidad recursiva (`_get_dir_stats`) asegurando que los archivos internos terminaron de copiado/descarga antes de mover la carpeta.
* **Consecuencias:** Martix organiza de forma homogénea tanto archivos individuales como directorios y álbumes completos.

---

### [2026-07-22] — ADR-000: Base del sistema y clasificación híbrida
* **Contexto:** Diseño inicial de la plataforma de organización 100% local.
* **Decisión:**
  - Cascada de reglas: Reglas por extensión > Reglas Scratch avanzadas (metadatos/condiciones) > Temas por palabra clave/OCR > IA Local opcional con Ollama > Categoría base.
  - Vigilancia en tiempo real multi-carpeta con Watchdog y programador de tareas en segundo plano (TaskScheduler).
  - Deduplicador en 2 pasos (Fast-Hash de 64KB + SHA256).

> **Nota sobre ADR-002, ADR-003 y ADR-004.** La auditoría de julio de 2026
> encontró fallos serios en las tres implementaciones: el borrado del analizador
> de espacio no tenía papelera ni confirmación, el desinstalador se mataba a sí
> mismo con `pkill -f martix` antes de limpiar nada, y las guardas de carpetas
> reservadas no consultaban las carpetas vigiladas. Las decisiones siguen en pie;
> lo que falló fue la implementación. Detalle en
> [auditoria-2026-07.md](auditoria-2026-07.md).
