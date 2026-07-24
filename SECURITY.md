# Política de seguridad

Martix tiene permisos de lectura y escritura sobre toda la carpeta personal del
usuario y procesa archivos descargados de internet. Los informes de seguridad se
toman en serio.

## Versiones con soporte

| Versión | Soporte |
|---|---|
| `main` | ✅ |
| Anteriores a la auditoría de 2026-07 | ❌ — contienen un XSS explotable con acceso a la API local. Actualiza |

## Cómo reportar una vulnerabilidad

**No abras una incidencia pública.**

Usa el [aviso de seguridad privado de GitHub](https://github.com/marcmarti9/martix/security/advisories/new),
que es el canal preferido.

Incluye, si puedes:

- Qué versión o commit estás probando.
- Los pasos para reproducirlo (una prueba de concepto ayuda muchísimo).
- Qué consigue un atacante: leer archivos, borrarlos, ejecutar código…
- Qué necesita para conseguirlo: ¿basta con que descargues un archivo?
  ¿hace falta que abras una web concreta? ¿acceso local al equipo?

Intentaré responder en unos días. Es un proyecto personal, no hay un equipo
detrás ni programa de recompensas, pero se te acreditará en el aviso y en el
CHANGELOG salvo que prefieras lo contrario.

## Qué cuenta como vulnerabilidad

Sí:

- Escapar de la carpeta personal (path traversal, enlaces simbólicos).
- Ejecutar JavaScript en el origen de Martix (XSS) — la API local no pide
  credenciales, así que equivale a controlar la aplicación.
- Hacer que Martix borre o mueva algo que no debería, o que salte las rutas
  protegidas.
- Conseguir que Martix haga peticiones de red a destinos no locales (SSRF), o
  que el contenido de un documento salga del equipo.
- Colgar o tumbar el proceso con un archivo preparado (zip bomb, PDF hostil,
  bomba de descompresión de imagen).
- Ejecución de código a partir de un archivo descargado.

No, o solo si demuestras un impacto real:

- **Que un proceso local pueda usar la API sin credencial.** Es un riesgo
  conocido y aceptado de una aplicación local; la mitigación es `MARTIX_TOKEN`.
  Está documentado en [docs/seguridad.md](docs/seguridad.md#4-riesgos-aceptados).
- **Que el token se guarde en `localStorage`.** También conocido, aceptado y
  mitigado por la Content-Security-Policy.
- Un atacante que ya ejecuta código como tu usuario. En ese punto ya tiene tus
  archivos y Martix es irrelevante.
- Resultados de escáneres automáticos sin un camino de explotación.

## Cómo se verifica

Cada defensa tiene una prueba que **ejecuta el ataque** contra la aplicación
real, no que comprueba que exista una mitigación:

```bash
cd backend
.venv/bin/python tests/test_security.py    # sale con código 1 si algo es explotable
```

Se ejecuta en CI en cada push. Si envías un arreglo, añade también la sonda que
reproduce el fallo.

El modelo de amenazas completo está en [docs/seguridad.md](docs/seguridad.md).
