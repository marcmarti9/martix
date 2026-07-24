<h1 align="center">Martix</h1>

<p align="center"><strong>Organizador de archivos en tiempo real, privado y 100% local.</strong></p>

<p align="center">
  Martix vive en segundo plano, vigila tus Descargas y archiva cada documento en
  cuanto llega — con reglas visuales, lectura del contenido, OCR local o una IA
  que corre en tu propio equipo. Nada sale de tu ordenador. Nada se borra sin
  poder recuperarlo.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python&logoColor=white" alt="Python 3.10+" />
  <img src="https://img.shields.io/badge/Flask-3.0%2B-black?style=flat-square&logo=flask&logoColor=white" alt="Flask 3" />
  <img src="https://img.shields.io/badge/Linux%20%7C%20macOS%20%7C%20Windows-lightgrey?style=flat-square" alt="Plataformas" />
  <img src="https://img.shields.io/badge/Licencia-MIT-green?style=flat-square" alt="Licencia MIT" />
  <img src="https://img.shields.io/badge/telemetr%C3%ADa-cero-success?style=flat-square" alt="Sin telemetría" />
</p>

---

## Por qué

Tu carpeta de Descargas es un vertedero: facturas, capturas, ZIPs, PDFs del
banco, música. Ordenarla a mano cuesta tiempo, y las alternativas en la nube te
piden subir precisamente los documentos que menos te apetece subir.

Martix hace ese trabajo en tu equipo. Sin cuenta, sin servidor, sin telemetría.

**Y con una regla que no se negocia: ningún borrado es definitivo.** Todo lo
que Martix elimina va a la papelera de tu escritorio (o a una cuarentena propia
si no la hay). Un programa con permisos sobre toda tu carpeta personal no puede
permitirse el lujo de equivocarse de forma irreversible.

---

## Qué hace

### Archiva solo, en cuanto llega

Vigila tus Descargas y las carpetas que le indiques. Espera a que la descarga
termine de verdad — comprueba que el archivo deja de crecer y que ningún
programa lo tiene abierto — y lo archiva. También carpetas enteras: un álbum de
fotos descargado se mueve como una unidad.

### Decide con lo que hay dentro, no solo con el nombre

```
1. Tus reglas          →  "PDF que contiene 'factura' → Documentos/Facturas"
2. Tus Temas           →  busca palabras clave en el nombre y en el CONTENIDO
                          de PDF, DOCX y TXT (y en imágenes, con OCR local)
3. Subcategorías       →  capturas de pantalla, currículums, recibos…
4. IA local (opcional) →  Ollama en tu equipo sugiere una carpeta
5. Categoría base      →  por extensión, como último recurso
```

### Reglas que se combinan de verdad

Varias reglas por extensión, con condiciones en AND sobre nombre, tamaño,
antigüedad, contenido y metadatos EXIF/ID3. El orden lo decides tú arrastrando
en la lista: gana la primera que coincide.

```
.pdf  +  contenido contiene "factura"     →  Documentos/Facturas
.pdf  +  contenido contiene "contrato"    →  Documentos/Contratos
.jpg  +  cámara es "NIKON Z6"             →  Fotos/Réflex/{EXIF_DATE}
 *    +  antigüedad > 365 días            →  Archivo/{FILE_YYYY}
```

### Y además

- **Renombrado con plantillas** — `{YYYY}`, `{Topic}`, `{ARTIST}`, `{EXIF_DATE}`,
  `{OriginalName}`…
- **Analizador de espacio en disco** — árbol con porcentajes, desglose por
  extensión y treemap interactivo en Canvas.
- **Detector de duplicados** — dos fases (fast-hash de 64 KB → SHA256), para no
  releer gigabytes.
- **Extracción segura de comprimidos** — con protección anti Zip-Slip y contra
  bombas de compresión. El `.zip` original se conserva.
- **Limpieza por antigüedad** programable, siempre a la papelera.
- **Simulación** — mira qué haría antes de dejarle hacerlo.
- **Deshacer** desde el historial.
- **Aprende de tus correcciones** — si mueves un archivo a mano, te propone la
  regla.
- Interfaz bilingüe ES/EN, tema claro y oscuro.

