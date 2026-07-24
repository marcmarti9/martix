# Auditoría de julio de 2026

Revisión completa del proyecto en dos tandas: **corrección** (bugs y malos
funcionamientos) y **seguridad**. Este documento recoge qué se encontró, cómo
se comprobó y qué se cambió.

**Resultado:** 16 bugs confirmados + 10 avisos en la primera tanda; 2
vulnerabilidades explotables + 8 debilidades en la segunda. Todo cerrado salvo
un punto convertido en opción del usuario y dos riesgos aceptados y
documentados.

---

## Método

No se auditó leyendo código y anotando sospechas. Para cada hipótesis se
escribió una sonda que **reproduce el fallo contra la aplicación real** en un
HOME y una base de datos temporales, y que informa de lo que observa. Las
sondas se quedaron en el repositorio como suites de regresión:

| Suite | Qué hace |
|---|---|
| `backend/tests/test_regressions.py` | 27 casos, uno por bug encontrado |
| `backend/tests/test_security.py` | 12 ataques reales contra la aplicación |
| `backend/tests/test_all.py` | Suite de integración previa (ampliada) |

Las dos primeras salen con código 1 si una defensa se debilita, así que sirven
en CI.

---

## Tanda 1 — Bugs y malos funcionamientos

### Críticos

