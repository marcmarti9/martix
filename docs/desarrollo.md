# Guía de desarrollo

## Puesta en marcha

```bash
git clone https://github.com/marcmarti9/martix.git
cd martix/backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Abre `http://127.0.0.1:5000`. Para la ventana de escritorio: `python desktop.py`
(necesita `requirements-desktop.txt`).

## Estructura

```
backend/
├── app/
│   ├── browser.py        Navegación segura (resolve_safe_path)
│   ├── classifier.py     "¿Qué es este archivo?" — Temas, OCR, EXIF/ID3
│   ├── db.py             SQLite, esquema y migraciones
│   ├── disk_analyzer.py  Escaneo de espacio y datos del treemap
│   ├── llm.py            Ollama local (opcional)
│   ├── organizer.py      Motor: reglas, movimiento, undo, mantenimiento
│   ├── scheduler.py      Tareas periódicas
│   ├── security.py       Políticas: rutas, validación, guardas HTTP
│   ├── server.py         API REST
│   ├── trash.py          Papelera / cuarentena
│   └── watcher.py        Patrulla en tiempo real (watchdog)
├── config/
│   ├── categories.json   Categorías, extensiones y subcategorías
│   └── settings.py       .env, rutas base, predicados de archivo
├── deploy/               Servicios por plataforma
├── tests/
│   ├── test_all.py         Integración
│   ├── test_regressions.py Un caso por bug de la auditoría
│   └── test_security.py    Ataques reales contra la aplicación
├── main.py               Punto de entrada
└── desktop.py            Ventana pywebview

frontend/                 HTML + CSS + JS, sin frameworks ni CDNs
database/scripts/         schema.sql
docs/                     Esta documentación
```

## Tests

```bash
cd backend
.venv/bin/python tests/test_all.py          # integración
.venv/bin/python tests/test_regressions.py  # regresiones (código 1 si falla)
.venv/bin/python tests/test_security.py     # seguridad (código 1 si falla)
```

Las tres son autocontenidas: crean un HOME y una base de datos temporales, así
que **no tocan tus archivos**. Se ejecutan en CI en cada push.

### Cómo escribir tests aquí

La convención del proyecto es **reproducir el problema, no comprobar que existe
una mitigación**. Un test que hace `grep` de una constante no prueba nada; uno
que crea un archivo hostil y comprueba qué hace la aplicación, sí.

`test_security.py` levanta un servidor HTTP real para verificar el SSRF, crea
enlaces simbólicos para intentar escapar de la carpeta personal, y ejecuta el
`escapeHtml()` real del frontend con Node para comprobar el escapado. Ese es el
nivel al que apuntar.

Al arreglar un bug, añade su caso a `test_regressions.py`.

## Convenciones

- **Comentarios en español**, como el resto del código.
- Los comentarios explican **por qué**, no qué. Si un comentario describe lo que
  hace la línea de al lado, sobra. Si explica una restricción no obvia (una
  condición de carrera, un formato heredado, un fallo del pasado), es valioso.
- Cualquier ruta que venga de la interfaz pasa por `browser.resolve_safe_path`.
- Cualquier borrado pasa por `trash.move_to_trash`. **Nunca** `unlink()` ni
  `rmtree()` directos sobre archivos del usuario.
- Cualquier salida a HTML pasa por `escapeHtml`.
- SQL siempre con parámetros enlazados.

## Base de datos

SQLite en `database/martix.db` (fuera del control de versiones). El esquema está
en `database/scripts/schema.sql` y las migraciones en `db._migrate()`.

Para añadir una migración: comprueba si el cambio ya está aplicado
(`PRAGMA table_info`), aplícalo si no, y hazlo idempotente. Se ejecuta una vez
por proceso, en el primer acceso.

Empezar de cero: para el servidor y borra `database/martix.db`. Se regenera.

## Empaquetado

```bash
cd backend
python build_desktop.py     # binario en backend/dist/
```

## Depuración

```bash
tail -f ~/.local/share/martix/*.log          # si has configurado logging a archivo
journalctl --user -u martix.service -f       # servicio systemd
```

Los módulos usan `logging` con los nombres `martix.organizer`, `martix.server`,
`martix.scheduler`, `martix.trash`, `martix.llm`.

Para ver qué haría Martix sin que mueva nada, usa la simulación
(`POST /api/simulate` o el botón "Simular" de la interfaz).
