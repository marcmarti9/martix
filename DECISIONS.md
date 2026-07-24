# Martix — Registro de Decisiones de Arquitectura y Producto (ADR)

Este documento registra todas las decisiones de diseño, arquitectura y producto tomadas durante el desarrollo de **Martix**, incluyendo el contexto, la justificación y los cambios realizados.

---

## 📅 Historial de Decisiones

### [2026-07-24] — ADR-001: Sustitución de Sortix por Martix y Desinstalación del Sistema
* **Contexto:** Existía en el sistema del usuario la versión previa (Sortix) ejecutándose al mismo tiempo que la nueva aplicación (Martix).
* **Decisión:** 
  1. Desinstalar completamente Sortix del PC del usuario: detener su proceso en segundo plano, eliminar los lanzadores `~/.config/autostart/sortix.desktop` y `~/.local/share/applications/sortix.desktop`, y deshabilitar su servicio systemd.
  2. Migrar la marca y configuración al nuevo proyecto unificado **Martix**.
* **Consecuencias:** Martix queda como el único organizador inteligente y explorador de archivos oficial en el sistema, evitando conflictos de puertos, duplicidad de consumo de RAM y vigilancias superpuestas.

---

### [2026-07-24] — ADR-002: Visualizador de Espacio de Disco
* **Contexto:** Martix operaba principalmente en segundo plano organizando descargas. Se requería una funcionalidad visual potente para analizar y gestionar el almacenamiento en disco de forma interactiva.
* **Decisión:**
  1. **Motor de Análisis (`backend/app/disk_analyzer.py`):** Algoritmo de escaneo recursivo de alto rendimiento que calcula tamaños acumulados, porcentaje del directorio padre, recuento de carpetas/archivos y clasificación de tipos de archivo por extensiones.
  2. **API REST (`backend/app/server.py`):**
     - `GET /api/disk/drives`: Listado de unidades y carpetas clave.
     - `POST /api/disk/scan`: Escaneo de ruta arbitraria o carpeta predeterminada.
     - `POST /api/disk/delete`: Eliminación segura de archivos/carpetas directamente desde la vista de análisis.
  3. **Interfaz de Usuario del Analizador (`frontend/`):**
     - **Barra de Resumen de Disco:** Espacio total, usado (% y barra azul) y libre (% y barra verde), más tiempo de escaneo.
     - **Vista de Árbol (Panel Izquierdo):** Jerarquía de carpetas con expansión/colapso, barras de progreso de % respecto al padre, tamaños formateados (GB/MB), conteos de elementos y filtro de texto.
     - **Desglose por Extensión (Panel Derecho):** Tabla ordenada por ocupación de espacio según tipo de archivo/extensión con barras de color.
     - **Treemap Interactivo (Panel Inferior):** Mapa visual dibujado en Canvas HTML5 con algoritmo de división squarified, rectángulos de tamaño proporcional, información en hover y vinculación directa de selección con la vista de árbol.
* **Consecuencias:** Martix evoluciona de un daemon pasivo a un explorador/analizador de espacio completo, permitiendo a los usuarios identificar y limpiar archivos pesados visualmente.

---

### [2026-07-24] — ADR-003: Instalador y Desinstalador Unificado de 1-Clic
* **Contexto:** Se necesitaba una forma sencilla, estándar y automatizada de instalar Martix en cualquier equipo (escritorio nativo, servicio en segundo plano, comando CLI) o desinstalarlo limpiamente.
* **Decisión:**
  1. Crear scripts raíz `install.sh` / `installer.py` y `uninstall.sh` / `uninstaller.py`.
  2. **Instalador:**
     - Configura el entorno virtual `.venv` e instala dependencias.
     - Registra el acceso directo en el menú de aplicaciones (`~/.local/share/applications/martix.desktop`).
     - Registra el autostart al iniciar sesión (`~/.config/autostart/martix.desktop`).
     - Genera y activa el servicio systemd de usuario (`~/.config/systemd/user/martix.service`).
     - Instala el comando global `martix` en `~/.local/bin/martix`.
  3. **Desinstalador:** Detiene procesos/servicios y elimina de forma limpia todos los archivos de integración creados en el sistema.
* **Consecuencias:** Distribución e integración en el sistema operativo simplificadas y ejecutables con un solo comando.

---

### [2026-07-22] — ADR-000: Base del Sistema Martix y Clasificación Híbrida
* **Contexto:** Diseño inicial de la plataforma de organización 100% local.
* **Decisión:**
  - Cascada de reglas: Reglas por extensión > Reglas Scratch avanzadas (metadatos/condiciones) > Temas por palabra clave/OCR > IA Local opcional con Ollama > Categoría base.
  - Vigilancia en tiempo real multi-carpeta con Watchdog y programador de tareas en segundo plano (TaskScheduler).
  - Deduplicador en 2 pasos (Fast-Hash de 64KB + SHA256).
