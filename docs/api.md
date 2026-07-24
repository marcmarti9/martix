# Referencia de la API REST

Base: `http://127.0.0.1:5000`. Todas las respuestas son JSON.

**Autenticación.** Ninguna mientras Martix escuche solo en `127.0.0.1`. Si
defines `MARTIX_TOKEN` en `backend/.env`, toda ruta `/api/*` exige la cabecera
`X-Martix-Token`. Es **obligatorio** si cambias `HOST`: el servidor se niega a
arrancar sin él.

**Guardas comunes** (`app/security.py:check_request`): la cabecera `Host` debe
ser local; en métodos que cambian estado, si el navegador envía `Origin`, debe
ser de confianza. Cuerpo máximo: 2 MB.

---

## Estado y control

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/status` | Patrulla activa, total organizado, carpeta de descargas |
| `POST` | `/api/patrol/toggle` | Enciende/apaga la patrulla. Cuerpo: `{"active": true}` (opcional, alterna si falta) |
| `POST` | `/api/organize-now` | Barrido inmediato de Descargas y carpetas vigiladas |
| `POST` | `/api/simulate` | Dry-run: qué haría con cada archivo, sin mover nada |
| `GET` | `/api/statistics` | Total, top categorías y actividad de 30 días |

## Reglas

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/rules` | Reglas **en orden de evaluación** (la primera que casa gana) |
| `POST` | `/api/rules` | Crea una regla. Varias pueden compartir extensión |
| `PATCH`/`PUT` | `/api/rules/<id>` | Modifica campos concretos |
| `POST` | `/api/rules/reorder` | Reordena. Cuerpo: `{"ids": [3, 1, 2]}` |
| `DELETE` | `/api/rules/<id>` | Elimina |
| `GET` | `/api/rules/export` | Exporta reglas y reglas de mantenimiento |
| `POST` | `/api/rules/import` | Importa (las inválidas se descartan en silencio) |

```jsonc
// POST /api/rules
{
  "extension": "pdf",              // o "*" para comodín
  "destination": "Documents/Facturas",  // relativa a tu carpeta personal
  "rename_pattern": "{FILE_YYYY}-{OriginalName}",   // opcional
  "conditions": [                  // opcional, se combinan con AND
    { "field": "content", "operator": "contains", "value": "factura" }
  ]
}
```

**Campos:** `name`, `stem`, `extension`, `size_kb`, `age_days`, `content`,
`artist`, `album`, `title`, `year`, `camera`, `exif_date`.
**Operadores:** `contains`, `not_contains`, `equals`, `starts_with`,
`ends_with`, `gt`, `lt`, `gte`, `lte`.

