# Configuración

## Variables de entorno (`backend/.env`)

Copia `backend/.env.example` a `backend/.env`. Todas son opcionales.

| Variable | Por defecto | Qué hace |
|---|---|---|
| `HOST` | `127.0.0.1` | Interfaz de escucha. **Cambiarlo exige `MARTIX_TOKEN`** |
| `PORT` | `5000` | Puerto |
| `DOWNLOADS_DIR` | `~/Downloads` | Carpeta vigilada principal |
| `MARTIX_TOKEN` | *(vacío)* | Token de la API. Obligatorio si `HOST` no es local |
| `MARTIX_DATA_DIR` | según sistema | Carpeta de datos (papelera propia) |
| `MARTIX_TRASH_RETENTION_DAYS` | `30` | Días que se conservan los archivos en la cuarentena |
| `MARTIX_LLM` | `0` | Activa la clasificación con LLM local |
| `MARTIX_LLM_URL` | `http://127.0.0.1:11434` | Ollama. **Debe ser loopback** |
| `MARTIX_LLM_MODEL` | `llama3.2` | Modelo |

> Los nombres antiguos `SORTIX_*` siguen funcionando por compatibilidad.

### Sobre `HOST`

El valor por defecto es la defensa más eficaz del proyecto: nadie fuera de tu
equipo puede hablar con Martix. Si lo cambias, `main.py` se **niega a arrancar**
sin un `MARTIX_TOKEN`. Genera uno así:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Carpeta de datos

Aquí vive la papelera propia (cuarentena) cuando `send2trash` no está instalado:

| Sistema | Ruta |
|---|---|
| Linux | `$XDG_DATA_HOME/martix` o `~/.local/share/martix` |
| macOS | `~/Library/Application Support/Martix` |
| Windows | `%LOCALAPPDATA%\Martix` |

---

## Categorías (`backend/config/categories.json`)

Define las categorías base, sus extensiones, su carpeta destino y las
subcategorías por patrón de nombre.

```jsonc
{
  "categories": {
    "documents": {
      "label": "Documentos",
      "icon": "document",
      "folder": "Documents/Unclassified",   // relativa a tu carpeta personal
      "extensions": ["pdf", "docx", "txt", "odt"],
      "subcategories": [
        {
          "label": "Facturas y recibos",
          "folder": "Documents/Invoices and receipts",
          "patterns": ["factura", "recibo", "invoice", "receipt"]
        }
      ]
    }
  },
  "topic_matching": {
    "content_extensions": ["pdf", "docx", "txt"]
  }
}
```

Los patrones se comparan sobre el nombre **normalizado** (minúsculas, sin
tildes, con `_ - .` convertidos en espacios), así que `banco_extracto3` casa con
`banco`.

El archivo se lee **al importar**: hay que reiniciar Martix tras editarlo.

---

## Ajustes desde la interfaz

Se guardan en la tabla `settings` y se cambian desde el panel de ajustes o por
API (`POST /api/settings`).

| Ajuste | Por defecto | Qué hace |
|---|---|---|
| `duplicate_action` | `suffix` | Si el destino ya tiene un archivo idéntico: `suffix` añade `(1)`, `skip` no mueve, `delete_source` manda el origen a la papelera |
| `unpack_archives` | `true` | Extrae `.zip` / `.tar` automáticamente. El comprimido **no se borra** |
| `watch_recursive` | `false` | Vigila también las subcarpetas |
| `onboarded` | `false` | Si ya se completó el asistente inicial |

### Sobre `watch_recursive`

Apagado, un archivo creado en `~/Descargas/album/foto.jpg` no dispara evento: se
recoge cuando la carpeta `album` se organiza entera. Encendido, cada archivo
interno se archiva por separado, lo que **deshace la estructura** de las
carpetas descargadas. Por eso es una decisión explícita del usuario.

---

## Reglas de mantenimiento

Borran por antigüedad, por carpeta, de forma recursiva. Los archivos van a la
**papelera**, nunca se destruyen.

Se saltan siempre: archivos y carpetas ocultos (los *dotfiles* son
configuración, no basura), rutas protegidas y enlaces simbólicos. Las carpetas
que quedan vacías se eliminan.

> Simula antes de activarlas. Una regla sobre la carpeta equivocada afecta a
> todo su árbol. Martix rechaza las rutas protegidas, pero no puede saber qué
> documentos te importan.

---

## Dependencias opcionales

Todo funciona sin ellas; cada una añade una capacidad:

| Paquete | Qué aporta | Si falta |
|---|---|---|
| `Send2Trash` | Papelera nativa del escritorio | Cuarentena propia de Martix |
| `defusedxml` | Parseo de XML reforzado | Parser estándar con rechazo explícito de DTD |
| **Tesseract** (binario) | OCR de imágenes | Las imágenes no se clasifican por contenido |
| **Ollama** (servicio) | Clasificación con IA local | Se usa la cascada normal |

Tesseract se instala con el gestor de paquetes del sistema:

```bash
sudo dnf install tesseract          # Fedora
sudo apt install tesseract-ocr      # Debian/Ubuntu
brew install tesseract              # macOS
```
