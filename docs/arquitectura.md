# Arquitectura de Martix

Cómo funciona el sistema por dentro: qué hace cada módulo, cómo viaja un
archivo desde que aparece en Descargas hasta que queda archivado, y por qué
las piezas están donde están.

> Si buscas *por qué* se tomó cada decisión, está en [decisiones.md](decisiones.md).
> Si buscas la referencia de endpoints, está en [api.md](api.md).

---

## 1. Vista general

Martix es un proceso Python que hace tres cosas a la vez:

```
┌──────────────────────────────────────────────────────────────────┐
│                      Proceso único de Martix                      │
│                                                                   │
│  ┌────────────────┐  ┌─────────────────┐  ┌───────────────────┐  │
│  │   Servidor     │  │  Patrulla       │  │   Programador     │  │
│  │   Flask        │  │  (watchdog)     │  │   (scheduler)     │  │
│  │                │  │                 │  │                   │  │
│  │ Sirve la UI y  │  │ Reacciona a     │  │ Barridos y        │  │
│  │ la API REST    │  │ archivos nuevos │  │ mantenimiento     │  │
│  │ en 127.0.0.1   │  │ en tiempo real  │  │ periódicos        │  │
│  └───────┬────────┘  └────────┬────────┘  └─────────┬─────────┘  │
│          │                    │                     │             │
│          └────────────────────┴─────────────────────┘             │
│                               │                                   │
│                    ┌──────────▼──────────┐                        │
│                    │   organizer.py      │  ← toda decisión de    │
│                    │  (motor de archivo) │    mover pasa por aquí │
│                    └──────────┬──────────┘                        │
│                               │                                   │
│         ┌─────────────────────┼─────────────────────┐             │
│         ▼                     ▼                     ▼             │
│   classifier.py         security.py            db.py              │
│   (¿qué es esto?)    (¿puedo tocarlo?)      (SQLite)              │
└──────────────────────────────────────────────────────────────────┘
```

Tres invariantes que sostienen el diseño:

1. **Nada sale del equipo.** La única petición saliente posible es al LLM
   local, y se valida en cada llamada que el destino sea loopback.
2. **Nada se borra de verdad.** Todo borrado pasa por la papelera.
3. **Nada se toca fuera de la carpeta personal.** Toda ruta que llega de la
   interfaz se resuelve y se valida contra `HOME_DIR` antes de usarse.

---

## 2. Módulos

### `config/settings.py` — configuración y detección de entorno

Punto único donde se leen `.env`, las rutas base y `categories.json`. Sin
dependencias externas a propósito, para que arranque en cualquier máquina.

Expone además dos predicados que usa todo el sistema:

- `is_temporary_download_file(path)` — descarta artefactos de descarga a medias
  (`.crdownload`, `.part`, prefijos de Chrome/Drive). Mira **solo el sufijo
  real y los prefijos conocidos**: buscar `.part` como subcadena marcaba como
  temporales archivos normales (`pelicula.part1.rar`).
- `is_file_in_use(path)` — detecta si otro proceso está escribiendo el archivo.
  En POSIX usa `flock` sobre un descriptor de **lectura**; en Windows intenta
  abrirlo. Un archivo de solo lectura no está "en uso".

### `app/security.py` — políticas de seguridad

Es el módulo de políticas, no de mecanismos. Contiene:

| Función | Responsabilidad |
|---|---|
| `clean_destination(raw)` | Normaliza un destino escrito por el usuario a ruta relativa segura. Rechaza absolutas, unidades de Windows, `..`, nombres reservados |
| `safe_destination_dir(rel)` | Última barrera antes de mover: convierte a absoluta revalidando contra `HOME_DIR` |
| `valid_extension` / `valid_conditions` | Validan lo que entra por la API antes de tocar la base de datos |
| `is_protected_path(path)` | ¿Es intocable? `~/.ssh`, `~/.config`, la propia BD… |
| `is_loopback_url(url)` | ¿Este destino de red es este mismo equipo? AntisiSRF y barrera de privacidad |
| `check_request(request)` | Guardas HTTP: Host (anti DNS-rebinding), Origin (anti CSRF), token |

**Dos conjuntos distintos de rutas protegidas**, y la diferencia importa:

- `EXACT_PROTECTED_PATHS` — solo por coincidencia exacta (`~`, la raíz). No se
  pueden mover ni borrar, pero su *contenido* sí: si no, Martix no podría
  organizar nada.
- `PROTECTED_SUBTREES` — ellos y todo su interior (`~/.ssh`, `~/.gnupg`,
  `~/.config`, la carpeta de datos de Martix).

### `app/browser.py` — navegación segura