> El orden importa: una regla `.pdf` sin condiciones colocada arriba deja
> muertas a todas las `.pdf` condicionales de debajo. Ver
> [arquitectura.md](arquitectura.md#4-modelo-de-datos).

**Placeholders de renombrado:** `{YYYY}` `{MM}` `{DD}` (hoy), `{FILE_YYYY}`
`{FILE_MM}` `{FILE_DD}` (fecha del archivo), `{OriginalName}`, `{Topic}`,
`{Category}`, `{ext}`, `{ARTIST}`, `{ALBUM}`, `{TITLE}`, `{CAMERA}`,
`{EXIF_DATE}`, `{YEAR}`. Si el patrón se resuelve a vacío se conserva el nombre
original.

## Temas

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/topics` | Lista |
| `POST` | `/api/topics` | `{"name", "destination", "keywords": [...], "rename_pattern"}` |
| `DELETE` | `/api/topics/<id>` | Elimina |

## Historial

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/log?limit=50` | Movimientos recientes (máx. 500) |
| `POST` | `/api/log/<id>/undo` | Devuelve el archivo a su origen |

Cada fila incluye `undoable`. Es `false` en desempaquetados y borrados de
mantenimiento: no son movimientos y no hay nada que devolver. Intentar
deshacerlos responde `409` con la vía correcta.

## Papelera

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/trash` | `{"native": bool, "items": [...]}` |
| `POST` | `/api/trash/<id>/restore` | Devuelve el elemento a su ruta original |
| `DELETE` | `/api/trash/<id>` | Borra definitivamente |

`native: true` significa que se usa la papelera del escritorio (`send2trash`) y
que se recupera desde el gestor de archivos, no desde aquí.

## Explorador

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/tree` | Árbol de la barra lateral |
| `GET` | `/api/browse?path=Documents` | Contenido de una carpeta |

Las rutas protegidas (`~/.ssh`, `~/.config`…) se ocultan del listado y devuelven
`403` si se intenta entrar.

## Carpetas vigiladas

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/watched-folders` | Lista |
| `POST` | `/api/watched-folders` | `{"folder_path": "Escritorio/Escaneos"}` |
| `DELETE` | `/api/watched-folders/<id>` | Elimina |

## Mantenimiento

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/maintenance/rules` | Lista (alias: `/api/maintenance`) |
| `POST` | `/api/maintenance/rules` | `{"directory_path", "max_age_days", "active"}` |
| `DELETE` | `/api/maintenance/rules/<id>` | Elimina |
| `POST` | `/api/maintenance/run` | Ejecuta ahora |

Los archivos van a la **papelera**, no se borran. Se saltan los ocultos y las
rutas protegidas.

## Duplicados

| Método | Ruta | Descripción |
|---|---|---|
| `GET`/`POST` | `/api/duplicates` | Busca. `POST {"directories": [...]}` para acotar |
| `POST` | `/api/duplicates/clean` | `{"files": [...]}` → a la papelera |

Dos fases: agrupación por tamaño → fast-hash de 64 KB → SHA256 completo.
Acotado a 200.000 archivos y 120 s.

## Analizador de espacio

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/disk/drives` | Ubicaciones escaneables |
| `POST` | `/api/disk/scan` | `{"path": "Documents"}` |
| `POST` | `/api/disk/delete` | `{"path": "...", "confirm": false}` |

`scan` devuelve `truncated: true` si se agotó el presupuesto de tiempo; los
totales son entonces incompletos.

`delete` responde `409` con `needs_confirmation` y `file_count` si la carpeta
tiene más de 25 archivos; repite con `"confirm": true`. Devuelve `403` en rutas
protegidas. Siempre va a la papelera.

## Ajustes

| Método | Ruta | Descripción |
|---|---|---|
| `GET`/`POST` | `/api/settings` | Ajustes generales |

```jsonc
{
  "duplicate_action": "suffix",  // "suffix" | "skip" | "delete_source"
  "onboarded": true,
  "unpack_archives": true,
  "watch_recursive": false,      // vigilar subcarpetas (ver nota abajo)
  "native_trash": true           // solo lectura: si send2trash está disponible
}
```

> `watch_recursive` archiva cada archivo interno por separado, lo que deshace la
> estructura de las carpetas descargadas. Por eso está apagado por defecto.

## Programador

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/scheduler/config` | Configuración actual |
| `POST`/`PUT` | `/api/scheduler/config` | `{"enabled": true, "interval_minutes": 60}` |
| `POST` | `/api/scheduler/run` | Ejecuta ya (alias: `/run-now`) |

## LLM local

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/llm/status` | Si está activado, URL y modelo |
| `POST` | `/api/llm/test` | Prueba la conexión con Ollama |
| `POST` | `/api/learn-correction` | Sugiere una regla a partir de una corrección manual |

`/api/llm/test` **solo acepta direcciones de loopback** (IP literal o
`localhost`). Cualquier otro destino devuelve `400`: sin esta restricción el
endpoint sería un SSRF, y la promesa de privacidad no tendría respaldo.

---

## Errores

| Código | Significado |
|---|---|
| `400` | Entrada inválida (ruta no permitida, condición no reconocida…) |
| `401` | Token ausente o incorrecto |
| `403` | Host/Origin no reconocido, o ruta protegida |
| `404` | No existe |
| `409` | Conflicto: undo imposible, o confirmación requerida |
| `413` | Cuerpo mayor de 2 MB |
| `500` | Error interno (el detalle va al log, no a la respuesta) |
