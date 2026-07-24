# Modelo de seguridad de Martix

Martix tiene permisos de lectura y escritura sobre toda tu carpeta personal y
procesa archivos que vienen de internet. Este documento explica de qué se
defiende, cómo, y qué riesgos quedan aceptados a conciencia.

> Para reportar una vulnerabilidad, consulta [SECURITY.md](../SECURITY.md).

---

## 1. Qué estamos protegiendo

| Activo | Por qué importa |
|---|---|
| Documentos personales | Martix está pensado para declaraciones, contratos, extractos bancarios |
| Integridad del sistema de archivos | Puede mover y borrar; un fallo puede perder datos |
| Confidencialidad frente a la red | La promesa del proyecto es que nada sale del equipo |
| Credenciales del usuario | `~/.ssh`, `~/.aws`, `~/.gnupg` están dentro de su alcance teórico |

## 2. De quién nos defendemos

1. **El archivo hostil.** Lo más probable. Descargas un `.zip`, un `.pdf` o una
   imagen preparados para explotar al que los procese. Martix los abre
   automáticamente, sin que nadie haga clic.
2. **La web abierta en otra pestaña.** Intenta hablar con `127.0.0.1:5000`
   mediante CSRF o DNS rebinding.
3. **Otro proceso del equipo.** En un equipo compartido, otra sesión o una
   aplicación cualquiera puede alcanzar la API local.
4. **La configuración equivocada.** Una regla de mantenimiento apuntando donde
   no debe, un `.env` copiado de un tutorial. No es un atacante, pero el daño
   es idéntico.

**Fuera de alcance:** un atacante que ya ejecuta código como tu usuario. En ese
punto tiene tus archivos directamente y Martix es irrelevante.

---

## 3. Defensas por vector

### 3.1 Rutas (path traversal)

Toda ruta que llega de la interfaz pasa por `browser.resolve_safe_path()`, que
**resuelve los enlaces simbólicos antes** de comprobar la contención. Un enlace
dentro de la carpeta personal apuntando a `/etc` se rechaza porque lo que se
compara es el destino real.

Los destinos de reglas pasan además por `security.clean_destination()`, que
rechaza rutas absolutas, unidades de Windows (`C:`), `..`, nombres reservados
(`CON`, `LPT1`), segmentos con puntos o espacios finales y nombres de más de
255 caracteres.

Los enlaces simbólicos se excluyen del organizado, del barrido, del
mantenimiento y de la deduplicación.

### 3.2 Archivos comprimidos

| Ataque | Defensa |
|---|---|
| Zip-Slip (`../../.bashrc`) | Se valida cada entrada contra el directorio de extracción |
| Rutas absolutas | Se rechazan explícitamente (POSIX y Windows) |
| Enlaces que escapan | Se valida el *destino* del enlace, no solo su nombre (CVE-2007-4559) |
| Nodos de dispositivo / FIFO | Rechazados |
| Bomba de compresión | Topes de tamaño total (4 GB), ratio (×200), entradas (20.000) y espacio libre |
| Permisos peligrosos | `extractall(filter="data")` en Python 3.12+ |

### 3.3 Contenido de documentos

| Ataque | Defensa |
|---|---|
| XXE / Billion Laughs en `.docx` | `defusedxml` si está instalado; siempre, rechazo explícito de cualquier DTD, con solape entre bloques para que no se parta la cadena |
| Zip bomb dentro del `.docx` | Lector con tope de 8 MB descomprimidos |
| Bomba de descompresión de imagen | `MAX_IMAGE_PIXELS` = 64 Mpx y `DecompressionBombWarning` como excepción |
| PDF hostil que cuelga el parser | Tope de 256 MB antes de abrir el archivo |
| OCR que no termina | `pytesseract` con `timeout=10` |

### 3.4 Interfaz web (XSS)

`escapeHtml()` escapa `& < > " ' \``. **Las comillas son imprescindibles**: la
función se usa dentro de atributos y los nombres de archivo los controla quien
te envía la descarga.

> Esto fue una vulnerabilidad real. La versión anterior usaba
> `textContent → innerHTML`, que no escapa comillas, y se interpolaba en
> `title="..."`. Una carpeta llamada `x" onmouseover="…` escapaba del atributo
> y ejecutaba JavaScript con acceso a toda la API local. Ver
> [auditoria-2026-07.md](auditoria-2026-07.md).

Como segunda línea de defensa hay una **Content-Security-Policy** restrictiva:
`default-src 'self'`, sin destinos de red externos, `frame-ancestors 'none'`,
`object-src 'none'`. La interfaz no usa CDNs, así que no rompe nada.

Los valores numéricos y los colores que vienen del servidor se coaccionan
(`safeNumber`, `safeColor`) antes de entrar en atributos `style`.

### 3.5 API HTTP