**XSS por nombre de archivo, con acceso total a la API local.**
`escapeHtml()` usaba `textContent → innerHTML`, que escapa `< > &` pero **no
comillas**, y se interpolaba dentro de atributos entrecomillados
(`title="${escapeHtml(node.path)}"` en el analizador de espacio). Cadena
completa reproducida: una carpeta descargada llamada `x" onmouseover="…`
escapaba del atributo y ejecutaba JavaScript en el origen de Martix, con acceso
a `/api/disk/delete`.
→ `escapeHtml` escapa ahora también `"`, `'` y `` ` ``.

**`/api/disk/delete` borraba cualquier ruta sin confirmación ni papelera.**
Aceptaba cualquier ruta bajo `~` y hacía `shutil.rmtree` recursivo, sin
comprobar que viniera de un escaneo previo.
→ Rutas protegidas rechazadas con 403, borrado a la papelera, y confirmación
explícita por encima de 25 archivos.

**Crear la aplicación Flask borraba archivos.**
`create_app()` lanzaba un hilo con `run_maintenance_cleanup()`. Importar el
módulo destruía datos del usuario, y además duplicaba el trabajo del scheduler,
que también ejecutaba el mantenimiento nada más arrancar.
→ Eliminado. El scheduler espera un intervalo completo antes de su primera
ejecución.

**El desinstalador se suicidaba.**
`pkill -f martix` casa con la línea de comandos del propio desinstalador
(`python3 /…/martix/uninstaller.py`). Se mataba antes de limpiar los accesos
directos, el autostart y el servicio, que quedaban instalados para siempre.
También mataba editores o terminales con el proyecto abierto.
→ Ahora busca las rutas concretas del servidor y nunca su propio PID.

### Datos del usuario

**Deshacer un desempaquetado no recuperaba nada.** El `.zip` se borraba con
`unlink()`, y el undo solo renombraba la carpeta extraída a `algo.zip`, dejando
una *carpeta* con extensión de archivo.
→ El comprimido ya no se borra: se extrae y se archiva con un movimiento normal
y reversible. La extracción se registra aparte como evento no reversible.

**El botón "Deshacer" aparecía donde nunca podía funcionar.** Las filas de
mantenimiento guardaban `destination="DELETED"` como si fuera una ruta, y
`undo_move` hacía `Path("DELETED").exists()` — relativo al directorio de trabajo
del proceso.
→ Nueva columna `moves_log.undoable`; la interfaz oculta el botón y el backend
explica la vía correcta.

**El mantenimiento borraba *dotfiles* sin papelera** y dejaba un esqueleto de
carpetas vacías creciendo.
→ Papelera obligatoria, se saltan ocultos y rutas protegidas, se limpian las
carpetas que quedan vacías.

### Clasificación

**`UNIQUE(extension)` dejaba sin sentido toda la función de condiciones.** Era
imposible tener dos reglas `.pdf` con condiciones distintas: la segunda
sobrescribía a la primera en silencio (`ON CONFLICT DO UPDATE`). Justo el caso
de uso que anuncia el proyecto — "pdf con *factura*" y "pdf con *contrato*" — no
funcionaba.
→ Índice no único, nueva columna `priority`, reordenación desde la interfaz y
endpoints `PATCH /api/rules/<id>` y `POST /api/rules/reorder`.

**Archivos que no se archivaban nunca:**

- `is_temporary_download_file` buscaba `.part` como **subcadena**, así que
  `pelicula.part1.rar`, `datos.partition.csv` o `informe.particular.pdf` se
  trataban como descargas a medias. Los RAR multiparte son de lo más común.
- `is_file_in_use` abría en modo `r+b`, así que todo archivo de **solo lectura**
  daba `PermissionError` y se reportaba como "en uso". El watcher además
  malgastaba 5 minutos esperando por cada uno.

**La clasificación por contenido de `.docx` no funcionaba en ningún documento
real.** Se leían 20.000 bytes de `document.xml` y se parseaban de golpe: en
cualquier documento de más de unas páginas el XML quedaba cortado a mitad,
`ET.fromstring` lanzaba `ParseError` y se devolvía cadena vacía.
→ Parser incremental en streaming, con `defusedxml` cuando está disponible.

**Otros:**

- `gte` / `lte` estaban implementados en el motor pero la API los rechazaba con
  400.
- `content not_contains X` casaba con **todos** los binarios, porque el
  contenido no legible se trataba como cadena vacía y `"" not_contains X` es
  siempre cierto.
- Los patrones de renombrado con placeholders vacíos generaban nombres ocultos
  (`.pdf`) o vacíos — y `dest_dir / ""` es el propio directorio destino.
- `is_destination_or_reserved_dir` no consultaba `watched_folders`: Martix podía
  mover la carpeta que él mismo estaba vigilando.

### Robustez y rendimiento

- **Bomba de compresión**: no había límite de tamaño al descomprimir. Un `.zip`
  de 20 KB se expandía ×1023 sin control.
- **Analizador de disco**: `max_depth` solo filtraba qué nodos se *guardaban*;
  la recursión llegaba hasta el fondo. Un árbol de 60 niveles consumía 60 marcos
  de pila. Ahora son 4, gracias a un acumulador iterativo, más un presupuesto de
  tiempo con aviso de escaneo parcial.
- **Base de datos**: el esquema se revalidaba en cada conexión. Leer un ajuste
  costaba **10 sentencias SQL**; ahora 3. Las reglas se leen una vez por barrido
  en vez de una vez por archivo.
- **Scheduler**: hacía busy-wait cada 0,5 s — 172.800 despertares al día que
  impedían a la CPU entrar en estados de bajo consumo.
- **Watcher**: los 4 hilos worker se creaban al *importar* `server.py`, con la
  patrulla apagada. Ahora se crean bajo demanda, y la cola está acotada.
- **Windows**: cada archivo organizado abría un `MessageBox` **modal**. Treinta
  descargas eran treinta diálogos robando el foco. Ahora es un toast nativo.
- Carrera sin capturar en `organize_file` si el destino desaparecía entre
  `exists()` y `stat()`.
- Código muerto eliminado: `_get_scan_dirs`, `_find_all_files`,
  `_scan_duplicates`, `classifier.check_conditions`.

### Convertido en opción

**El watcher no es recursivo.** Un archivo creado directamente en
`~/Descargas/subcarpeta/` no dispara ningún evento. Es coherente con el diseño
(las carpetas se mueven enteras), así que en vez de cambiar el comportamiento
se añadió el ajuste `watch_recursive`, **apagado por defecto**.

---

## Tanda 2 — Seguridad

### Explotables

**SSRF en `/api/llm/test`.** El endpoint hacía una petición HTTP *desde el
servidor* a la URL que le pasaran, sin restringir el destino, y devolvía el
cuerpo al cliente. Servía para sondear puertos de localhost y de la red local a
través de Martix.
→ Nueva `security.is_loopback_url()`: solo IPs literales de loopback. Los
nombres de dominio se rechazan porque pueden resolver a otra cosa más tarde
(DNS rebinding).

**`/api/browse` listaba `~/.ssh`.** El explorador recorría credenciales y
configuración. Los nombres de archivo por sí solos ya dicen dónde están las
claves.
→ Las rutas protegidas se ocultan del listado y entrar en ellas devuelve 403.

### Debilidades corregidas

| Debilidad | Corrección |
|---|---|
| Sin Content-Security-Policy ni `X-Frame-Options` | CSP restrictiva sin destinos externos + `DENY` |
| `LLM_URL` sin validar pese a prometer "cero llamadas externas" | Se valida como loopback en cada llamada |
| Bomba de descompresión de imagen (OCR y EXIF) | `MAX_IMAGE_PIXELS` a 64 Mpx y warning → excepción |
| PDF hostil sin tope de tamaño | Máximo 256 MB antes de abrir cualquier archivo |
| `notify-send` interpretaba nombres con `-` como opciones | Separador `--` antes de los datos del usuario |
| `find_duplicates` sin límites dentro de la petición HTTP | Tope de 200.000 archivos y 120 s |

### Verificado como ya seguro

- Path traversal al servir el frontend: `send_from_directory` usa `safe_join`.
- Escape de la carpeta personal por enlace simbólico: `resolve_safe_path`
  resuelve el enlace antes de comprobar la contención.

### Riesgos aceptados

Documentados en [seguridad.md](seguridad.md#4-riesgos-aceptados): el token en
`localStorage` (mitigado por la CSP) y la aceptación de peticiones sin cabecera
`Origin` (inherente a una API local; la mitigación es `MARTIX_TOKEN`).

---

## Migración desde versiones anteriores

Automática al arrancar, en `db._migrate()`. No hay que hacer nada.

- `rules`: se elimina el índice único sobre `extension` y se añade `priority`.
  Si el índice venía de una restricción de columna, la tabla se rehace
  conservando todas las reglas.
- `moves_log`: nueva columna `undoable`. Las filas antiguas de categoría
  `mantenimiento` o `desempaquetado` se marcan como no reversibles.

Verificado sobre la base de datos real en uso: la migración se aplicó sin
perder reglas.

Dos dependencias nuevas, **ambas opcionales** (hay camino alternativo si
faltan): `Send2Trash` para la papelera nativa y `defusedxml` para el parseo
reforzado de XML.
