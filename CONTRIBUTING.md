# Contribuir a Martix

Gracias por querer mejorar Martix. Este documento cubre lo imprescindible; la
guía completa de desarrollo está en [docs/desarrollo.md](docs/desarrollo.md).

## Reglas de la casa

Martix tiene permisos sobre toda la carpeta personal del usuario y procesa
archivos descargados de internet. Tres cosas no se negocian:

1. **Todo local.** Sin telemetría, sin analítica, sin llamadas a servicios
   externos. La única petición saliente posible es al LLM local, y se valida en
   cada llamada que el destino sea loopback.
2. **Ningún borrado es definitivo.** Nada de `unlink()` ni `rmtree()` sobre
   archivos del usuario: todo pasa por `trash.move_to_trash()`.
3. **Ninguna ruta se usa sin validar.** Lo que llega de la interfaz pasa por
   `browser.resolve_safe_path()`; los destinos de reglas, por
   `security.clean_destination()`.

Además: la rama `main` está protegida, todo entra por pull request.

## Puesta en marcha

```bash
cd backend
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/python main.py        # interfaz en http://127.0.0.1:5000
```

## Tests

Las tres suites son autocontenidas: usan un HOME y una base de datos temporales,
así que nunca tocan tus archivos.

```bash
cd backend
./.venv/bin/python tests/test_all.py           # integración
./.venv/bin/python tests/test_regressions.py   # regresiones de la auditoría
./.venv/bin/python tests/test_security.py      # ataques reales
```

Las tres tienen que pasar antes de abrir un PR. También se ejecutan en CI.

### Cómo se escriben los tests aquí

**Reproduce el problema, no compruebes que existe una mitigación.** Un test que
hace `grep` de una constante no demuestra nada; uno que crea un archivo hostil y
observa qué hace la aplicación, sí.

- ¿Arreglas un bug? Añade su caso a `test_regressions.py`.
- ¿Añades una defensa? Añade a `test_security.py` la sonda que intenta
  saltársela.

## Estilo

- **Comentarios en español**, como el resto del código.
- Los comentarios explican **por qué**, no qué. Si describe lo que hace la línea
  de al lado, sobra. Si explica una restricción no obvia —una condición de
  carrera, un formato heredado, un fallo que ya ocurrió—, es justo lo que hace
  falta.
- SQL siempre con parámetros enlazados.
- Todo lo que va a HTML pasa por `escapeHtml`.

## Pull requests

- Un PR, un tema.
- Explica el **porqué** en la descripción: el qué se ve en el diff.
- Si cambias comportamiento visible, actualiza `CHANGELOG.md`.
- Si tomas una decisión de arquitectura, añade su ADR a
  [docs/decisiones.md](docs/decisiones.md).

## Vulnerabilidades

No abras una incidencia pública. Sigue [SECURITY.md](SECURITY.md).
