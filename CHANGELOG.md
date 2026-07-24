# Historial de cambios

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).

---

## [Sin publicar]

### Seguridad

- **Corregido un XSS explotable con acceso a la API local.** `escapeHtml()` no
  escapaba comillas y se usaba dentro de atributos HTML: una carpeta descargada
  con un nombre preparado escapaba del atributo y ejecutaba JavaScript en el
  origen de Martix, con acceso a los endpoints de borrado. **Actualiza.**
- **Corregido un SSRF** en `POST /api/llm/test`: hacía peticiones desde el
  servidor a cualquier URL y devolvía la respuesta, lo que permitía sondear
  localhost y la red local a través de Martix. Ahora solo se aceptan IPs
  literales de loopback.
- **`/api/browse` ya no lista `~/.ssh`, `~/.aws` ni `~/.gnupg`.** Los nombres de
  archivo por sí solos indican dónde están las claves.
- **`create_app()` ya no borra archivos.** Crear la aplicación Flask lanzaba un
  hilo de mantenimiento que eliminaba documentos del usuario como efecto
  secundario de arrancar o importar el módulo.
- **`/api/disk/delete` ya no hace `rmtree` sobre cualquier ruta.** Rechaza rutas
  protegidas con 403, envía a la papelera y exige confirmación por encima de 25
  archivos.
- El contenido de los documentos ya no puede salir del equipo: `MARTIX_LLM_URL`
  se valida como loopback en cada llamada.
- Añadidas Content-Security-Policy restrictiva y `X-Frame-Options: DENY`.
- Límites contra bombas de compresión (`.zip`, `.docx`) y de descompresión de
  imagen; tope de 256 MB antes de abrir cualquier archivo para leerlo.
- `notify-send` recibe `--` antes de los datos del usuario: un archivo llamado
  `--expire-time=0` se interpretaba como opción del comando.

### Añadido

- **Papelera** (`app/trash.py`): ningún borrado es definitivo. Usa la papelera
  nativa del escritorio (`send2trash`) o una cuarentena propia restaurable.
  Nuevos endpoints `GET /api/trash`, `POST /api/trash/<id>/restore`,
  `DELETE /api/trash/<id>`.
- **Prioridad en las reglas**: varias reglas pueden compartir extensión y el
  orden decide cuál gana. Reordenables desde la interfaz. Nuevos endpoints
  `PATCH /api/rules/<id>` y `POST /api/rules/reorder`.
- Operadores `gte` y `lte` en las condiciones (estaban implementados en el motor
  pero la API los rechazaba).
- Ajuste `watch_recursive` para vigilar también las subcarpetas (apagado por
  defecto).
- Aviso de escaneo parcial en el analizador de espacio cuando se agota el
  presupuesto de tiempo.
- Suites `tests/test_regressions.py` (27 casos) y `tests/test_security.py`
  (12 ataques), más CI en GitHub Actions.
- Documentación completa en `docs/`.

### Corregido

- **`UNIQUE(extension)` hacía inútiles las condiciones de las reglas.** Crear una
  segunda regla `.pdf` sobrescribía la primera en silencio, así que era
  imposible tener "pdf con *factura*" y "pdf con *contrato*" a la vez.
- **Archivos que no se archivaban nunca:** los que contenían `.part` en el
  nombre (`pelicula.part1.rar`, `datos.partition.csv`) y **todos** los de solo
  lectura, que se reportaban como "en uso".
- **La clasificación por contenido de `.docx` no funcionaba en ningún documento
  real:** el XML se truncaba a 20 KB y el parseo fallaba siempre.
- **Deshacer un desempaquetado no recuperaba nada:** el `.zip` se borraba y el
  undo solo renombraba la carpeta extraída. Ahora el comprimido se conserva y su
  archivado sí es reversible.
- El botón "Deshacer" aparecía en filas donde nunca podía funcionar
  (desempaquetados, mantenimiento).
- `content not_contains X` casaba con todos los archivos binarios.
- Los patrones de renombrado con placeholders vacíos generaban nombres ocultos
  (`.pdf`) o vacíos.
- Martix podía mover la carpeta que él mismo estaba vigilando.
- El mantenimiento borraba *dotfiles* de configuración y dejaba carpetas vacías.
- **El desinstalador se mataba a sí mismo** (`pkill -f martix` casa con su propia
  línea de comandos) y nunca llegaba a limpiar los accesos directos, el
  autostart ni el servicio.
- En Windows, cada archivo organizado abría un diálogo modal en vez de una
  notificación.
- Carrera al comprobar duplicados en el destino si otro worker lo eliminaba.
- Los enlaces simbólicos se excluyen del organizado, el barrido, el
  mantenimiento y la deduplicación.

### Rendimiento

- Leer un ajuste pasa de 10 sentencias SQL a 3: el esquema se valida una vez por
  proceso, no en cada conexión.
- Las reglas se leen una vez por barrido, no una vez por archivo.
- El analizador de espacio usa un acumulador iterativo: un árbol de 60 niveles
  pasa de 60 marcos de pila a 4.
- El scheduler espera el intervalo real en vez de despertar cada 0,5 s
  (172.800 despertares diarios menos).
- Los 4 hilos del watcher se crean bajo demanda, no al importar `server.py`.
- Límites en la búsqueda de duplicados (200.000 archivos, 120 s).

### Migración

Automática al arrancar. La tabla `rules` pierde el índice único y gana
`priority`; `moves_log` gana `undoable`. No se pierde ninguna regla.

Dos dependencias nuevas, ambas **opcionales** (hay camino alternativo si
faltan): `Send2Trash` y `defusedxml`.

---

## [2026-07-24]

### Añadido

- Analizador visual de espacio en disco: árbol con porcentaje del padre,
  desglose por extensión y treemap *squarified* interactivo en Canvas.
- Instalador y desinstalador unificados de un clic (`install.sh` /
  `uninstall.sh`) con acceso de escritorio, autostart, servicio systemd y
  comando `martix`.
- Organización de carpetas y subdirectorios completos, no solo archivos sueltos.
- La ruta de destino aparece en las notificaciones del sistema.

### Cambiado

- El proyecto pasa de llamarse Sortix a **Martix**.

---

## [2026-07-22]

### Añadido

- Patrulla multi-carpeta en tiempo real sobre Descargas y carpetas vigiladas.
- Programador de tareas en segundo plano para mantenimiento y barridos.
- Empaquetado de un clic con PyInstaller (`build_desktop.py`).
- Deduplicación en dos fases (fast-hash de 64 KB + SHA256).
- Metadatos EXIF e ID3 en condiciones y plantillas de renombrado.

---

## [2026-07-19]

### Añadido

- Primera versión: clasificación por reglas y Temas, patrulla con watchdog,
  simulación, historial con deshacer, estadísticas y endurecimiento inicial
  (anti path-traversal, anti Zip-Slip, guardas de Host/Origin, token de API).