---

## Instalación

### Un comando (Linux)

```bash
git clone https://github.com/marcmarti9/martix.git
cd martix
./install.sh
```

Instala dependencias, registra Martix en el menú de aplicaciones, lo arranca al
iniciar sesión, activa el servicio en segundo plano e instala el comando
`martix`. Para revertirlo: `./uninstall.sh`.

### A mano (cualquier sistema)

```bash
git clone https://github.com/marcmarti9/martix.git
cd martix/backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Abre <http://127.0.0.1:5000>. Para una ventana de escritorio sin navegador:
`python desktop.py`.

### Opcionales

| Para… | Instala |
|---|---|
| Leer texto dentro de imágenes | Tesseract (`sudo apt install tesseract-ocr`) |
| Clasificación con IA local | [Ollama](https://ollama.com) + `MARTIX_LLM=1` |
| Ventana de escritorio nativa | `pip install -r requirements-desktop.txt` |

---

## Privacidad

Esto no es un eslogan, es una restricción del código:

- **Una sola petición saliente posible** en todo el proyecto: al LLM local. Se
  valida en cada llamada que el destino sea una IP de loopback. Si apuntas
  `MARTIX_LLM_URL` a un servidor remoto, Martix se niega a enviar nada y lo
  registra en el log.
- **El servidor escucha solo en `127.0.0.1`.** Si cambias `HOST`, se niega a
  arrancar sin un token de acceso.
- **Cero telemetría, cero analítica, cero cuentas.** No hay a dónde enviarlo.
- **La interfaz no carga nada de internet.** Sin CDNs, sin fuentes remotas: lo
  impide su propia Content-Security-Policy.

Los detalles, incluidos los riesgos que se aceptan a conciencia, están en
[docs/seguridad.md](docs/seguridad.md).

---

## Documentación

| | |
|---|---|
| [Arquitectura](docs/arquitectura.md) | Cómo funciona por dentro, módulo a módulo |
| [Seguridad](docs/seguridad.md) | Modelo de amenazas y defensas |
| [Configuración](docs/configuracion.md) | Variables de entorno, categorías, ajustes |
| [API REST](docs/api.md) | Referencia completa de endpoints |
| [Desarrollo](docs/desarrollo.md) | Puesta en marcha, tests, convenciones |
| [Decisiones (ADR)](docs/decisiones.md) | Por qué el proyecto es como es |
| [Auditoría 2026-07](docs/auditoria-2026-07.md) | 16 bugs y 2 vulnerabilidades, y cómo se cerraron |
| [Hoja de ruta](docs/hoja-de-ruta.md) | Estado y backlog |

---

## Tests

```bash
cd backend
.venv/bin/python tests/test_all.py           # integración
.venv/bin/python tests/test_regressions.py   # un caso por bug corregido
.venv/bin/python tests/test_security.py      # ataques reales contra la app
```

Las suites de seguridad y regresión **no comprueban que exista una mitigación:
ejecutan el ataque**. Levantan un servidor HTTP para probar el SSRF, crean
enlaces simbólicos para intentar escapar de la carpeta personal y ejecutan el
escapado real del frontend. Si alguien debilita una defensa, salen en rojo.

Todas usan un HOME y una base de datos temporales, así que no tocan tus
archivos.

---

## Estado

Funcional y en uso diario. La auditoría de julio de 2026 encontró y cerró 16
bugs y 2 vulnerabilidades explotables; el detalle está en
[docs/auditoria-2026-07.md](docs/auditoria-2026-07.md).

Es un proyecto personal mantenido en abierto: úsalo, pero haz copia de seguridad
de lo que te importe antes de soltarlo sobre carpetas críticas, y prueba tus
reglas con **Simular** primero.

---

## Contribuir

Las incidencias y los PRs son bienvenidos — lee [CONTRIBUTING.md](CONTRIBUTING.md)
y [docs/desarrollo.md](docs/desarrollo.md).

¿Has encontrado un fallo de seguridad? No abras una incidencia pública: sigue
[SECURITY.md](SECURITY.md).

## Licencia

[MIT](LICENSE). Creado por Marc Martí Torralba.