`resolve_safe_path(raw)` es el embudo por el que pasa **toda** ruta que llega
de la interfaz. Resuelve enlaces simbólicos *antes* de comprobar la
contención, así que un enlace dentro de la carpeta personal apuntando a `/etc`
se rechaza. `list_directory` oculta además las rutas protegidas: los nombres de
archivo de `~/.ssh` ya son información útil para un atacante.

### `app/classifier.py` — "¿qué es este archivo?"

Decide categoría y carpeta destino, sin mover nada. Cascada:

```
1. Temas del usuario     → por nombre, y si no, por CONTENIDO (PDF/DOCX/TXT/OCR)
2. Subcategorías         → patrones en el nombre (capturas, facturas, CVs…)
3. LLM local (opcional)  → solo si MARTIX_LLM=1 y nada anterior encajó
4. Categoría base        → por extensión (fallback final)
```

La extracción de contenido está deliberadamente acotada:

- **PDF**: 6 páginas, 20.000 caracteres, archivo ≤ 256 MB.
- **DOCX**: `document.xml` se parsea **en streaming** con un parser incremental,
  con tope de 8 MB descomprimidos y rechazo de cualquier DTD. Antes se leían
  20.000 bytes y se parseaban de golpe, lo que fallaba en todo documento real.
- **Imágenes (OCR)**: `MAX_IMAGE_PIXELS` a 64 Mpx y `DecompressionBombWarning`
  convertido en excepción.

`content_is_extractable(ext)` distingue "no se pudo leer" de "se leyó y estaba
vacío". Sin esa distinción, una condición `content not_contains X` casaba con
todos los binarios del sistema.

### `app/organizer.py` — el motor

Todo movimiento de archivos pasa por aquí. Piezas principales:

- **`resolve_destination_folder(path, rules)`** — aplica la primera regla del
  usuario que case; si ninguna, delega en `classify()`.
- **`check_conditions(path, ext, conditions, facts)`** — evalúa las condiciones
  en AND. `FileFacts` cachea lo caro (stat, contenido, metadatos) para que una
  regla con tres condiciones de contenido no abra el PDF tres veces.
- **`format_rename_pattern(...)`** — sustituye placeholders, sanea el nombre y,
  si el resultado queda vacío, **conserva el nombre original**.
- **`unpack_archive(...)`** — descompresión con validación de Zip-Slip, enlaces
  que escapan, rutas absolutas, nodos de dispositivo, y presupuesto de tamaño /
  ratio / entradas / espacio libre.
- **`organize_file` / `organize_folder`** — el movimiento en sí, bajo
  `_move_lock` (elegir nombre libre y mover debe ser una sección crítica: hay 4
  workers concurrentes).
- **`run_maintenance_cleanup()`** — borrado por antigüedad, siempre a la
  papelera, saltando ocultos y rutas protegidas, y limpiando carpetas vacías.

### `app/trash.py` — la papelera

Ningún borrado de Martix es definitivo. Dos estrategias:

1. Si hay `send2trash`, se usa la **papelera nativa del escritorio** y el
   usuario recupera desde su gestor de archivos habitual.
2. Si no, **cuarentena propia** en la carpeta de datos, con índice JSON y
   restauración desde la API.

### `app/watcher.py` — patrulla en tiempo real

`PatrolManager` gestiona las vigilancias de watchdog; `_DownloadEventHandler`
recibe los eventos y los mete en una **cola acotada** que consumen 4 workers
creados bajo demanda.

Antes de mover nada, `_wait_until_stable` espera a que el archivo deje de
crecer (5 comprobaciones estables, hasta 5 minutos). Para carpetas mide el
tamaño y el recuento del árbol completo, para pillar descargas tipo Drive.

### `app/scheduler.py` — tareas periódicas

Un hilo que ejecuta mantenimiento y barrido cada N minutos. Espera el intervalo
real (con despertares de como mucho 60 s para notar cambios de configuración),
no hace busy-wait. La primera ejecución espera un intervalo completo: arrancar
Martix no debe disparar un borrado.

### `app/db.py` — persistencia

SQLite en modo WAL. El esquema se valida **una vez por proceso** (no en cada
conexión) y se revalida si la base de datos desaparece en caliente. Contiene
también las migraciones para bases de datos de versiones anteriores.

### `app/disk_analyzer.py` — analizador de espacio

Escaneo con dos regímenes: por encima de `max_depth` construye nodos del árbol
para la interfaz; por debajo usa un **acumulador iterativo** que suma tamaños
sin gastar pila. Todo el escaneo está acotado por un presupuesto de tiempo, y
si se agota devuelve `truncated: true` para que la interfaz lo diga en vez de
presentar totales incompletos como definitivos.

### `frontend/` — interfaz

JavaScript sin frameworks ni dependencias externas (lo exige la CSP y el
principio de "todo local"). `app.js` contiene el i18n ES/EN, el explorador, el
constructor de reglas, el analizador de disco y el treemap en Canvas.