| Ataque | Defensa |
|---|---|
| DNS rebinding | La cabecera `Host` debe ser local |
| CSRF | Si el navegador envía `Origin`, debe ser de confianza |
| Acceso desde la red | El servidor solo escucha en `127.0.0.1` por defecto, y **se niega a arrancar** si se expone sin `MARTIX_TOKEN` |
| Comparación de token | `hmac.compare_digest` (tiempo constante) |
| Agotamiento de memoria | `MAX_CONTENT_LENGTH` de 2 MB |
| Clickjacking | `X-Frame-Options: DENY` + `frame-ancestors 'none'` |
| Fuga por caché | `Cache-Control: no-store` en toda la API |

### 3.6 Peticiones salientes (SSRF y privacidad)

Martix hace **exactamente una** petición saliente posible: al LLM local. Se
valida con `security.is_loopback_url()`, que exige:

- esquema `http` o `https`,
- una **IP literal** de loopback (o `localhost`).

Los nombres de dominio se rechazan a propósito: `evil.com` puede resolver hoy a
`127.0.0.1` y mañana a otra cosa (DNS rebinding).

Esto cubre dos cosas a la vez:

1. **Anti-SSRF**: `/api/llm/test` no puede usarse para sondear puertos de
   localhost o de la red local a través de Martix.
2. **Privacidad**: `llm.suggest_subfolder()` envía un fragmento del *contenido*
   del documento. La comprobación se repite en cada llamada, así que un `.env`
   mal copiado no puede exfiltrar un extracto bancario en silencio.

### 3.7 Borrado

Ningún borrado de Martix es definitivo:

- Todo pasa por `trash.move_to_trash()` — papelera nativa o cuarentena propia.
- `security.is_protected_path()` rechaza `~/.ssh`, `~/.gnupg`, `~/.config`, la
  propia base de datos y cualquier `.git` en cualquier nivel.
- Borrar una carpeta con más de 25 archivos exige confirmación explícita.
- El mantenimiento salta los archivos ocultos: los *dotfiles* son configuración,
  no basura caducable.

### 3.8 Ejecución de comandos

Las notificaciones lanzan procesos externos. Nunca se usa `shell=True` y los
datos del usuario van como argumentos separados. En Linux se añade `--` antes
del título y el mensaje: sin él, un archivo llamado `--expire-time=0` se
interpretaba como opción de `notify-send`.

### 3.9 Base de datos

Todas las consultas usan parámetros enlazados. Los únicos f-strings en SQL
componen nombres de columna a partir de una lista blanca cerrada en el código.

---

## 4. Riesgos aceptados

Decisiones conscientes, no descuidos.

### El token se guarda en `localStorage`

**Riesgo:** un XSS podría extraerlo y reutilizarlo.
**Por qué se acepta:** la alternativa (cookie `HttpOnly` + `SameSite=Strict`)
exige un flujo de sesión que complica el arranque sin navegador (app de
escritorio, `curl`). El riesgo está mitigado por la CSP y por el saneado de
salida corregido.
**Si te importa:** el token solo existe cuando expones Martix fuera de
localhost, que no es la configuración recomendada.

### Se aceptan peticiones sin cabecera `Origin`

**Riesgo:** cualquier proceso local puede manejar la API cuando no hay token.
**Por qué se acepta:** es inherente a una API local sin autenticación, y es lo
que permite usar `curl` o la app de escritorio. Los navegadores actuales envían
`Origin` en toda petición cross-origin, así que el CSRF clásico sí está cubierto.
**Mitigación:** en un equipo compartido, define `MARTIX_TOKEN` en
`backend/.env`. Se exige siempre en cuanto la API deja de ser solo local.

### El LLM local ve el contenido de los documentos

Es el propósito de la función y está **apagado por defecto**. Solo se activa
con `MARTIX_LLM=1`, y el destino se valida como loopback en cada llamada.

---

## 5. Verificación

Las defensas no se comprueban leyendo el código: hay una suite que **ejecuta
los ataques** contra la aplicación real.

```bash
cd backend
.venv/bin/python tests/test_security.py    # 12 ataques; sale con código 1 si alguno funciona
.venv/bin/python tests/test_regressions.py # 27 regresiones de la auditoría
.venv/bin/python tests/test_all.py         # suite de integración
```

Si debilitas una defensa, `test_security.py` vuelve a marcar EXPLOTABLE. Está
pensado para ejecutarse en CI en cada push.

---

## 6. Recomendaciones de despliegue

- **No cambies `HOST`.** El valor por defecto `127.0.0.1` es la defensa más
  eficaz que tiene el proyecto.
- Si lo expones en tu LAN, define un `MARTIX_TOKEN` largo y aleatorio. Martix
  no arrancará sin él.
- Instala `send2trash` (está en `requirements.txt`) para que los borrados vayan
  a la papelera de tu escritorio y puedas recuperarlos desde el gestor de
  archivos.
- Repasa tus reglas de mantenimiento antes de activarlas: usa "Simular" primero.
- Mantén `MARTIX_LLM=0` salvo que quieras la clasificación con IA y tengas
  Ollama en local.