`escapeHtml()` escapa `& < > " ' \``. Las comillas **no son opcionales**: se
interpola dentro de atributos, y los nombres de archivo los controla quien
envía la descarga.

---

## 3. Flujo completo de un archivo

Qué ocurre cuando guardas `factura_luz_marzo.pdf` en `~/Descargas`:

```
1. watchdog          on_created → _schedule()
                     ¿es temporal (.crdownload)? ¿es carpeta reservada?
                          │
2. cola acotada      un worker lo recoge (máx. 4 en paralelo)
                          │
3. _wait_until_stable  espera a que el tamaño no cambie 5 veces seguidas
                       y a que ningún proceso lo tenga bloqueado
                          │
4. organize_file     ¿existe? ¿es enlace? ¿0 bytes? ¿ruta protegida?
                          │
5. ¿es comprimido?   sí → unpack_archive() con todos los límites,
                          se extrae y se SIGUE (el .zip no se borra)
                          │
6. resolve_destination_folder
                     │
                     ├─ reglas del usuario, por orden de prioridad
                     │  (primera que case gana; FileFacts cachea lo caro)
                     │
                     └─ si ninguna → classifier.classify()
                        ├─ Temas (nombre → contenido/OCR)
                        ├─ Subcategorías por patrón
                        ├─ LLM local (si está activado)
                        └─ categoría por extensión
                          │
7. safe_destination_dir  revalida que el destino cae dentro de ~
                          │
8. format_rename_pattern  si la regla renombra; si queda vacío, nombre original
                          │
9. [_move_lock]      elegir nombre libre + shutil.move como sección crítica
                     ¿ya existe idéntico? → según ajuste: sufijo / omitir /
                                             enviar el origen a la papelera
                          │
10. db.log_move      queda en el historial, reversible desde la interfaz
                          │
11. notificación     toast nativo del sistema
```

---

## 4. Modelo de datos

```sql
rules            -- reglas del usuario. VARIAS por extensión: es lo que
                 -- permite "pdf con 'factura'" y "pdf con 'contrato'".
                 -- 'priority' fija el orden de evaluación (menor = antes).

topics           -- Temas por palabras clave (Banco, Gimnasio…)

moves_log        -- historial. 'undoable' distingue los movimientos
                 -- reversibles de los eventos que no lo son
                 -- (desempaquetados, borrados de mantenimiento).

settings         -- clave/valor: patrulla activa, acción ante duplicados…

maintenance_rules -- borrado por antigüedad, por carpeta

watched_folders  -- carpetas vigiladas además de Descargas
```

**Orden de evaluación de reglas** (`db._RULES_ORDER`), y el orden *es* la
semántica:

1. `priority` — lo fija el usuario, reordenable desde la interfaz.
2. Extensión concreta antes que comodín `*` (por orden ASCII, `*` iría primero
   y silenciaría toda regla específica).
3. Reglas **con** condiciones antes que las que no las tienen: son más
   específicas, y si no una regla `.pdf → Documentos` sin condiciones dejaría
   muerta a `.pdf que contiene factura → Facturas`.
4. `id`, para que el orden sea estable.

---

## 5. Concurrencia

| Hilo | Cuántos | Qué hace |
|---|---|---|
| Flask | según petición | Atiende la API y sirve la interfaz |
| Observer de watchdog | 1 | Recibe eventos del sistema de archivos |
| Workers de patrulla | 4 (bajo demanda) | Esperan estabilidad y organizan |
| Scheduler | 1 | Barrido y mantenimiento periódicos |
| Notificaciones | efímero | Un hilo por notificación, no bloquea |

Puntos de sincronización:

- **`organizer._move_lock`** — elegir un nombre de destino libre y mover es un
  *check-then-act*. Sin el lock, dos workers pueden ver el mismo destino como
  libre a la vez y uno pisa el archivo del otro.
- **`db._schema_lock`** — la validación del esquema ocurre una sola vez.
- **`trash._lock`** — el índice JSON de la cuarentena se escribe de forma atómica.
- **`PatrolManager._lock`** — alta y baja de vigilancias.

---

## 6. Cómo añadir cosas

**Un campo nuevo de condición** (p. ej. "número de páginas"):

1. `security._VALID_CONDITION_FIELDS` — permitirlo en la API.
2. `organizer.FileFacts.value_for()` — saber calcularlo (y cachearlo).
3. `frontend/app.js` — añadirlo al desplegable y al i18n (`cond_field_*`).
4. `backend/tests/test_regressions.py` — un caso que lo ejercite.

**Un endpoint nuevo**: si acepta rutas, pasa por `browser.resolve_safe_path`;
si borra, por `_safe_delete_target` y `trash.move_to_trash`. Nunca `unlink()`
ni `rmtree()` directos.

**Una categoría nueva**: `backend/config/categories.json`. Se lee al importar,
así que hay que reiniciar.
