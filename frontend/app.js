/* Martix - interfaz tipo explorador de archivos.
   Sidebar con Descargas + categorias + tus Temas; panel principal con el
   contenido real de la carpeta seleccionada; ajustes en un dialog aparte. */

(function initTheme() {
    const theme = localStorage.getItem("martix_theme") || localStorage.getItem("sortix_theme") || "light";
    document.documentElement.classList.toggle("dark", theme === "dark");
})();

const TRANSLATIONS = {
    es: {
        patrol_label: "En vivo",
        patrol_title: "Clasifica Descargas en cuanto terminan",
        organize_btn: "Organizar ahora",
        settings_title: "Ajustes",
        organized_count_prefix: "Archivos organizados",
        empty_state: "Esta carpeta está vacía (o aún no se ha creado).",
        settings_title_modal: "Ajustes de Martix",
        close_title: "Cerrar",
        tab_topics: "Temas",
        tab_rules: "Reglas por extensión",
        topics_hint: "Un Tema es cualquier cosa que quieras agrupar: tu banco, el gimnasio, una app concreta, facturas de un proveedor... Martix mira el nombre del archivo y, si hace falta, su contenido, buscando estas palabras clave.",
        topic_name_label: "Nombre del tema",
        topic_name_placeholder: "ej. Banco, Gimnasio, Netflix",
        topic_dest_label: "Carpeta destino",
        topic_dest_placeholder: "ej. Documents/Banco",
        topic_keywords_label: "Palabras clave (separadas por comas)",
        topic_keywords_placeholder: "ej. banco, extracto, iban",
        add_topic_btn: "Añadir tema",
        rules_hint: "Las reglas por extensión son más simples y siempre ganan a la clasificación automática: todo archivo con esa extensión va directo a la carpeta que indiques.",
        rule_ext_label: "Extensión",
        rule_ext_placeholder: "ej. pdf",
        rule_dest_label: "Carpeta destino",
        rule_dest_placeholder: "ej. Documents/Facturas",
        add_rule_btn: "Añadir regla",
        tab_general: "General",
        general_hint: "Ajustes globales del sistema para gestionar archivos duplicados e integraciones.",
        cleanup_mode_notify: "Avisar y pedir revisión (recomendado)",
        cleanup_mode_direct: "Enviar automáticamente a la papelera",
        cleanup_delete_btn: "Enviar a papelera",
        cleanup_dismiss_btn: "Descartar",
        cleanup_deleted: "Archivo enviado a la papelera.",
        cleanup_dismissed: "Sugerencia descartada.",
        cleanup_empty: "No hay sugerencias pendientes.",
        tab_ai: "IA local",
        files_suffix: "archivos",
        simulate_modal_hint: "Nada se mueve hasta que pulses Organizar ahora.",
        privacy_title: "Solo en este equipo",
        privacy_caption: "Sin nube ni telemetría",
        trash_load_error: "No se pudo cargar la papelera.",
        disk_analyzer_title: "Uso del espacio",
        ai_hint: "Martix detecta Ollama local automáticamente cuando el equipo puede usarlo; tus archivos no salen a la nube.",
        ai_status_enabled: "Ollama activado (modo LLM)",
        ai_status_disabled: "Ollama desactivado (modo heurístico)",
        ai_testing: "Probando...",
        ai_test_ok: "Conexión correcta y modelo disponible",
        ai_test_ok_no_model: "Conectado, pero el modelo indicado no está descargado en Ollama",
        ai_test_fail: "No se pudo conectar con Ollama",
        duplicate_action_label: "Acción al encontrar archivos idénticos en destino",
        dup_opt_suffix: "Añadir sufijo numérico, ej. archivo (1).pdf",
        dup_opt_skip: "Omitir movimiento (dejar en Descargas)",
        dup_opt_delete_source: "Eliminar archivo original (ya guardado)",
        save_settings_btn: "Guardar ajustes",
        topic_rename_label: "Patrón de renombrado (opcional)",
        topic_rename_placeholder: "ej. {YYYY}-{MM} - {OriginalName}.{ext}",
        rule_rename_label: "Patrón de renombrado (opcional)",
        rule_rename_placeholder: "ej. {Category}/{OriginalName}.{ext}",
        rule_conditions_label: "Condiciones de activación (opcional)",
        btn_add_condition: "+ Añadir condición",
        cond_field_name: "Nombre de archivo",
        cond_field_stem: "Nombre (sin extensión)",
        cond_field_extension: "Extensión",
        cond_field_size_kb: "Tamaño (KB)",
        cond_field_age_days: "Antigüedad (días)",
        cond_field_content: "Contenido de texto",
        cond_field_artist: "Artista",
        cond_field_album: "Álbum",
        cond_field_title: "Título",
        cond_field_year: "Año",
        cond_field_camera: "Cámara",
        cond_field_exif_date: "Fecha EXIF",
        learn_correction_btn: "Aprender de la corrección",
        learn_correction_title: "Aprender de la corrección / Crear regla",
        status_rule_suggested: "Regla sugerida cargada en la pestaña de reglas.",
        status_learn_error: "No se pudo generar la regla sugerida.",
        cond_op_contains: "Contiene",
        cond_op_not_contains: "No contiene",
        cond_op_equals: "Es igual a",
        cond_op_starts_with: "Empieza con",
        cond_op_ends_with: "Termina con",
        cond_op_gt: "Mayor que",
        cond_op_lt: "Menor que",
        cond_op_gte: "Mayor o igual que",
        cond_op_lte: "Menor o igual que",
        rule_order_hint: "Orden de evaluación: gana la primera regla que coincide",
        rule_move_up: "Subir (evaluar antes)",
        rule_move_down: "Bajar (evaluar después)",
        disk_scan_truncated: "Escaneo parcial: la carpeta es demasiado grande y se alcanzó el límite de tiempo. Los totales mostrados son incompletos.",
        confirm_delete_folder: "Vas a enviar a la papelera una carpeta con {n} archivos. ¿Continuar?",
        status_moved_to_trash: "Enviado a la papelera",
        cond_value_placeholder: "Valor",
        status_settings_saved: "Ajustes del sistema guardados.",
        status_settings_save_error: "No se pudo guardar la configuración.",
        
        home: "Inicio",
        downloads: "Descargas",
        images: "Imágenes",
        videos: "Videos",
        music: "Música",
        compressed: "Comprimidos",
        installers: "Instaladores",
        documents: "Documentos",
        other: "Otros",
        code: "Desarrollo",
        books: "Libros",
        fonts: "Fuentes",
        data: "Datos",
        
        status_conn_error: "No se pudo contactar con Martix.",
        status_patrol_active: "Clasificación en vivo: Descargas.",
        status_patrol_inactive: "Clasificación en vivo en pausa.",
        status_patrol_error: "No se pudo cambiar la clasificación en vivo.",
        status_organizing: "Organizando...",
        status_organized_done: "Listo: {moved} archivo(s) organizado(s); {review} para revisar.",
        status_organize_error: "Fallo al organizar la carpeta de descargas.",
        status_folder_error: "No se pudo abrir esa carpeta.",
        
        topics_empty: "Aún no tienes ningún tema. Añade el primero abajo.",
        rules_empty: "No tienes reglas personalizadas todavía.",
        delete_topic_title: "Eliminar tema",
        delete_rule_title: "Eliminar regla",
        status_topic_saved: "Tema guardado.",
        status_topic_save_error: "No se pudo guardar el tema.",
        status_rule_saved: "Regla guardada.",
        status_rule_save_error: "No se pudo guardar la regla.",
        theme_title: "Cambiar tema",
        
        welcome_message: "Bienvenido: define tus primeros Temas (banco, gimnasio, apps...) y listo, Martix se encarga solo a partir de ahora.",
        
        tab_history: "Historial",
        history_title: "Historial de movimientos",
        history_hint: "Últimos movimientos de Martix. Si un archivo acabó donde no debía, pulsa «Deshacer» y volverá a su carpeta de origen.",
        history_empty: "Martix aún no ha movido ningún archivo.",
        history_load_error: "No se pudo cargar el historial.",
        undo_title: "Deshacer: devolver el archivo a su carpeta de origen",
        status_undone_done: '"{filename}" devuelto a su carpeta de origen.',
        status_undo_error: "No se pudo deshacer el movimiento.",
        history_undone_label: "deshecho",
        select_all_btn: "Seleccionar todo",
        undo_selected_btn: "Deshacer seleccionados",
        status_batch_undo_done: "Deshechos {count} movimiento(s) correctamente.",

        tab_trash: "Papelera",
        trash_hint: "Elementos en cuarentena local de Martix. Puedes recuperarlos o eliminarlos definitivamente.",
        trash_empty: "La papelera de cuarentena está vacía.",
        trash_native_active: "Papelera nativa del sistema",
        trash_quarantine_active: "Cuarentena local de Martix",
        purge_all_trash_btn: "Vaciar papelera",
        purge_item_btn: "Eliminar definitivamente",
        restore_item_btn: "Restaurar",
        status_trash_restored: '"{filename}" restaurado correctamente.',
        status_trash_purged: "Papelera vaciada ({count} elemento(s) eliminados).",
        status_trash_item_purged: '"{filename}" eliminado definitivamente.',
        confirm_purge_all_trash: "¿Seguro que deseas eliminar todos los elementos de la cuarentena definitivamente?",
        
        export_rules_btn: "Exportar reglas (JSON)",
        import_rules_btn: "Importar reglas (JSON)",
        duplicates_folder_label: "Carpetas a analizar (opcional, separadas por comas):",
        duplicates_folder_placeholder: "ej. Documents, Downloads",
        status_rules_exported: "Reglas exportadas correctamente.",
        status_rules_imported: "Reglas importadas correctamente.",
        status_export_error: "Error al exportar las reglas.",
        status_import_error: "Error al importar las reglas.",
        
        tab_duplicates: "Deduplicar",
        duplicates_hint: "Escanea y elimina archivos duplicados para liberar espacio.",
        scan_duplicates_btn: "Buscar duplicados",
        auto_select_btn: "Seleccionar todos menos uno",
        clean_selected_btn: "Limpiar seleccionados",
        scanning_message: "Buscando archivos duplicados...",
        duplicates_empty: "No se han encontrado archivos duplicados.",
        status_cleaning_done: "Limpieza completada: se eliminaron {count} archivo(s).",
        status_cleaning_error: "No se pudieron eliminar algunos archivos.",
        status_scanning_error: "No se pudieron buscar archivos duplicados.",
        
        tab_maintenance: "Mantenimiento",
        maintenance_hint: "Configura reglas para eliminar automáticamente archivos de carpetas específicas después de cierta cantidad de días.",
        maintenance_folder_label: "Carpeta",
        maintenance_folder_placeholder: "ej. Downloads/Junk",
        maintenance_age_label: "Edad máxima (días)",
        maintenance_age_placeholder: "ej. 30",
        add_maintenance_rule_btn: "Añadir regla de mantenimiento",
        run_maintenance_btn: "Ejecutar mantenimiento ahora",
        maintenance_empty: "No hay reglas de mantenimiento configuradas.",
        delete_maintenance_rule_title: "Eliminar regla de mantenimiento",
        status_maintenance_saved: "Regla de mantenimiento guardada.",
        status_maintenance_save_error: "No se pudo guardar la regla de mantenimiento.",
        status_maintenance_deleted: "Regla de mantenimiento eliminada.",
        status_maintenance_delete_error: "No se pudo eliminar la regla de mantenimiento.",
        status_maintenance_running: "Ejecutando mantenimiento...",
        status_maintenance_run_done: "Mantenimiento completado: {count} archivo(s) limpiado(s).",
        status_maintenance_run_error: "No se pudo ejecutar el mantenimiento.",

        // Simulate
        simulate_title: "Simular organización",
        status_simulating: "Simulando...",
        simulate_modal_title: "Resultado de la simulación",
        organize_report_title: "Resultado de la organización",
        simulate_no_changes: "No se moverían archivos.",
        simulate_move_label: "se movería a",
        simulate_close_btn: "Cerrar",
        status_simulate_error: "No se pudo ejecutar la simulación.",

        // Watched folders
        tab_watched: "Carpetas vigiladas",
        watched_hint: "Añade carpetas adicionales que Martix organizará al pulsar «Organizar ahora».",
        watched_folder_label: "Ruta de la carpeta",
        watched_folder_placeholder: "ej. /home/user/Desktop",
        add_watched_btn: "Añadir carpeta",
        watched_empty: "No hay carpetas vigiladas configuradas.",
        delete_watched_title: "Eliminar carpeta vigilada",
        status_watched_saved: "Carpeta vigilada añadida.",
        status_watched_save_error: "No se pudo añadir la carpeta.",
        status_watched_deleted: "Carpeta vigilada eliminada.",
        status_watched_delete_error: "No se pudo eliminar la carpeta vigilada.",

        // Statistics
        tab_stats: "Estadísticas",
        stats_hint: "Resumen de la actividad de Martix.",
        stats_total_label: "archivos organizados en total",
        stats_top_categories: "Categorías principales",
        stats_activity_title: "Actividad (últimos 30 días)",
        stats_no_data: "Aún no hay datos suficientes.",
        stats_load_error: "No se pudieron cargar las estadísticas.",

        // Toolbar & Header
        patrol_on: "En vivo",
        patrol_off: "En pausa",
        organize_title: "Organizar archivos de descargas y carpetas vigiladas inmediatamente",
        simulate_btn: "Simular (Prueba)",
        simulate_title: "Prueba tus reglas sin mover ningún archivo real",
        help_btn: "Ayuda",
        help_title: "Ver tutorial y guía paso a paso",
        settings_btn: "Ajustes y Reglas",
        settings_title: "Configurar reglas, temas, deduplicador y mantenimiento",
        sidebar_folders_title: "LUGARES",
        sidebar_subtitle: "Accesos rápidos",
        content_eyebrow: "UBICACIÓN",
        content_description: "Tus carpetas importantes, en un solo lugar.",
        folder_view_description: "Contenido de esta carpeta.",
        open_folder: "Abrir carpeta",
        folder_label: "Carpeta",
        empty_state_title: "Carpeta sin archivos",
        theme_dark: "Oscuro",
        theme_light: "Claro",

        // Onboarding Welcome Modal
        step_prefix: "Paso {step} de 4",
        welcome_title: "¡Bienvenido a Martix!",
        welcome_subtitle: "Organizador de archivos local, privado y visual",
        slide1_title: "100% Local y Privado",
        slide1_desc: "Tus documentos, extractos bancarios y fotos jamás salen de tu ordenador. Martix funciona sin nube, sin telemetría y sin enviar datos a internet.",
        slide2_title: "Auto-Organización en Tiempo Real",
        slide2_desc: "Martix vigila tu carpeta de Descargas y carpetas vigiladas. Cuando termina una descarga (.crdownload / .part), la clasifica y la traslada a su sitio en segundos.",
        slide3_title: "Reglas Scratch, OCR e IA Local",
        slide3_desc: "Define reglas por extensión, nombre, tamaño o días. Martix lee texto dentro de PDFs/imágenes (OCR) y metadatos EXIF/ID3. ¡Usa Ollama local si quieres!",
        slide4_title: "Tú decides sobre la limpieza",
        slide4_desc: "Los instaladores se sugieren para revisión. El envío automático a la papelera solo ocurre si lo activas tú.",
        btn_prev: "Anterior",
        btn_next: "Siguiente",
        btn_start: "Empezar",

        // Disk Space Analyzer
        disk_analyzer_btn: "Analizador de Espacio",
        disk_analyzer_btn_title: "Analizador interactivo de tamaño de archivos y carpetas",
        disk_analyzer_modal_title: "Analizador de Espacio de Disco",
        disk_analyzer_modal_subtitle: "Visualizador interactivo de carpetas, archivos, extensiones y mapa de bloques",
        disk_analyzer_input_ph: "Ruta a escanear (ej. Downloads, ~)",
        disk_analyzer_scan_btn: "Escanear",
        disk_analyzer_status_label: "Estado:",
        disk_analyzer_ready_status: "Listo para escanear",
        disk_analyzer_scanning_status: "Escaneando disco...",
        disk_analyzer_scanning_tree: "Escaneando directorio de archivos... Por favor espera.",
        disk_analyzer_scanning_ext: "Calculando desglose de extensiones...",
        disk_analyzer_scan_done: "Escaneo completado en {s} s",
        disk_analyzer_scan_error: "Error al escanear",
        disk_analyzer_total_label: "Espacio Total:",
        disk_analyzer_used_label: "Espacio Usado:",
        disk_analyzer_free_label: "Espacio Libre:",
        disk_analyzer_tree_title: "Vista de Árbol (Carpetas y Archivos)",
        disk_analyzer_filter_ph: "Filtrar por nombre...",
        disk_analyzer_th_name: "Carpeta / Archivo",
        disk_analyzer_th_pct: "% del Padre",
        disk_analyzer_th_size: "Tamaño",
        disk_analyzer_th_items: "Elementos",
        disk_analyzer_th_files: "Archivos",
        disk_analyzer_th_folders: "Carpetas",
        disk_analyzer_th_modified: "Modificado",
        disk_analyzer_tree_empty: "Haz clic en \"Escanear\" para analizar la carpeta.",
        disk_analyzer_ext_title: "Desglose por Extensión",
        disk_analyzer_th_extension: "Extensión",
        disk_analyzer_th_filetype: "Tipo de Archivo",
        disk_analyzer_th_pct_total: "% del Total",
        disk_analyzer_ext_empty: "Sin datos.",
        disk_analyzer_treemap_title: "Mapa Treemap Visual (Bloques por Tamaño)",
        disk_analyzer_hover_hint: "Pasa el cursor sobre un bloque o haz clic para seleccionar",
        disk_analyzer_no_selection: "Ningún elemento seleccionado",
        disk_analyzer_selected: "Seleccionado",
        disk_analyzer_delete_btn: "Eliminar Elemento",
        disk_analyzer_confirm_delete: "¿Enviar este elemento a la papelera?\n\n{path}",
        disk_analyzer_close_btn: "Cerrar",

        // Updates
        update_available_btn: "Actualización disponible",
        update_available_title: "Existe una nueva versión de Martix en el repositorio. Haz clic para actualizar.",
        update_confirm_dialog: "¿Deseas actualizar Martix a la última versión disponible desde GitHub?",
        status_updating: "Actualizando Martix en segundo plano..."
    },
    en: {
        patrol_label: "Live sort",
        patrol_title: "File new downloads as they finish",
        organize_btn: "Organize now",
        settings_title: "Settings & Rules",
        organized_count_prefix: "Organized files",
        empty_state: "This folder is empty (or has not been created yet).",
        settings_title_modal: "Martix Settings",
        close_title: "Close",
        tab_topics: "Topics",
        tab_rules: "Rules by Extension",

        // Toolbar & Header
        patrol_on: "Live",
        patrol_off: "Paused",
        organize_title: "Organize downloads and watched folders immediately",
        simulate_btn: "Simulate (Test)",
        simulate_title: "Test your rules without moving any real files",
        help_btn: "Help",
        help_title: "View step-by-step tutorial and guide",
        settings_btn: "Settings & Rules",
        settings_title: "Configure rules, topics, deduplication and maintenance",
        sidebar_folders_title: "PLACES",
        sidebar_subtitle: "Quick access",
        content_eyebrow: "LOCATION",
        content_description: "Your important folders, in one place.",
        folder_view_description: "Contents of this folder.",
        open_folder: "Open folder",
        folder_label: "Folder",
        empty_state_title: "Empty Folder",
        theme_dark: "Dark",
        theme_light: "Light",

        // Onboarding Welcome Modal
        step_prefix: "Step {step} of 4",
        welcome_title: "Welcome to Martix!",
        welcome_sub: "Your intelligent, 100% local and private file organizer.",
        slide1_title: "100% Local & Private",
        slide1_desc: "Your documents, invoices, and photos never leave your machine. No cloud, no tracking, and no internet data calls.",
        slide2_title: "Live sorting",
        slide2_desc: "Martix watches your Downloads and custom folders. Once a download finishes (.crdownload / .part), it automatically files it in its target destination.",
        slide3_title: "Scratch Rules, OCR & Metadata",
        slide3_desc: "Define visual rules combining extension, keywords, age (days), image OCR scanning, and EXIF/ID3 metadata tags. Connect local Ollama AI whenever needed.",
        slide4_title: "You decide what gets cleaned",
        slide4_desc: "Installers are suggested for review. Automatic trash only runs if you turn it on.",
        btn_prev: "Previous",
        btn_next: "Next",
        btn_start: "Get started",

        // Disk Space Analyzer
        disk_analyzer_btn: "Disk Space Analyzer",
        disk_analyzer_btn_title: "Interactive file and folder size analyzer",
        disk_analyzer_modal_title: "Disk Space Analyzer",
        disk_analyzer_modal_subtitle: "Interactive visualizer for folders, files, extensions, and treemaps",
        disk_analyzer_input_ph: "Path to scan (e.g. Downloads, ~)",
        disk_analyzer_scan_btn: "Scan",
        disk_analyzer_status_label: "Status:",
        disk_analyzer_ready_status: "Ready to scan",
        disk_analyzer_scanning_status: "Scanning disk...",
        disk_analyzer_scanning_tree: "Scanning file directory... Please wait.",
        disk_analyzer_scanning_ext: "Calculating extension breakdown...",
        disk_analyzer_scan_done: "Scan completed in {s} s",
        disk_analyzer_scan_error: "Scan failed",
        disk_analyzer_total_label: "Total Space:",
        disk_analyzer_used_label: "Used Space:",
        disk_analyzer_free_label: "Free Space:",
        disk_analyzer_tree_title: "Tree View (Folders & Files)",
        disk_analyzer_filter_ph: "Filter by name...",
        disk_analyzer_th_name: "Folder / File",
        disk_analyzer_th_pct: "% of Parent",
        disk_analyzer_th_size: "Size",
        disk_analyzer_th_items: "Items",
        disk_analyzer_th_files: "Files",
        disk_analyzer_th_folders: "Folders",
        disk_analyzer_th_modified: "Modified",
        disk_analyzer_tree_empty: "Click \"Scan\" to analyze the folder.",
        disk_analyzer_ext_title: "Extension Breakdown",
        disk_analyzer_th_extension: "Extension",
        disk_analyzer_th_filetype: "File Type",
        disk_analyzer_th_pct_total: "% of Total",
        disk_analyzer_ext_empty: "No data.",
        disk_analyzer_treemap_title: "Visual Treemap (Blocks by Size)",
        disk_analyzer_hover_hint: "Hover over a block or click to select",
        disk_analyzer_no_selection: "No item selected",
        disk_analyzer_selected: "Selected",
        disk_analyzer_delete_btn: "Delete Item",
        disk_analyzer_confirm_delete: "Send this item to the trash?\n\n{path}",
        disk_analyzer_close_btn: "Close",

        // Updates
        update_available_btn: "Update available",
        update_available_title: "A new version of Martix is available. Click to update.",
        update_confirm_dialog: "Do you want to update Martix to the latest version from GitHub?",
        status_updating: "Updating Martix in the background...",

        topics_hint: "A Topic is anything you want to group: your bank, the gym, a specific app, invoices from a supplier... Martix looks at the filename and, if needed, its content, searching for these keywords.",
        topic_name_label: "Topic name",
        topic_name_placeholder: "e.g. Bank, Gym, Netflix",
        topic_dest_label: "Destination folder",
        topic_dest_placeholder: "e.g. Documents/Bank",
        topic_keywords_label: "Keywords (comma-separated)",
        topic_keywords_placeholder: "e.g. bank, statement, iban",
        add_topic_btn: "Add topic",
        rules_hint: "Rules by extension are simpler and always override automatic classification: any file with that extension goes directly to the folder you specify.",
        rule_ext_label: "Extension",
        rule_ext_placeholder: "e.g. pdf",
        rule_dest_label: "Destination folder",
        rule_dest_placeholder: "e.g. Documents/Invoices",
        add_rule_btn: "Add rule",
        tab_general: "General",
        general_hint: "Global system settings to manage duplicate files and integrations.",
        cleanup_mode_notify: "Notify and ask for review (recommended)",
        cleanup_mode_direct: "Automatically send to the trash",
        cleanup_delete_btn: "Send to trash",
        cleanup_dismiss_btn: "Dismiss",
        cleanup_deleted: "File sent to the trash.",
        cleanup_dismissed: "Suggestion dismissed.",
        cleanup_empty: "No pending suggestions.",
        tab_ai: "Local AI",
        files_suffix: "files",
        simulate_modal_hint: "Nothing moves until you click Organize now.",
        privacy_title: "Only on this computer",
        privacy_caption: "No cloud, no telemetry",
        trash_load_error: "Could not load the trash.",
        disk_analyzer_title: "Disk usage",
        ai_hint: "Martix detects local Ollama automatically when the computer can run it; your files never go to the cloud.",
        ai_status_enabled: "Ollama enabled (LLM mode)",
        ai_status_disabled: "Ollama disabled (heuristic mode)",
        ai_testing: "Testing...",
        ai_test_ok: "Connected successfully and model available",
        ai_test_ok_no_model: "Connected, but the specified model isn't pulled in Ollama",
        ai_test_fail: "Could not connect to Ollama",
        duplicate_action_label: "Action when identical files exist in destination",
        dup_opt_suffix: "Add numeric suffix, e.g. file (1).pdf",
        dup_opt_skip: "Skip movement (keep in Downloads)",
        dup_opt_delete_source: "Delete original file (already saved)",
        save_settings_btn: "Save settings",
        topic_rename_label: "Rename pattern (optional)",
        topic_rename_placeholder: "e.g. {YYYY}-{MM} - {OriginalName}.{ext}",
        rule_rename_label: "Rename pattern (optional)",
        rule_rename_placeholder: "e.g. {Category}/{OriginalName}.{ext}",
        rule_conditions_label: "Activation conditions (optional)",
        btn_add_condition: "+ Add condition",
        cond_field_name: "File name",
        cond_field_stem: "File name (no ext)",
        cond_field_extension: "Extension",
        cond_field_size_kb: "Size (KB)",
        cond_field_age_days: "Age (days)",
        cond_field_content: "Text content",
        cond_field_artist: "Artist",
        cond_field_album: "Album",
        cond_field_title: "Title",
        cond_field_year: "Year",
        cond_field_camera: "Camera",
        cond_field_exif_date: "EXIF Date",
        learn_correction_btn: "Learn from correction",
        learn_correction_title: "Learn from correction / Create rule",
        status_rule_suggested: "Suggested rule loaded into rules tab.",
        status_learn_error: "Could not generate suggested rule.",
        cond_op_contains: "Contains",
        cond_op_not_contains: "Does not contain",
        cond_op_equals: "Equals",
        cond_op_starts_with: "Starts with",
        cond_op_ends_with: "Ends with",
        cond_op_gt: "Greater than",
        cond_op_lt: "Less than",
        cond_op_gte: "Greater than or equal",
        cond_op_lte: "Less than or equal",
        rule_order_hint: "Evaluation order: the first matching rule wins",
        rule_move_up: "Move up (evaluate earlier)",
        rule_move_down: "Move down (evaluate later)",
        disk_scan_truncated: "Partial scan: the folder is too large and the time limit was reached. The totals shown are incomplete.",
        confirm_delete_folder: "You are about to move a folder with {n} files to the trash. Continue?",
        status_moved_to_trash: "Moved to trash",
        cond_value_placeholder: "Value",
        status_settings_saved: "System settings saved.",
        status_settings_save_error: "Could not save configuration.",
        
        home: "Home",
        downloads: "Downloads",
        images: "Images",
        videos: "Videos",
        music: "Music",
        compressed: "Compressed",
        installers: "Installers",
        documents: "Documents",
        other: "Other",
        code: "Development",
        books: "Books",
        fonts: "Fonts",
        data: "Data",
        
        status_conn_error: "Could not connect to Martix.",
        status_patrol_active: "Live sort is on: Downloads.",
        status_patrol_inactive: "Live sort is paused.",
        status_patrol_error: "Could not change live sort.",
        status_organizing: "Organizing...",
        status_organized_done: "Done: {moved} file(s) organized; {review} need review.",
        status_organize_error: "Failed to organize downloads folder.",
        status_folder_error: "Could not open that folder.",
        
        topics_empty: "You don't have any topics yet. Add your first one below.",
        rules_empty: "You don't have any custom rules yet.",
        delete_topic_title: "Delete topic",
        delete_rule_title: "Delete rule",
        status_topic_saved: "Topic saved.",
        status_topic_save_error: "Could not save topic.",
        status_rule_saved: "Rule saved.",
        status_rule_save_error: "Could not save rule.",
        theme_title: "Toggle theme",
        
        welcome_message: "Welcome: define your first Topics (bank, gym, apps...) and that's it, Martix takes care of the rest.",
        
        tab_history: "History",
        history_hint: "Recent Martix movements. If a file ended up in the wrong place, click Undo to return it to its source folder.",
        history_empty: "Martix has not moved any files yet.",
        history_load_error: "Could not load history.",
        undo_title: "Undo: return the file to its source folder",
        status_undone_done: '"{filename}" returned to its source folder.',
        status_undo_error: "Could not undo the movement.",
        history_undone_label: "undone",
        select_all_btn: "Select all",
        undo_selected_btn: "Undo selected",
        status_batch_undo_done: "Successfully undone {count} move(s).",

        tab_trash: "Trash",
        trash_hint: "Items in Martix local quarantine. You can restore them or permanently delete them.",
        trash_empty: "Local quarantine trash is empty.",
        trash_native_active: "System native trash",
        trash_quarantine_active: "Martix local quarantine",
        purge_all_trash_btn: "Empty trash",
        purge_item_btn: "Delete permanently",
        restore_item_btn: "Restore",
        status_trash_restored: '"{filename}" restored successfully.',
        status_trash_purged: "Trash emptied ({count} item(s) deleted).",
        status_trash_item_purged: '"{filename}" deleted permanently.',
        confirm_purge_all_trash: "Are you sure you want to permanently delete all items in local quarantine?",
        
        export_rules_btn: "Export rules (JSON)",
        import_rules_btn: "Import rules (JSON)",
        duplicates_folder_label: "Folders to analyze (optional, comma-separated):",
        duplicates_folder_placeholder: "e.g. Documents, Downloads",
        status_rules_exported: "Rules exported successfully.",
        status_rules_imported: "Rules imported successfully.",
        status_export_error: "Error exporting rules.",
        status_import_error: "Error importing rules.",
        
        tab_duplicates: "Deduplicate",
        duplicates_hint: "Scan and delete duplicate files to free up space.",
        scan_duplicates_btn: "Scan for duplicates",
        auto_select_btn: "Auto-select all but one",
        clean_selected_btn: "Clean Selected",
        scanning_message: "Scanning for duplicate files...",
        duplicates_empty: "No duplicate files found.",
        status_cleaning_done: "Cleaning completed: {count} file(s) deleted.",
        status_cleaning_error: "Could not delete some files.",
        status_scanning_error: "Could not scan for duplicate files.",
        
        tab_maintenance: "Maintenance",
        maintenance_hint: "Configure rules to automatically clean up files from specific folders after a certain number of days.",
        maintenance_folder_label: "Folder",
        maintenance_folder_placeholder: "e.g. Downloads/Junk",
        maintenance_age_label: "Max age (days)",
        maintenance_age_placeholder: "e.g. 30",
        add_maintenance_rule_btn: "Add maintenance rule",
        run_maintenance_btn: "Run maintenance now",
        maintenance_empty: "No maintenance rules configured yet.",
        delete_maintenance_rule_title: "Delete maintenance rule",
        status_maintenance_saved: "Maintenance rule saved.",
        status_maintenance_save_error: "Could not save maintenance rule.",
        status_maintenance_deleted: "Maintenance rule deleted.",
        status_maintenance_delete_error: "Could not delete maintenance rule.",
        status_maintenance_running: "Running maintenance...",
        status_maintenance_run_done: "Maintenance completed: {count} file(s) cleaned up.",
        status_maintenance_run_error: "Could not run maintenance.",

        // Simulate
        simulate_title: "Simulate organization",
        status_simulating: "Simulating...",
        simulate_modal_title: "Simulation results",
        organize_report_title: "Organization report",
        simulate_no_changes: "No files would be moved.",
        simulate_move_label: "would move to",
        simulate_close_btn: "Close",
        status_simulate_error: "Could not run simulation.",

        // Watched folders
        tab_watched: "Watched Folders",
        watched_hint: "Add additional folders that Martix will organize when you click \"Organize now\".",
        watched_folder_label: "Folder path",
        watched_folder_placeholder: "e.g. /home/user/Desktop",
        add_watched_btn: "Add folder",
        watched_empty: "No watched folders configured.",
        delete_watched_title: "Delete watched folder",
        status_watched_saved: "Watched folder added.",
        status_watched_save_error: "Could not add folder.",
        status_watched_deleted: "Watched folder removed.",
        status_watched_delete_error: "Could not remove watched folder.",

        // Statistics
        tab_stats: "Statistics",
        stats_hint: "Summary of Martix activity.",
        stats_total_label: "total files organized",
        stats_top_categories: "Top Categories",
        stats_activity_title: "Activity (last 30 days)",
        stats_no_data: "Not enough data yet.",
        stats_load_error: "Could not load statistics."
    },
    zh: {
        patrol_label: "自动整理",
        patrol_title: "实时整理下载文件夹",
        organize_btn: "立即整理",
        settings_title: "设置",
        organized_count_prefix: "已整理文件",
        empty_state: "此文件夹为空",
        settings_title_modal: "Martix 设置",
        close_title: "关闭",
        tab_topics: "主题",
        tab_rules: "扩展名规则",
        tab_ai: "本地 AI",
        home: "首页",
        downloads: "下载",
        images: "图片",
        videos: "视频",
        music: "音乐",
        compressed: "压缩包",
        installers: "安装包",
        documents: "文档",
        other: "其他",
        theme_dark: "暗色",
        theme_light: "亮色",
        help_btn: "帮助",
        settings_btn: "设置与规则",
        simulate_btn: "模拟测试",
        export_rules_btn: "导出规则 (JSON)",
        import_rules_btn: "导入规则 (JSON)",
        tab_duplicates: "去重",
        tab_watched: "监控文件夹",
        tab_stats: "统计",
        tab_maintenance: "维护",
        tab_history: "历史记录",
        tab_general: "通用设置"
    },
    hi: {
        patrol_label: "ऑटो-व्यवस्थित",
        patrol_title: "रियल-टाइम में डाउनलोड व्यवस्थित करें",
        organize_btn: "अभी व्यवस्थित करें",
        settings_title: "सेटिंग्स",
        organized_count_prefix: "व्यवस्थित फ़ाइलें",
        empty_state: "यह फ़ोल्डर खाली है",
        settings_title_modal: "Martix सेटिंग्स",
        close_title: "बंद करें",
        tab_topics: "विषय",
        tab_rules: "एक्सटेंशन नियम",
        tab_ai: "लोकल AI",
        home: "होम",
        downloads: "डाउनलोड",
        images: "चित्र",
        videos: "वीडियो",
        music: "संगीत",
        compressed: "कंप्रेस्ड",
        installers: "इंस्टॉलर",
        documents: "दस्तावेज़",
        other: "अन्य",
        theme_dark: "डार्क",
        theme_light: "लाइट",
        help_btn: "सहायता",
        settings_btn: "सेटिंग्स और नियम",
        simulate_btn: "सिमुलेशन",
        export_rules_btn: "नियम निर्यात करें",
        import_rules_btn: "नियम आयात करें",
        tab_duplicates: "डुप्लिकेट",
        tab_watched: "निगरानी फ़ोल्डर",
        tab_stats: "आंकड़े",
        tab_maintenance: "रखरखाव",
        tab_history: "इतिहास",
        tab_general: "सामान्य"
    },
    fr: {
        patrol_label: "Auto-Organiser",
        patrol_title: "Organisation automatique des téléchargements en temps réel",
        organize_btn: "Organiser maintenant",
        settings_title: "Paramètres",
        organized_count_prefix: "Fichiers organisés",
        empty_state: "Ce dossier est vide",
        settings_title_modal: "Paramètres de Martix",
        close_title: "Fermer",
        tab_topics: "Thèmes",
        tab_rules: "Règles par extension",
        tab_ai: "IA locale",
        home: "Accueil",
        downloads: "Téléchargements",
        images: "Images",
        videos: "Vidéos",
        music: "Musique",
        compressed: "Archives",
        installers: "Installateurs",
        documents: "Documents",
        other: "Autres",
        theme_dark: "Sombre",
        theme_light: "Clair",
        help_btn: "Aide",
        settings_btn: "Paramètres & Règles",
        simulate_btn: "Simuler (Test)",
        export_rules_btn: "Exporter règles (JSON)",
        import_rules_btn: "Importer règles (JSON)",
        tab_duplicates: "Dédupliquer",
        tab_watched: "Dossiers surveillés",
        tab_stats: "Statistiques",
        tab_maintenance: "Maintenance",
        tab_history: "Historique",
        tab_general: "Général"
    },
    de: {
        patrol_label: "Auto-Organisieren",
        patrol_title: "Downloads in Echtzeit automatisch organisieren",
        organize_btn: "Jetzt organisieren",
        settings_title: "Einstellungen",
        organized_count_prefix: "Organisierte Dateien",
        empty_state: "Dieser Ordner ist leer",
        settings_title_modal: "Martix Einstellungen",
        close_title: "Schließen",
        tab_topics: "Themen",
        tab_rules: "Regeln nach Erweiterung",
        tab_ai: "Lokale KI",
        home: "Startseite",
        downloads: "Downloads",
        images: "Bilder",
        videos: "Videos",
        music: "Musik",
        compressed: "Archive",
        installers: "Installer",
        documents: "Dokumente",
        other: "Sonstiges",
        theme_dark: "Dunkel",
        theme_light: "Hell",
        help_btn: "Hilfe",
        settings_btn: "Einstellungen & Regeln",
        simulate_btn: "Simulieren (Test)",
        export_rules_btn: "Regeln exportieren",
        import_rules_btn: "Regeln importieren",
        tab_duplicates: "Duplikate",
        tab_watched: "Überwachte Ordner",
        tab_stats: "Statistiken",
        tab_maintenance: "Wartung",
        tab_history: "Verlauf",
        tab_general: "Allgemein"
    }
};

let currentLang = localStorage.getItem("martix_lang") || localStorage.getItem("sortix_lang");
if (!currentLang) {
    const navLang = (navigator.language || navigator.userLanguage || "").toLowerCase();
    if (navLang.startsWith("es")) currentLang = "es";
    else if (navLang.startsWith("zh")) currentLang = "zh";
    else if (navLang.startsWith("hi")) currentLang = "hi";
    else if (navLang.startsWith("fr")) currentLang = "fr";
    else if (navLang.startsWith("de")) currentLang = "de";
    else currentLang = "en"; // Global fallback to English
}

function t(key, defaultVal) {
    const translations = TRANSLATIONS[currentLang] || TRANSLATIONS.en;
    if (translations && translations[key] !== undefined) {
        return translations[key];
    }
    const fallback = TRANSLATIONS.en;
    if (fallback && fallback[key] !== undefined) {
        return fallback[key];
    }
    return defaultVal !== undefined ? defaultVal : key;
}

function applyLanguage() {
    document.documentElement.lang = currentLang;
    
    document.querySelectorAll("[data-i18n]").forEach(el => {
        const key = el.getAttribute("data-i18n");
        el.textContent = t(key);
    });

    document.querySelectorAll("[data-i18n-title]").forEach(el => {
        const key = el.getAttribute("data-i18n-title");
        el.setAttribute("title", t(key));
    });

    document.querySelectorAll("[data-i18n-placeholder]").forEach(el => {
        const key = el.getAttribute("data-i18n-placeholder");
        el.setAttribute("placeholder", t(key));
    });

    const langSelect = document.getElementById("lang-select");
    if (langSelect) {
        langSelect.value = currentLang;
    }

    updateThemeButton();
}

// ---- tema claro/oscuro (rdsx style) ---------------------------------------
let currentTheme = localStorage.getItem("martix_theme") || localStorage.getItem("sortix_theme") || "light";

function updateThemeButton() {
    const container = document.getElementById("theme-btn-svg-container");
    const labelEl = document.getElementById("theme-btn-label");
    if (labelEl) {
        labelEl.textContent = currentTheme === "dark" ? t("theme_light", "Claro") : t("theme_dark", "Oscuro");
    }
    if (container) {
        container.innerHTML = currentTheme === "dark" ? svgIcon("sun") : svgIcon("moon");
    }
}

function toggleTheme() {
    const nextTheme = currentTheme === "dark" ? "light" : "dark";
    
    const switchTheme = () => {
        currentTheme = nextTheme;
        localStorage.setItem("martix_theme", currentTheme);
        document.documentElement.classList.toggle("dark", currentTheme === "dark");
        updateThemeButton();
    };

    if (!document.startViewTransition) {
        switchTheme();
    } else {
        document.startViewTransition(switchTheme);
    }
}

const ICONS = {
    sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>',
    moon: '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>',
    downloads: '<path d="M12 3v11m0 0-4-4m4 4 4-4M5 15v3a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-3"/>',
    image: '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="8.5" cy="9.5" r="1.5"/><path d="m21 16-5-5-9 9"/>',
    video: '<rect x="3" y="5" width="14" height="14" rx="2"/><path d="m17 9 4-3v12l-4-3"/>',
    audio: '<path d="M9 18V5l11-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="17" cy="16" r="3"/>',
    archive: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18M9 4v5M9 13h2"/>',
    installer: '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M9 8h6M9 12h6M9 16h3"/>',
    code: '<path d="m8 8-4 4 4 4M16 8l4 4-4 4M14 5l-4 14"/>',
    book: '<path d="M5 4.5A2.5 2.5 0 0 1 7.5 2H20v17H7.5A2.5 2.5 0 0 0 5 21.5z"/><path d="M5 4.5v17M8 6h8"/>',
    font: '<path d="M4 19 10 5h4l6 14M7 14h10"/>',
    data: '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v7c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 12v7c0 1.7 3.6 3 8 3s8-1.3 8-3v-7"/>',
    document: '<path d="M6 2h9l5 5v15H6z"/><path d="M15 2v5h5"/>',
    pdf: '<path d="M6 2h9l5 5v15H6z"/><path d="M15 2v5h5"/><text x="8" y="17" font-size="6" fill="currentColor" stroke="none">PDF</text>',
    other: '<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M3 7l3-4h5l2 3h8"/>',
    folder: '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    topic: '<path d="m12 2 2.5 7.5H22l-6 4.5 2.3 7L12 16.8 5.7 21l2.3-7-6-4.5h7.5z"/>',
    home: '<path d="m3 11 9-8 9 8"/><path d="M5 10v10h14V10"/>',
    settings: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.2a1.7 1.7 0 0 0-1-1.5 1.7 1.7 0 0 0-1.9.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.9 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.2a1.7 1.7 0 0 0 1.5-1 1.7 1.7 0 0 0-.3-1.9l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.9.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.2a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.9-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.9V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.2a1.7 1.7 0 0 0-1.5 1z"/>',
    close: '<path d="M18 6 6 18M6 6l12 12"/>',
    trash: '<path d="M3 6h18M8 6V4a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2m2 0-1 14a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1L5 6"/>',
    chevron: '<path d="m9 18 6-6-6-6"/>',
    undo: '<path d="M9 14 4 9l5-5"/><path d="M4 9h10a6 6 0 0 1 6 6v1a4 4 0 0 1-4 4h-5"/>',
    simulate: '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>',
    eye: '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>',
    chart: '<path d="M18 20V10M12 20V4M6 20v-6"/>',
    brain: '<path d="M12 2a5 5 0 0 0-5 5c0 .6.1 1.2.3 1.8A5 5 0 0 0 3 13a5 5 0 0 0 4.5 4.96A5 5 0 0 0 12 22a5 5 0 0 0 4.5-4.04A5 5 0 0 0 21 13a5 5 0 0 0-4.3-4.2A5 5 0 0 0 12 2z"/>',
};

function svgIcon(name, extraClass) {
    const body = ICONS[name] || ICONS.other;
    return `<svg class="icon ${extraClass || ""}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">${body}</svg>`;
}

const EXT_TO_ICON = {
    jpg: "image", jpeg: "image", png: "image", gif: "image", webp: "image", heic: "image",
    heif: "image", bmp: "image", tiff: "image", svg: "image", raw: "image",
    mp4: "video", mkv: "video", mov: "video", avi: "video", webm: "video", flv: "video", wmv: "video", m4v: "video",
    mp3: "audio", wav: "audio", flac: "audio", ogg: "audio", m4a: "audio", aac: "audio", wma: "audio",
    zip: "archive", rar: "archive", "7z": "archive", tar: "archive", gz: "archive", tgz: "archive", bz2: "archive", xz: "archive",
    exe: "installer", msi: "installer", deb: "installer", rpm: "installer", appimage: "installer", dmg: "installer", pkg: "installer", apk: "installer",
    pdf: "pdf",
    doc: "document", docx: "document", odt: "document", txt: "document", ppt: "document", pptx: "document", xls: "document", xlsx: "document", csv: "document", rtf: "document",
    py: "code", js: "code", mjs: "code", cjs: "code", ts: "code", tsx: "code", jsx: "code", html: "code", htm: "code", css: "code", scss: "code", java: "code", kt: "code", c: "code", h: "code", cpp: "code", cs: "code", go: "code", rs: "code", rb: "code", php: "code", swift: "code", dart: "code", sh: "code", ps1: "code", bat: "code", sql: "code",
    epub: "book", mobi: "book", azw: "book", azw3: "book", djvu: "book",
    ttf: "font", otf: "font", woff: "font", woff2: "font",
    json: "data", xml: "data", yaml: "data", yml: "data", toml: "data", sqlite: "data", sqlite3: "data", db: "data",
};

function iconForFile(ext) {
    return EXT_TO_ICON[ext] || "other";
}

function formatSize(bytes) {
    if (bytes == null) return "";
    if (bytes < 1024) return `${bytes} B`;
    const units = ["KB", "MB", "GB", "TB"];
    let value = bytes / 1024;
    let i = 0;
    while (value >= 1024 && i < units.length - 1) {
        value /= 1024;
        i++;
    }
    return `${value.toFixed(1)} ${units[i]}`;
}

function formatBytes(bytes) {
    return formatSize(bytes);
}

// ---- estado ------------------------------------------------------------

let tree = [];
let currentPath = null; // null => vista raiz (tiles de categorias/temas)

const patrolToggle = document.getElementById("patrol-toggle");
const organizeBtn = document.getElementById("btn-organize");
const filesOrganizedEl = document.getElementById("files-organized-count");
const statusMessageEl = document.getElementById("status-message");
const breadcrumbsEl = document.getElementById("breadcrumbs");
const folderTreeEl = document.getElementById("folder-tree");
const fileGridEl = document.getElementById("file-grid");
const emptyStateEl = document.getElementById("empty-state");
const contentTitleEl = document.getElementById("content-title");
const contentDescriptionEl = document.getElementById("content-description");
const cleanupPanelEl = document.getElementById("cleanup-panel");
const cleanupCountEl = document.getElementById("cleanup-count");
const cleanupSuggestionsEl = document.getElementById("cleanup-suggestions-list");

const settingsModal = document.getElementById("settings-modal");
const topicsListEl = document.getElementById("topics-list");
const rulesListEl = document.getElementById("rules-list");
const topicForm = document.getElementById("topic-form");
const ruleForm = document.getElementById("rule-form");
const maintenanceListEl = document.getElementById("maintenance-list");
const maintenanceForm = document.getElementById("maintenance-form");
const btnRunMaintenance = document.getElementById("btn-run-maintenance");
const simulateBtn = document.getElementById("btn-simulate");
const watchedListEl = document.getElementById("watched-folders-list");
const watchedForm = document.getElementById("watched-form");

let statusTimer = null;
let simulationRows = [];
let simulationPage = 0;
const SIMULATION_PAGE_SIZE = 100;

function showStatus(message, isError = false) {
    statusMessageEl.textContent = message;
    statusMessageEl.classList.toggle("error", isError);
    clearTimeout(statusTimer);
    statusTimer = setTimeout(() => { statusMessageEl.textContent = ""; }, 6000);
}

async function refreshCleanupSuggestions() {
    if (!cleanupPanelEl || !cleanupSuggestionsEl) return;
    try {
        const suggestions = await fetchJSON("/api/cleanup-suggestions");
        cleanupCountEl.textContent = suggestions.length;
        cleanupPanelEl.hidden = suggestions.length === 0;
        cleanupSuggestionsEl.innerHTML = suggestions.length
            ? suggestions.map(item => `
                <div class="cleanup-item" data-suggestion-id="${Number(item.id)}">
                    <div class="cleanup-item-main">
                        <strong>${escapeHtml(item.filename)}</strong>
                        <span>${escapeHtml(item.reason)} · ${escapeHtml(item.path)}</span>
                    </div>
                    <div class="cleanup-item-actions">
                        <button type="button" class="btn btn-danger cleanup-delete" data-id="${Number(item.id)}">${escapeHtml(t("cleanup_delete_btn"))}</button>
                        <button type="button" class="btn btn-quiet cleanup-dismiss" data-id="${Number(item.id)}">${escapeHtml(t("cleanup_dismiss_btn"))}</button>
                    </div>
                </div>
            `).join("")
            : `<p class="hint">${escapeHtml(t("cleanup_empty"))}</p>`;

        cleanupSuggestionsEl.querySelectorAll(".cleanup-delete").forEach(button => {
            button.addEventListener("click", async () => {
                button.disabled = true;
                try {
                    await fetchJSON(`/api/cleanup-suggestions/${Number(button.dataset.id)}/delete`, { method: "POST" });
                    showStatus(t("cleanup_deleted"));
                    await refreshCleanupSuggestions();
                } catch (err) {
                    button.disabled = false;
                    showStatus(err.message, true);
                }
            });
        });
        cleanupSuggestionsEl.querySelectorAll(".cleanup-dismiss").forEach(button => {
            button.addEventListener("click", async () => {
                try {
                    await fetchJSON(`/api/cleanup-suggestions/${Number(button.dataset.id)}/dismiss`, { method: "POST" });
                    showStatus(t("cleanup_dismissed"));
                    await refreshCleanupSuggestions();
                } catch (err) {
                    showStatus(err.message, true);
                }
            });
        });
    } catch (err) {
        console.warn("No se pudieron cargar las sugerencias de limpieza", err);
    }
}

// Si Martix esta configurado con MARTIX_TOKEN (p.ej. expuesto en la LAN),
// la API responde 401 hasta que el navegador presente el token. Se pide una
// una vez y se conserva solo durante la ventana actual.
function withToken(options) {
    // Tokens are only kept for the current window. Persisting a LAN/API token
    // in localStorage made it recoverable by any later script running in this
    // origin; the desktop build does not need a token at all.
    const token = sessionStorage.getItem("martix_token") || sessionStorage.getItem("sortix_token");
    const base = options || {};
    const headers = { ...(base.headers || {}), "X-Martix-Client": "martix-ui" };
    if (!token) return { ...base, headers };
    return { ...base, headers: { ...headers, "X-Martix-Token": token, "X-Sortix-Token": token } };
}

async function fetchJSON(url, options) {
    let res = await fetch(url, withToken(options));
    if (res.status === 401) {
        const token = prompt("Esta instancia de Martix esta protegida.\nIntroduce el token de acceso (MARTIX_TOKEN):");
        if (token) {
            sessionStorage.setItem("martix_token", token.trim());
            res = await fetch(url, withToken(options));
        }
    }
    if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.error || `Error ${res.status}`);
    }
    if (res.status === 204) return null;
    return res.json();
}

// ---- barra lateral / arbol ----------------------------------------------

async function loadTree() {
    tree = await fetchJSON("/api/tree");
    renderSidebar();
}

function renderSidebar() {
    folderTreeEl.innerHTML = "";

    const homeItem = document.createElement("li");
    const homeBtn = document.createElement("button");
    homeBtn.type = "button";
    homeBtn.className = "tree-item" + (currentPath === null ? " active" : "");
    homeBtn.innerHTML = `${svgIcon("home")}<span>${t("home", "Inicio")}</span>`;
    homeBtn.addEventListener("click", () => navigateTo(null));
    homeItem.appendChild(homeBtn);
    folderTreeEl.appendChild(homeItem);

    for (const item of tree) {
        const li = document.createElement("li");
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "tree-item" + (currentPath === item.path ? " active" : "");
        btn.innerHTML = `${svgIcon(item.icon)}<span>${escapeHtml(t(item.key, item.label))}</span>`;
        btn.addEventListener("click", () => navigateTo(item.path));
        li.appendChild(btn);
        folderTreeEl.appendChild(li);
    }
}

// Escapa texto para insertarlo en HTML, INCLUIDO dentro de atributos.
//
// La version anterior hacia `div.textContent = text; return div.innerHTML`, que
// solo escapa & < >. Los nombres de archivo los controla quien envia la
// descarga, asi que una carpeta llamada  x" onmouseover="..."  se salia del
// atributo title="" del analizador de espacio y ejecutaba JavaScript en el
// origen de Martix, con acceso a toda la API local (incluidos los endpoints de
// borrado). Las comillas y el acento grave TIENEN que escaparse aqui.
function escapeHtml(text) {
    if (text === null || text === undefined) return "";
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;")
        .replace(/`/g, "&#96;");
}

// Coacciona un valor del servidor a numero antes de meterlo en un atributo
// style. Los porcentajes y tamanos vienen calculados del backend, pero si un
// dia llegasen como cadena se colarian dentro del CSS de la pagina.
function safeNumber(value, fallback = 0) {
    const n = Number(value);
    return Number.isFinite(n) ? n : fallback;
}

// Solo permite colores en formato #rgb / #rrggbb; cualquier otra cosa cae al
// gris neutro en vez de inyectarse tal cual en el atributo style.
function safeColor(value, fallback = "#8d8b85") {
    return /^#[0-9a-fA-F]{3,8}$/.test(String(value || "")) ? String(value) : fallback;
}

// ---- navegacion / breadcrumbs --------------------------------------------

function labelForPath(path) {
    const match = tree.find((item) => item.path === path);
    if (match) return t(match.key, match.label);
    const segments = path.split("/");
    return segments[segments.length - 1];
}

function renderBreadcrumbs() {
    breadcrumbsEl.innerHTML = "";

    const homeCrumb = document.createElement("button");
    homeCrumb.className = "crumb";
    homeCrumb.innerHTML = `${svgIcon("home")}<span>${t("home", "Inicio")}</span>`;
    homeCrumb.addEventListener("click", () => navigateTo(null));
    breadcrumbsEl.appendChild(homeCrumb);

    if (currentPath === null) return;

    const segments = currentPath.split("/");
    let accumulated = "";
    segments.forEach((segment, index) => {
        accumulated = accumulated ? `${accumulated}/${segment}` : segment;
        const sep = document.createElement("span");
        sep.className = "crumb-sep";
        sep.innerHTML = svgIcon("chevron");
        breadcrumbsEl.appendChild(sep);

        const crumb = document.createElement("button");
        crumb.className = "crumb";
        const isLast = index === segments.length - 1;
        crumb.textContent = labelForPath(accumulated);
        const target = accumulated;
        crumb.addEventListener("click", () => navigateTo(target));
        if (isLast) crumb.classList.add("current");
        breadcrumbsEl.appendChild(crumb);
    });
}

async function navigateTo(path) {
    currentPath = path;
    renderSidebar();
    renderBreadcrumbs();
    await renderContent();
}

// ---- contenido principal --------------------------------------------------

async function renderContent() {
    fileGridEl.innerHTML = "";
    emptyStateEl.hidden = true;
    if (contentTitleEl) {
        contentTitleEl.textContent = currentPath === null
            ? t("home", "Inicio")
            : labelForPath(currentPath);
    }
    if (contentDescriptionEl) {
        contentDescriptionEl.textContent = currentPath === null
            ? t("content_description", "Tus carpetas importantes, en un solo lugar.")
            : t("folder_view_description", "Contenido de esta carpeta.");
    }

    if (currentPath === null) {
        renderRootTiles();
        return;
    }

    try {
        const data = await fetchJSON(`/api/browse?path=${encodeURIComponent(currentPath)}`);
        if (!data.exists || data.entries.length === 0) {
            emptyStateEl.hidden = false;
            return;
        }
        for (const entry of data.entries) {
            fileGridEl.appendChild(buildTile(entry));
        }
    } catch (err) {
        showStatus(t("status_folder_error"), true);
    }
}

function renderRootTiles() {
    fileGridEl.innerHTML = "";
    for (const item of tree) {
        const card = document.createElement("button");
        card.type = "button";
        card.className = "category-card";
        card.innerHTML = `
            <span class="category-card-icon">${svgIcon(item.icon)}</span>
            <span class="category-card-copy">
                <span class="category-card-title">${escapeHtml(t(item.key, item.label))}</span>
                <span class="category-card-count">${item.count !== undefined ? item.count + ' ' + t("files_suffix", "archivos") : t("open_folder", "Abrir carpeta")}</span>
            </span>
            <span class="category-card-action" aria-hidden="true">${svgIcon("chevron")}</span>
        `;
        card.addEventListener("click", () => navigateTo(item.path));
        fileGridEl.appendChild(card);
    }
}

function buildTile(entry) {
    const tile = document.createElement(entry.is_dir ? "button" : "div");
    if (entry.is_dir) {
        tile.type = "button";
        tile.className = "tile folder-tile";
        tile.innerHTML = `
            <span class="tile-leading">${svgIcon("folder", "tile-icon")}</span>
            <span class="tile-info"><span class="tile-name">${escapeHtml(entry.name)}</span><span class="tile-meta">${escapeHtml(t("folder_label", "Carpeta"))}</span></span>
            <span class="tile-action" aria-hidden="true">${svgIcon("chevron")}</span>
        `;
        tile.addEventListener("click", () => navigateTo(entry.path));
    } else {
        tile.className = "tile file-tile";
        tile.title = `${entry.name} - ${formatSize(entry.size)} - ${entry.modified}`;
        tile.innerHTML = `
            <span class="tile-leading">${svgIcon(iconForFile(entry.ext), "tile-icon")}</span>
            <span class="tile-info"><span class="tile-name">${escapeHtml(entry.name)}</span><span class="tile-meta">${formatSize(entry.size)}${entry.modified ? ` · ${escapeHtml(entry.modified)}` : ""}</span></span>
            <span class="tile-size">${formatSize(entry.size)}</span>
        `;
    }
    return tile;
}

// ---- estado global: patrulla / stats --------------------------------------

async function refreshStatus() {
    try {
        const data = await fetchJSON("/api/status");
        patrolToggle.checked = data.active;
        filesOrganizedEl.textContent = data.files_organized;

        const pill = document.getElementById("patrol-status-pill");
        const pillText = document.getElementById("patrol-status-text");
        if (pill && pillText) {
            pill.className = "status-pill " + (data.active ? "active" : "inactive");
            pillText.textContent = data.active ? t("patrol_on") : t("patrol_off");
        }
    } catch (err) {
        showStatus(t("status_conn_error"), true);
    }
}

patrolToggle.addEventListener("change", async () => {
    const desired = patrolToggle.checked;
    try {
        const data = await fetchJSON("/api/patrol/toggle", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ active: desired }),
        });
        patrolToggle.checked = data.active;
        const pill = document.getElementById("patrol-status-pill");
        const pillText = document.getElementById("patrol-status-text");
        if (pill && pillText) {
            pill.className = "status-pill " + (data.active ? "active" : "inactive");
            pillText.textContent = data.active ? t("patrol_on") : t("patrol_off");
        }
        showStatus(data.active ? t("status_patrol_active") : t("status_patrol_inactive"));
    } catch (err) {
        patrolToggle.checked = !desired;
        showStatus(t("status_patrol_error"), true);
    }
});

organizeBtn.addEventListener("click", async () => {
    organizeBtn.disabled = true;
    showStatus(t("status_organizing"));
    try {
        const data = await fetchJSON("/api/organize-now", { method: "POST" });
        const reviewCount = Number(data.review_count ?? (Array.isArray(data.review) ? data.review.length : 0));
        let doneMessage = t("status_organized_done")
            .replace("{moved}", data.moved)
            .replace("{review}", reviewCount);
        if (data.truncated) {
            doneMessage += " La revision se ha limitado; vuelve a ejecutar el barrido.";
        }
        showStatus(doneMessage);
        const reportRows = [
            ...(Array.isArray(data.items) ? data.items.map(item => ({
                ...item,
                status: "move",
                current_path: item.source,
                would_move_to: item.destination,
            })) : []),
            ...(Array.isArray(data.review) ? data.review : []),
            ...(Array.isArray(data.skipped) ? data.skipped : []),
        ];
        if (reportRows.length > 0) {
            showSimulateResults({ simulated: reportRows, mode: "organize" });
        }
        await refreshCleanupSuggestions();
        await refreshStatus();
        await loadTree();
        if (currentPath !== null) await renderContent();
    } catch (err) {
        showStatus(t("status_organize_error"), true);
    } finally {
        organizeBtn.disabled = false;
    }
});

// ---- simulación (dry run) ---------------------------------------------------

if (simulateBtn) {
    simulateBtn.addEventListener("click", async () => {
        simulateBtn.disabled = true;
        showStatus(t("status_simulating"));
        try {
            const data = await fetchJSON("/api/simulate", { method: "POST" });
            showSimulateResults(data);
        } catch (err) {
            showStatus(err.message || t("status_simulate_error"), true);
        } finally {
            simulateBtn.disabled = false;
        }
    });
}

function showSimulateResultsLegacy(data) {
    const modal = document.getElementById("simulate-modal");
    const container = document.getElementById("simulate-results-body");
    const closeBtnHeader = document.getElementById("btn-close-simulate");
    const closeBtnFooter = document.getElementById("btn-close-simulate-footer");

    if (!modal || !container) return;

    const moves = Array.isArray(data) ? data : (data.simulated || []);
    const previewWasTruncated = moves.some(item => item.status === "truncated");
    const previewRows = moves.filter(item => item.status !== "truncated");
    // Una carpeta de Descargas puede contener miles de archivos. Pintarlos
    // todos en un dialogo crea miles de nodos DOM y deja QWebEngine en "No
    // responde" aunque el servidor haya terminado correctamente.
    const maxPreviewRows = 250;

    if (!previewRows || previewRows.length === 0) {
        container.innerHTML = `<div class="empty-state-card" style="padding: 30px;"><div class="empty-icon-badge">${svgIcon("folder")}</div><h3>${t("simulate_no_changes")}</h3><p>${t("simulate_modal_hint")}</p></div>`;
    } else {
        container.innerHTML = previewRows.slice(0, maxPreviewRows).map(item => `
            <div class="simulation-row ${item.status === "review" ? "review" : ""}">
                <span class="simulate-file">${escapeHtml(item.filename || item.file)}</span>
                <span aria-hidden="true">→</span>
                <span class="simulate-target">${escapeHtml(item.would_move_to || item.destination || "Se queda para revisión")}</span>
            </div>
        `).join("");
        if (previewWasTruncated || previewRows.length > maxPreviewRows) {
            const notice = document.createElement("p");
            notice.className = "hint simulation-limit-notice";
            const shown = Math.min(maxPreviewRows, previewRows.length);
            notice.textContent = previewWasTruncated
                ? `Vista previa parcial: se muestran ${shown} resultados. Organizar ahora no usa este limite.`
                : `Se muestran ${shown} de ${previewRows.length} resultados para mantener la app fluida.`;
            container.prepend(notice);
        }
    }

    if (closeBtnHeader) closeBtnHeader.onclick = () => modal.close();
    if (closeBtnFooter) closeBtnFooter.onclick = () => modal.close();
    modal.showModal();
}

// The preview is paginated so the full server report remains available without
// creating thousands of DOM nodes at once.
function renderSimulationPage() {
    const container = document.getElementById("simulate-results-body");
    const pagination = document.getElementById("simulate-pagination");
    const prevBtn = document.getElementById("btn-simulate-prev");
    const nextBtn = document.getElementById("btn-simulate-next");
    const pageLabel = document.getElementById("simulate-page-label");
    if (!container) return;

    const counts = simulationRows.reduce((acc, item) => {
        const key = item.status || "skipped";
        acc[key] = (acc[key] || 0) + 1;
        return acc;
    }, {});
    const totalPages = Math.max(1, Math.ceil(simulationRows.length / SIMULATION_PAGE_SIZE));
    simulationPage = Math.min(simulationPage, totalPages - 1);
    const start = simulationPage * SIMULATION_PAGE_SIZE;
    const pageRows = simulationRows.slice(start, start + SIMULATION_PAGE_SIZE);

    const summary = document.createElement("div");
    summary.className = "simulation-summary";
    summary.textContent = `${simulationRows.length} elementos · ${counts.move || 0} se moverian · ${counts.review || 0} para revision · ${(counts.skipped || 0) + (counts.already_there || 0)} sin mover`;

    if (simulationRows.length === 0) {
        container.replaceChildren(summary);
        const empty = document.createElement("div");
        empty.className = "empty-state-card";
        empty.style.padding = "30px";
        empty.innerHTML = `<div class="empty-icon-badge">${svgIcon("folder")}</div><h3>${t("simulate_no_changes")}</h3><p>${t("simulate_modal_hint")}</p>`;
        container.appendChild(empty);
    } else {
        const list = document.createElement("div");
        list.innerHTML = pageRows.map(item => {
            const isReview = item.status === "review";
            const isSkipped = item.status === "skipped" || item.status === "already_there";
            const target = isReview
                ? "Se queda para revision"
                : isSkipped
                    ? (item.reason || "No se mueve")
                    : (item.would_move_to || item.destination || "Sin destino");
            const rowClass = isReview ? "review" : (isSkipped ? "skipped" : "");
            return `
                <div class="simulation-row ${rowClass}">
                    <span class="simulate-file">${escapeHtml(item.filename || item.file)}</span>
                    <span aria-hidden="true">→</span>
                    <span class="simulate-target">${escapeHtml(target)}</span>
                </div>
            `;
        }).join("");
        container.replaceChildren(summary, list);
    }

    if (pagination) pagination.hidden = totalPages <= 1;
    if (prevBtn) {
        prevBtn.disabled = simulationPage === 0;
        prevBtn.onclick = () => {
            if (simulationPage > 0) {
                simulationPage -= 1;
                renderSimulationPage();
            }
        };
    }
    if (nextBtn) {
        nextBtn.disabled = simulationPage >= totalPages - 1;
        nextBtn.onclick = () => {
            if (simulationPage < totalPages - 1) {
                simulationPage += 1;
                renderSimulationPage();
            }
        };
    }
    if (pageLabel) {
        const first = simulationRows.length ? start + 1 : 0;
        const last = Math.min(start + SIMULATION_PAGE_SIZE, simulationRows.length);
        pageLabel.textContent = `Pagina ${simulationPage + 1} de ${totalPages} · ${first}-${last}`;
    }
}

function showSimulateResults(data) {
    const modal = document.getElementById("simulate-modal");
    const closeBtnHeader = document.getElementById("btn-close-simulate");
    const closeBtnFooter = document.getElementById("btn-close-simulate-footer");
    if (!modal) return;

    const rows = Array.isArray(data) ? data : (data.simulated || []);
    const title = modal.querySelector("h2");
    if (title) {
        title.textContent = !Array.isArray(data) && data.mode === "organize"
            ? t("organize_report_title", "Resultado de la organizacion")
            : t("simulate_modal_title");
    }
    simulationRows = rows.filter(item => item.status !== "truncated");
    simulationPage = 0;
    renderSimulationPage();

    if (closeBtnHeader) closeBtnHeader.onclick = () => modal.close();
    if (closeBtnFooter) closeBtnFooter.onclick = () => modal.close();
    modal.showModal();
}

// ---- ajustes: temas --------------------------------------------------------

async function refreshTopics() {
    const topics = await fetchJSON("/api/topics");
    topicsListEl.innerHTML = "";
    if (topics.length === 0) {
        topicsListEl.innerHTML = `<li class="empty">${t("topics_empty")}</li>`;
    }
    for (const topic of topics) {
        const li = document.createElement("li");
        li.innerHTML = `<div class="settings-item-main">
            <strong>${escapeHtml(topic.name)}</strong>
            <span class="muted">&rarr; ${escapeHtml(topic.destination)}</span>
            <span class="keywords">${topic.keywords.map(escapeHtml).join(", ")}</span>
        </div>`;
        const delBtn = document.createElement("button");
        delBtn.className = "icon-btn danger";
        delBtn.innerHTML = svgIcon("trash");
        delBtn.title = t("delete_topic_title");
        delBtn.addEventListener("click", async () => {
            await fetchJSON(`/api/topics/${topic.id}`, { method: "DELETE" });
            await refreshTopics();
            await loadTree();
        });
        li.appendChild(delBtn);
        topicsListEl.appendChild(li);
    }
}

topicForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const name = document.getElementById("topic-name").value.trim();
    const destination = document.getElementById("topic-destination").value.trim();
    const keywords = document.getElementById("topic-keywords").value.trim();
    const rename_pattern = document.getElementById("topic-rename-pattern").value.trim();
    if (!name || !destination || !keywords) return;
    try {
        await fetchJSON("/api/topics", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, destination, keywords, rename_pattern }),
        });
        topicForm.reset();
        await refreshTopics();
        await loadTree();
        showStatus(t("status_topic_saved"));
    } catch (err) {
        showStatus(err.message || t("status_topic_save_error"), true);
    }
});

// ---- ajustes: reglas por extension ------------------------------------------

const conditionsContainer = document.getElementById("rule-conditions-container");
const btnAddCondition = document.getElementById("btn-add-condition");

function createConditionRow(data = {}) {
    const row = document.createElement("div");
    row.className = "condition-row";

    row.innerHTML = `
        <select class="cond-field select-control" aria-label="${t("cond_field_name") || "Campo"}">
            <option value="name">${t("cond_field_name")}</option>
            <option value="stem">${t("cond_field_stem")}</option>
            <option value="extension">${t("cond_field_extension")}</option>
            <option value="size_kb">${t("cond_field_size_kb")}</option>
            <option value="age_days">${t("cond_field_age_days")}</option>
            <option value="content">${t("cond_field_content")}</option>
            <option value="artist">${t("cond_field_artist")}</option>
            <option value="album">${t("cond_field_album")}</option>
            <option value="title">${t("cond_field_title")}</option>
            <option value="year">${t("cond_field_year")}</option>
            <option value="camera">${t("cond_field_camera")}</option>
            <option value="exif_date">${t("cond_field_exif_date")}</option>
        </select>
        <select class="cond-operator select-control" aria-label="Operador">
            <option value="contains">${t("cond_op_contains")}</option>
            <option value="not_contains">${t("cond_op_not_contains")}</option>
            <option value="equals">${t("cond_op_equals")}</option>
            <option value="starts_with">${t("cond_op_starts_with")}</option>
            <option value="ends_with">${t("cond_op_ends_with")}</option>
            <option value="gt">${t("cond_op_gt")}</option>
            <option value="lt">${t("cond_op_lt")}</option>
            <option value="gte">${t("cond_op_gte")}</option>
            <option value="lte">${t("cond_op_lte")}</option>
        </select>
        <input type="text" class="cond-value text-control" placeholder="${t("cond_value_placeholder")}" aria-label="Valor">
        <button type="button" class="btn-remove-cond icon-button danger" title="Eliminar condición" aria-label="Eliminar condición">&times;</button>
    `;

    const fieldSel = row.querySelector(".cond-field");
    const opSel = row.querySelector(".cond-operator");
    const valInput = row.querySelector(".cond-value");
    const removeBtn = row.querySelector(".btn-remove-cond");

    function updateInputType() {
        if (fieldSel.value === "age_days" || fieldSel.value === "size_kb") {
            valInput.type = "number";
            valInput.step = "any";
        } else {
            valInput.type = "text";
        }
    }

    fieldSel.addEventListener("change", updateInputType);

    if (data.field) fieldSel.value = data.field;
    if (data.operator) opSel.value = data.operator;
    if (data.value !== undefined) valInput.value = data.value;

    updateInputType();

    removeBtn.addEventListener("click", () => {
        row.remove();
    });

    conditionsContainer.appendChild(row);
}

if (btnAddCondition) {
    btnAddCondition.addEventListener("click", () => {
        createConditionRow();
    });
}

async function refreshRules() {
    const rules = await fetchJSON("/api/rules");
    rulesListEl.innerHTML = "";
    if (rules.length === 0) {
        rulesListEl.innerHTML = `<li class="empty">${t("rules_empty")}</li>`;
    }
    let index = 0;
    for (const rule of rules) {
        const li = document.createElement("li");
        
        let details = [];
        if (rule.rename_pattern) {
            details.push(`Renombrar: <code>${escapeHtml(rule.rename_pattern)}</code>`);
        }
        if (rule.conditions) {
            try {
                const conds = JSON.parse(rule.conditions);
                if (conds && conds.length > 0) {
                    const condStrs = conds.map(c => {
                        const fieldName = escapeHtml(t(`cond_field_${c.field}`) || c.field);
                        const opName = escapeHtml(t(`cond_op_${c.operator}`) || c.operator);
                        return `${fieldName} ${opName.toLowerCase()} "${escapeHtml(c.value)}"`;
                    });
                    details.push(`Condiciones: ${condStrs.join(" AND ")}`);
                }
            } catch(e) {}
        }
        
        const detailsStr = details.length > 0 
            ? `<div class="rule-details" style="font-size: 0.75rem; margin-top: 4px; color: var(--color-text-muted);">${details.join(" | ")}</div>`
            : "";
            
        // El orden decide que regla gana cuando varias casan con el mismo
        // archivo, asi que se muestra y se puede cambiar.
        li.innerHTML = `
            <div class="settings-item-main" style="display: flex; flex-direction: column;">
                <div>
                    <span class="rule-order-badge" title="${escapeHtml(t("rule_order_hint"))}">${index + 1}</span>
                    <strong>.${escapeHtml(rule.extension)}</strong>
                    <span class="muted">&rarr; ${escapeHtml(rule.destination)}</span>
                </div>
                ${detailsStr}
            </div>
        `;

        const actions = document.createElement("div");
        actions.style.display = "flex";
        actions.style.gap = "4px";

        const moveRule = async (delta) => {
            const ids = rules.map(r => r.id);
            const from = index;
            const to = from + delta;
            if (to < 0 || to >= ids.length) return;
            [ids[from], ids[to]] = [ids[to], ids[from]];
            await fetchJSON("/api/rules/reorder", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ ids }),
            });
            await refreshRules();
        };

        const upBtn = document.createElement("button");
        upBtn.className = "icon-btn";
        upBtn.textContent = "↑";
        upBtn.title = t("rule_move_up");
        upBtn.disabled = index === 0;
        upBtn.addEventListener("click", () => moveRule(-1));

        const downBtn = document.createElement("button");
        downBtn.className = "icon-btn";
        downBtn.textContent = "↓";
        downBtn.title = t("rule_move_down");
        downBtn.disabled = index === rules.length - 1;
        downBtn.addEventListener("click", () => moveRule(1));

        const delBtn = document.createElement("button");
        delBtn.className = "icon-btn danger";
        delBtn.innerHTML = svgIcon("trash");
        delBtn.title = t("delete_rule_title");
        delBtn.addEventListener("click", async () => {
            await fetchJSON(`/api/rules/${rule.id}`, { method: "DELETE" });
            await refreshRules();
        });

        actions.append(upBtn, downBtn, delBtn);
        li.appendChild(actions);
        rulesListEl.appendChild(li);
        index += 1;
    }
}

ruleForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const extension = document.getElementById("rule-extension").value.trim();
    const destination = document.getElementById("rule-destination").value.trim();
    const rename_pattern = document.getElementById("rule-rename-pattern").value.trim();
    
    // Compilar condiciones visuales
    const condRows = conditionsContainer.querySelectorAll(".condition-row");
    const conditions = [];
    for (const row of condRows) {
        const field = row.querySelector(".cond-field").value;
        const operator = row.querySelector(".cond-operator").value;
        const value = row.querySelector(".cond-value").value.trim();
        if (field && operator && value) {
            conditions.push({ field, operator, value });
        }
    }

    if (!extension || !destination) return;

    try {
        await fetchJSON("/api/rules", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                extension,
                destination,
                rename_pattern,
                conditions: conditions.length > 0 ? conditions : null
            }),
        });
        ruleForm.reset();
        conditionsContainer.innerHTML = "";
        await refreshRules();
        showStatus(t("status_rule_saved"));
    } catch (err) {
        showStatus(err.message || t("status_rule_save_error"), true);
    }
});

// ---- historial de movimientos + deshacer -----------------------------------

const historyListEl = document.getElementById("history-list");
let selectedHistoryIds = new Set();

function formatDate(sqlDate) {
    if (!sqlDate) return "";
    // SQLite guarda "YYYY-MM-DD HH:MM:SS" en UTC
    const date = new Date(sqlDate.replace(" ", "T") + "Z");
    if (Number.isNaN(date.getTime())) return sqlDate;
    return date.toLocaleString(undefined, { dateStyle: "short", timeStyle: "short" });
}

async function refreshHistory() {
    selectedHistoryIds.clear();
    const btnUndoSelected = document.getElementById("btn-history-undo-selected");
    if (btnUndoSelected) btnUndoSelected.disabled = true;

    let moves;
    try {
        moves = await fetchJSON("/api/log?limit=50");
    } catch (err) {
        historyListEl.innerHTML = `<li class="empty">${t("history_load_error")}</li>`;
        return;
    }
    historyListEl.innerHTML = "";
    if (moves.length === 0) {
        historyListEl.innerHTML = `<li class="empty">${t("history_empty")}</li>`;
        return;
    }
    for (const move of moves) {
        const li = document.createElement("li");
        if (move.undone_at) li.classList.add("undone");
        const undoneText = move.undone_at ? ` &middot; ${t("history_undone_label")}` : "";
        const isUndoable = !move.undone_at && move.undoable !== false;

        let checkboxHtml = "";
        if (isUndoable) {
            checkboxHtml = `<input type="checkbox" class="history-item-checkbox" data-move-id="${move.id}" style="margin-right: 8px; cursor: pointer;">`;
        }

        li.innerHTML = `
            ${checkboxHtml}
            <div class="settings-item-main">
                <strong>${escapeHtml(move.filename)}</strong>
                <span class="muted">${escapeHtml(move.category)} &rarr; ${escapeHtml(move.destination)}</span>
                <span class="keywords">${escapeHtml(formatDate(move.moved_at))}${undoneText}</span>
            </div>`;

        if (isUndoable) {
            const checkbox = li.querySelector(".history-item-checkbox");
            if (checkbox) {
                checkbox.addEventListener("change", (e) => {
                    if (e.target.checked) selectedHistoryIds.add(move.id);
                    else selectedHistoryIds.delete(move.id);
                    if (btnUndoSelected) btnUndoSelected.disabled = selectedHistoryIds.size === 0;
                });
            }

            const actionContainer = document.createElement("div");
            actionContainer.style.display = "flex";
            actionContainer.style.gap = "6px";

            const learnBtn = document.createElement("button");
            learnBtn.className = "icon-btn";
            learnBtn.innerHTML = svgIcon("brain");
            learnBtn.title = t("learn_correction_title");
            learnBtn.addEventListener("click", async () => {
                learnBtn.disabled = true;
                try {
                    const ruleData = await fetchJSON("/api/learn-correction", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            filename: move.filename,
                            to_folder: move.destination,
                            from_folder: move.source
                        })
                    });
                    openSettings("rules");
                    if (ruleData) {
                        const extInput = document.getElementById("rule-extension");
                        const destInput = document.getElementById("rule-destination");
                        if (extInput && ruleData.extension) {
                            extInput.value = ruleData.extension;
                        } else if (extInput && ruleData.conditions) {
                            const extCond = ruleData.conditions.find(c => c.field === "extension");
                            if (extCond) extInput.value = extCond.value.replace(/^\./, "");
                        }
                        if (destInput && ruleData.destination) {
                            destInput.value = ruleData.destination;
                        }
                        const conditionsContainer = document.getElementById("rule-conditions-container");
                        if (conditionsContainer && Array.isArray(ruleData.conditions)) {
                            conditionsContainer.innerHTML = "";
                            ruleData.conditions.forEach(cond => createConditionRow(cond));
                        }
                    }
                    showStatus(t("status_rule_suggested"));
                } catch (err) {
                    showStatus(err.message || t("status_learn_error"), true);
                } finally {
                    learnBtn.disabled = false;
                }
            });
            actionContainer.appendChild(learnBtn);

            const undoBtn = document.createElement("button");
            undoBtn.className = "icon-btn";
            undoBtn.innerHTML = svgIcon("undo");
            undoBtn.title = t("undo_title");
            undoBtn.addEventListener("click", async () => {
                undoBtn.disabled = true;
                try {
                    const result = await fetchJSON(`/api/log/${move.id}/undo`, { method: "POST" });
                    showStatus(t("status_undone_done").replace("{filename}", result.filename));
                    await Promise.all([refreshHistory(), refreshStatus()]);
                    if (currentPath !== null) await renderContent();
                } catch (err) {
                    undoBtn.disabled = false;
                    showStatus(err.message || t("status_undo_error"), true);
                }
            });
            actionContainer.appendChild(undoBtn);

            li.appendChild(actionContainer);
        }
        historyListEl.appendChild(li);
    }
}

const btnHistorySelectAll = document.getElementById("btn-history-select-all");
if (btnHistorySelectAll) {
    btnHistorySelectAll.addEventListener("click", () => {
        const checkboxes = document.querySelectorAll(".history-item-checkbox");
        const allChecked = Array.from(checkboxes).length > 0 && Array.from(checkboxes).every(cb => cb.checked);
        checkboxes.forEach(cb => {
            cb.checked = !allChecked;
            const mid = parseInt(cb.dataset.moveId, 10);
            if (!allChecked) selectedHistoryIds.add(mid);
            else selectedHistoryIds.delete(mid);
        });
        const btnUndoSelected = document.getElementById("btn-history-undo-selected");
        if (btnUndoSelected) btnUndoSelected.disabled = selectedHistoryIds.size === 0;
    });
}

const btnHistoryUndoSelected = document.getElementById("btn-history-undo-selected");
if (btnHistoryUndoSelected) {
    btnHistoryUndoSelected.addEventListener("click", async () => {
        if (selectedHistoryIds.size === 0) return;
        btnHistoryUndoSelected.disabled = true;
        try {
            const res = await fetchJSON("/api/log/undo-batch", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ move_ids: Array.from(selectedHistoryIds) })
            });
            showStatus(t("status_batch_undo_done").replace("{count}", res.success_count || 0));
            await Promise.all([refreshHistory(), refreshStatus()]);
            if (currentPath !== null) await renderContent();
        } catch (err) {
            showStatus(err.message || t("status_undo_error"), true);
        } finally {
            btnHistoryUndoSelected.disabled = false;
        }
    });
}

// ---- gestion de papelera / cuarentena ----------------------------------------

const trashListEl = document.getElementById("trash-list");
const trashEmptyMsgEl = document.getElementById("trash-empty-msg");
const trashStatusTextEl = document.getElementById("trash-status-text");

async function refreshTrash() {
    if (!trashListEl) return;
    let data;
    try {
        data = await fetchJSON("/api/trash");
    } catch (err) {
        trashListEl.innerHTML = `<li class="empty">${t("trash_load_error")}</li>`;
        return;
    }

    if (trashStatusTextEl) {
        trashStatusTextEl.textContent = data.native ? (t("trash_native_active") || "Papelera nativa del sistema") : (t("trash_quarantine_active") || "Cuarentena local de Martix");
    }

    const items = data.items || [];
    trashListEl.innerHTML = "";

    if (items.length === 0) {
        if (trashEmptyMsgEl) trashEmptyMsgEl.hidden = false;
        return;
    } else {
        if (trashEmptyMsgEl) trashEmptyMsgEl.hidden = true;
    }

    for (const item of items) {
        const li = document.createElement("li");
        const dateStr = item.deleted_at ? formatDate(item.deleted_at) : "";
        const sizeStr = formatSize(item.size_bytes || 0);

        li.innerHTML = `
            <div class="settings-item-main">
                <strong>${escapeHtml(item.name)}</strong>
                <span class="muted">${escapeHtml(item.original_path || "")}</span>
                <span class="keywords">${sizeStr} &middot; ${dateStr}</span>
            </div>`;

        const actionContainer = document.createElement("div");
        actionContainer.style.display = "flex";
        actionContainer.style.gap = "6px";

        const restoreBtn = document.createElement("button");
        restoreBtn.className = "btn btn-small btn-quiet";
        restoreBtn.textContent = t("restore_item_btn") || "Restaurar";
        restoreBtn.addEventListener("click", async () => {
            restoreBtn.disabled = true;
            try {
                const res = await fetchJSON(`/api/trash/${item.id}/restore`, { method: "POST" });
                showStatus((t("status_trash_restored") || '"{filename}" restaurado.').replace("{filename}", item.name));
                await refreshTrash();
                if (currentPath !== null) await renderContent();
            } catch (err) {
                restoreBtn.disabled = false;
                showStatus(err.message || "Error al restaurar", true);
            }
        });

        const purgeBtn = document.createElement("button");
        purgeBtn.className = "btn btn-small btn-danger";
        purgeBtn.textContent = t("purge_item_btn") || "Eliminar";
        purgeBtn.addEventListener("click", async () => {
            purgeBtn.disabled = true;
            try {
                await fetchJSON(`/api/trash/${item.id}`, { method: "DELETE" });
                showStatus((t("status_trash_item_purged") || '"{filename}" eliminado.').replace("{filename}", item.name));
                await refreshTrash();
            } catch (err) {
                purgeBtn.disabled = false;
                showStatus(err.message || "Error al eliminar", true);
            }
        });

        actionContainer.appendChild(restoreBtn);
        actionContainer.appendChild(purgeBtn);
        li.appendChild(actionContainer);
        trashListEl.appendChild(li);
    }
}

const btnPurgeAllTrash = document.getElementById("btn-purge-all-trash");
if (btnPurgeAllTrash) {
    btnPurgeAllTrash.addEventListener("click", async () => {
        if (!confirm(t("confirm_purge_all_trash") || "¿Eliminar todo definitivamente?")) return;
        btnPurgeAllTrash.disabled = true;
        try {
            const res = await fetchJSON("/api/trash", { method: "DELETE" });
            showStatus((t("status_trash_purged") || "Papelera vaciada.").replace("{count}", res.purged || 0));
            await refreshTrash();
        } catch (err) {
            showStatus(err.message || "Error al vaciar papelera", true);
        } finally {
            btnPurgeAllTrash.disabled = false;
        }
    });
}

// ---- ajustes generales (duplicados) -------------------------------------------

const generalSettingsForm = document.getElementById("general-settings-form");
const duplicateActionSelect = document.getElementById("duplicate-action-select");
const cleanupModeSelect = document.getElementById("cleanup-mode-select");

async function refreshGeneralSettings() {
    try {
        const settings = await fetchJSON("/api/settings");
        duplicateActionSelect.value = settings.duplicate_action || "suffix";
        if (cleanupModeSelect) cleanupModeSelect.value = settings.cleanup_mode || "notify";
    } catch (err) {
        console.error("Error loading general settings:", err);
    }
}

if (generalSettingsForm) {
    generalSettingsForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const duplicate_action = duplicateActionSelect.value;
        const cleanup_mode = cleanupModeSelect ? cleanupModeSelect.value : "notify";
        try {
            await fetchJSON("/api/settings", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ duplicate_action, cleanup_mode })
            });
            showStatus(t("status_settings_saved"));
        } catch (err) {
            showStatus(err.message || t("status_settings_save_error"), true);
        }
    });
}

// ---- IA local (Ollama) ------------------------------------------------------

const aiUrlInput = document.getElementById("ai-url-input");
const aiModelInput = document.getElementById("ai-model-input");
const aiStatusBadge = document.getElementById("ai-status-badge");
const aiStatusText = document.getElementById("ai-status-text");
const btnTestAi = document.getElementById("btn-test-ai");

async function refreshAiSettings() {
    try {
        const status = await fetchJSON("/api/llm/status");
        aiUrlInput.value = status.url || aiUrlInput.value;
        aiModelInput.value = status.model || aiModelInput.value;
        aiStatusBadge.className = "status-pill " + (status.enabled ? "active" : "inactive");
        aiStatusBadge.title = status.reason || "";
        aiStatusText.textContent = status.enabled ? t("ai_status_enabled") : t("ai_status_disabled");
    } catch (err) {
        console.error("Error loading AI settings:", err);
    }
}

if (btnTestAi) {
    btnTestAi.addEventListener("click", async () => {
        const original = btnTestAi.textContent;
        btnTestAi.disabled = true;
        btnTestAi.textContent = t("ai_testing");
        try {
            const result = await fetchJSON("/api/llm/test", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ url: aiUrlInput.value.trim(), model: aiModelInput.value.trim() })
            });
            if (result.ok && result.model_found) {
                showStatus(t("ai_test_ok"));
            } else if (result.ok) {
                showStatus(t("ai_test_ok_no_model"), true);
            } else {
                showStatus(`${t("ai_test_fail")}: ${result.error || ""}`, true);
            }
        } catch (err) {
            showStatus(err.message || t("ai_test_fail"), true);
        } finally {
            btnTestAi.disabled = false;
            btnTestAi.textContent = original;
        }
    });
}

// ---- mantenimiento (reglas y limpieza) ---------------------------------------

async function refreshMaintenance() {
    try {
        const rules = await fetchJSON("/api/maintenance/rules");
        maintenanceListEl.innerHTML = "";
        if (rules.length === 0) {
            maintenanceListEl.innerHTML = `<li class="empty">${t("maintenance_empty")}</li>`;
            return;
        }
        for (const rule of rules) {
            const li = document.createElement("li");
            const folderName = rule.directory_path || rule.folder || rule.name;
            const maxAge = rule.max_age_days || rule.age_days;
            li.innerHTML = `<div class="settings-item-main">
                <strong>${escapeHtml(folderName)}</strong>
                <span class="muted">&rarr; ${maxAge} ${currentLang === "es" ? "días" : "days"}</span>
            </div>`;
            
            const delBtn = document.createElement("button");
            delBtn.className = "icon-btn danger";
            delBtn.innerHTML = svgIcon("trash");
            delBtn.title = t("delete_maintenance_rule_title");
            delBtn.addEventListener("click", async () => {
                try {
                    await fetchJSON(`/api/maintenance/rules/${rule.id}`, { method: "DELETE" });
                    await refreshMaintenance();
                    showStatus(t("status_maintenance_deleted"));
                } catch (err) {
                    showStatus(err.message || t("status_maintenance_delete_error"), true);
                }
            });
            li.appendChild(delBtn);
            maintenanceListEl.appendChild(li);
        }
    } catch (err) {
        console.error("Error refreshing maintenance rules:", err);
    }
}

if (maintenanceForm) {
    maintenanceForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const folder = document.getElementById("maintenance-folder").value.trim();
        const age = document.getElementById("maintenance-age").value.trim();
        if (!folder || !age) return;
        try {
            await fetchJSON("/api/maintenance/rules", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    folder: folder,
                    directory_path: folder,
                    max_age_days: parseInt(age, 10)
                }),
            });
            maintenanceForm.reset();
            await refreshMaintenance();
            showStatus(t("status_maintenance_saved"));
        } catch (err) {
            showStatus(err.message || t("status_maintenance_save_error"), true);
        }
    });
}

if (btnRunMaintenance) {
    btnRunMaintenance.addEventListener("click", async () => {
        btnRunMaintenance.disabled = true;
        showStatus(t("status_maintenance_running"));
        try {
            const data = await fetchJSON("/api/maintenance/run", { method: "POST" });
            const count = data.deleted !== undefined ? data.deleted : 0;
            showStatus(t("status_maintenance_run_done").replace("{count}", count));
        } catch (err) {
            showStatus(err.message || t("status_maintenance_run_error"), true);
        } finally {
            btnRunMaintenance.disabled = false;
        }
    });
}

// ---- carpetas vigiladas (multi-folder watch) --------------------------------

async function refreshWatchedFolders() {
    try {
        const folders = await fetchJSON("/api/watched-folders");
        watchedListEl.innerHTML = "";
        if (!folders || folders.length === 0) {
            watchedListEl.innerHTML = `<li class="empty">${t("watched_empty")}</li>`;
            return;
        }
        for (const folder of folders) {
            const li = document.createElement("li");
            const path = folder.folder_path || "";
            li.innerHTML = `<div class="settings-item-main">
                <strong>${escapeHtml(path)}</strong>
            </div>`;
            const delBtn = document.createElement("button");
            delBtn.className = "icon-btn danger";
            delBtn.innerHTML = svgIcon("trash");
            delBtn.title = t("delete_watched_title");
            delBtn.addEventListener("click", async () => {
                try {
                    await fetchJSON(`/api/watched-folders/${folder.id}`, { method: "DELETE" });
                    await refreshWatchedFolders();
                    showStatus(t("status_watched_deleted"));
                } catch (err) {
                    showStatus(err.message || t("status_watched_delete_error"), true);
                }
            });
            li.appendChild(delBtn);
            watchedListEl.appendChild(li);
        }
    } catch (err) {
        watchedListEl.innerHTML = `<li class="empty">${t("watched_empty")}</li>`;
    }
}

if (watchedForm) {
    watchedForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const path = document.getElementById("watched-folder-path").value.trim();
        if (!path) return;
        try {
            await fetchJSON("/api/watched-folders", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ folder_path: path }),
            });
            watchedForm.reset();
            await refreshWatchedFolders();
            showStatus(t("status_watched_saved"));
        } catch (err) {
            showStatus(err.message || t("status_watched_save_error"), true);
        }
    });
}

// ---- estadísticas (statistics dashboard) ------------------------------------

const CHART_COLORS = [
    "#77736c", "#918a7d", "#6e746f", "#9b8f7a", "#8a7770",
    "#7c8277", "#a09384", "#6b6e69", "#958d82", "#737975"
];

async function refreshStatistics() {
    const totalEl = document.getElementById("stats-total-count");
    const catChart = document.getElementById("stats-categories-chart");
    const actChart = document.getElementById("stats-activity-chart");
    if (!totalEl || !catChart || !actChart) return;

    try {
        const data = await fetchJSON("/api/statistics");

        // Total count
        const total = data.total_organized || 0;
        totalEl.textContent = total.toLocaleString();

        // Top categories bar chart
        const categories = data.by_category || [];
        catChart.innerHTML = "";
        if (categories.length === 0) {
            catChart.innerHTML = `<p class="hint">${t("stats_no_data")}</p>`;
        } else {
            const maxCount = Math.max(...categories.map(cat => cat.c || 0), 1);
            categories.forEach((cat, i) => {
                const name = cat.category || "";
                const count = cat.c || 0;
                const pct = Math.round((count / maxCount) * 100);
                const color = CHART_COLORS[i % CHART_COLORS.length];
                const row = document.createElement("div");
                row.className = "stats-bar-row";
                row.innerHTML = `
                    <span class="stats-bar-label">${escapeHtml(name)}</span>
                    <div class="stats-bar-track">
                        <div class="stats-bar-fill" style="width: ${safeNumber(pct)}%; background-color: ${safeColor(color)};"></div>
                    </div>
                    <span class="stats-bar-value">${count}</span>
                `;
                catChart.appendChild(row);
            });
        }

        // Activity chart (last 30 days)
        const activity = data.by_day || [];
        actChart.innerHTML = "";
        if (activity.length === 0) {
            actChart.innerHTML = `<p class="hint">${t("stats_no_data")}</p>`;
        } else {
            const maxDay = Math.max(...activity.map(d => d.c || 0), 1);
            const chart = document.createElement("div");
            chart.className = "stats-activity-bars";
            activity.forEach((day, i) => {
                const count = day.c || 0;
                const heightPct = Math.max(Math.round((count / maxDay) * 100), 2);
                const color = CHART_COLORS[i % CHART_COLORS.length];
                const bar = document.createElement("div");
                bar.className = "stats-day-bar";
                bar.title = `${day.day || ""}: ${count}`;
                bar.innerHTML = `<div class="stats-day-fill" style="height: ${safeNumber(heightPct)}%; background-color: ${safeColor(color)};"></div>`;
                chart.appendChild(bar);
            });
            actChart.appendChild(chart);

            // Date labels (first, middle, last)
            if (activity.length >= 2) {
                const labels = document.createElement("div");
                labels.className = "stats-activity-labels";
                const firstDate = activity[0].day || "";
                const lastDate = activity[activity.length - 1].day || "";
                labels.innerHTML = `<span>${escapeHtml(firstDate)}</span><span>${escapeHtml(lastDate)}</span>`;
                actChart.appendChild(labels);
            }
        }
    } catch (err) {
        if (totalEl) totalEl.textContent = "–";
        if (catChart) catChart.innerHTML = `<p class="hint">${t("stats_load_error")}</p>`;
        if (actChart) actChart.innerHTML = "";
    }
}

// ---- deduplicación (buscar y limpiar duplicados) ----------------------------

let duplicateGroups = [];

async function scanDuplicates() {
    const spinner = document.getElementById("duplicates-loading");
    const container = document.getElementById("duplicates-container");
    const listEl = document.getElementById("duplicates-list");
    const emptyMsg = document.getElementById("duplicates-empty-msg");
    const btnAutoSelect = document.getElementById("btn-auto-select-duplicates");
    const btnClean = document.getElementById("btn-clean-duplicates");

    if (!spinner || !container || !listEl || !emptyMsg) return;

    spinner.style.display = "block";
    listEl.style.display = "none";
    emptyMsg.style.display = "none";
    if (btnAutoSelect) btnAutoSelect.disabled = true;
    if (btnClean) btnClean.disabled = true;

    try {
        const folderInput = document.getElementById("duplicates-folder-input");
        const folderVal = (folderInput ? folderInput.value : "").strip ? folderInput.value.strip() : (folderInput ? folderInput.value.trim() : "");
        if (folderVal) {
            const dirs = folderVal.split(",").map(s => s.trim()).filter(Boolean);
            duplicateGroups = await fetchJSON("/api/duplicates", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ directories: dirs }),
            });
        } else {
            duplicateGroups = await fetchJSON("/api/duplicates");
        }
        listEl.innerHTML = "";

        if (duplicateGroups.length === 0) {
            emptyMsg.style.display = "block";
        } else {
            duplicateGroups.forEach((groupObj, groupIdx) => {
                let files = [];
                let sizeBytes = 0;
                if (groupObj && Array.isArray(groupObj)) {
                    files = groupObj;
                    sizeBytes = files[0]?.size || 0;
                } else if (groupObj && groupObj.files && Array.isArray(groupObj.files)) {
                    files = groupObj.files;
                    sizeBytes = groupObj.size_bytes || files[0]?.size || 0;
                }

                if (files.length === 0) return;

                const groupDiv = document.createElement("div");
                groupDiv.className = "duplicates-group";

                const header = document.createElement("div");
                header.className = "duplicates-group-header";
                
                const groupSizeStr = formatSize(sizeBytes);
                const groupTitle = currentLang === "es" 
                    ? `Grupo ${groupIdx + 1} (${groupSizeStr} cada uno)` 
                    : `Group ${groupIdx + 1} (${groupSizeStr} each)`;
                
                header.innerHTML = `<strong>${groupTitle}</strong>`;
                groupDiv.appendChild(header);

                const itemsList = document.createElement("div");
                itemsList.className = "duplicates-group-list";

                files.forEach((file) => {
                    const item = document.createElement("div");
                    item.className = "duplicates-item";

                    const cb = document.createElement("input");
                    cb.type = "checkbox";
                    cb.className = "duplicates-item-checkbox";
                    cb.dataset.path = file.path;
                    cb.addEventListener("change", updateCleanButtonState);

                    const details = document.createElement("div");
                    details.className = "duplicates-item-details";
                    
                    let formattedTime = file.mtime;
                    if (formattedTime) {
                        try {
                            const date = new Date(formattedTime);
                            formattedTime = date.toLocaleString(undefined, { dateStyle: "short", timeStyle: "short" });
                        } catch (e) {}
                    }

                    details.innerHTML = `
                        <span class="duplicates-item-name">${escapeHtml(file.name)}</span>
                        <span class="duplicates-item-path">${escapeHtml(file.path)}</span>
                        <span class="duplicates-item-meta">${formatSize(sizeBytes)} &middot; ${escapeHtml(formattedTime)}</span>
                    `;

                    item.appendChild(cb);
                    item.appendChild(details);
                    itemsList.appendChild(item);
                });

                groupDiv.appendChild(itemsList);
                listEl.appendChild(groupDiv);
            });
            listEl.style.display = "flex";
            if (btnAutoSelect) btnAutoSelect.disabled = false;
        }
    } catch (err) {
        showStatus(t("status_scanning_error"), true);
        emptyMsg.textContent = t("status_scanning_error");
        emptyMsg.style.display = "block";
    } finally {
        spinner.style.display = "none";
    }
}

function updateCleanButtonState() {
    const btnClean = document.getElementById("btn-clean-duplicates");
    if (!btnClean) return;
    const checkedBoxes = document.querySelectorAll(".duplicates-item-checkbox:checked");
    btnClean.disabled = checkedBoxes.length === 0;
}

function autoSelectDuplicates() {
    const groups = document.querySelectorAll(".duplicates-group");
    groups.forEach((group) => {
        const checkboxes = group.querySelectorAll(".duplicates-item-checkbox");
        checkboxes.forEach((cb, idx) => {
            cb.checked = idx > 0;
        });
    });
    updateCleanButtonState();
}

async function cleanSelectedDuplicates() {
    const btnClean = document.getElementById("btn-clean-duplicates");
    const checkedBoxes = document.querySelectorAll(".duplicates-item-checkbox:checked");
    if (checkedBoxes.length === 0) return;

    const filesToDelete = Array.from(checkedBoxes).map(cb => cb.dataset.path);
    
    if (btnClean) btnClean.disabled = true;
    showStatus(currentLang === "es" ? "Eliminando duplicados..." : "Deleting duplicates...");

    try {
        const res = await fetchJSON("/api/duplicates/clean", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ files: filesToDelete }),
        });
        
        const count = res.deleted !== undefined ? res.deleted : (res.cleaned !== undefined ? res.cleaned : filesToDelete.length);
        showStatus(t("status_cleaning_done").replace("{count}", count));
        await scanDuplicates();
    } catch (err) {
        showStatus(t("status_cleaning_error"), true);
        if (btnClean) btnClean.disabled = false;
    }
}

// ---- modal de ajustes --------------------------------------------------------

const settingsBtnIcon = document.getElementById("settings-btn-icon");
if (settingsBtnIcon) settingsBtnIcon.innerHTML = svgIcon("settings");
const closeSettingsBtn = document.getElementById("btn-close-settings");
if (closeSettingsBtn) closeSettingsBtn.innerHTML = svgIcon("close");

document.getElementById("btn-settings").addEventListener("click", () => openSettings());
document.getElementById("btn-close-settings").addEventListener("click", () => settingsModal.close());

const btnScan = document.getElementById("btn-scan-duplicates");
if (btnScan) btnScan.addEventListener("click", scanDuplicates);

const btnAutoSelect = document.getElementById("btn-auto-select-duplicates");
if (btnAutoSelect) btnAutoSelect.addEventListener("click", autoSelectDuplicates);

const btnClean = document.getElementById("btn-clean-duplicates");
if (btnClean) btnClean.addEventListener("click", cleanSelectedDuplicates);

for (const tabBtn of document.querySelectorAll(".tab-btn")) {
    tabBtn.addEventListener("click", () => {
        for (const b of document.querySelectorAll(".tab-btn")) b.classList.remove("active");
        for (const p of document.querySelectorAll(".tab-panel")) p.hidden = true;
        tabBtn.classList.add("active");
        document.getElementById(`tab-${tabBtn.dataset.tab}`).hidden = false;
        if (tabBtn.dataset.tab === "history") refreshHistory();
        if (tabBtn.dataset.tab === "general") refreshGeneralSettings();
        if (tabBtn.dataset.tab === "maintenance") refreshMaintenance();
        if (tabBtn.dataset.tab === "trash") refreshTrash();
        if (tabBtn.dataset.tab === "watched") refreshWatchedFolders();
        if (tabBtn.dataset.tab === "stats") refreshStatistics();
        if (tabBtn.dataset.tab === "ai") refreshAiSettings();
    });
}

async function exportRules() {
    try {
        const data = await fetchJSON("/api/rules/export");
        const jsonStr = JSON.stringify(data, null, 2);
        const blob = new Blob([jsonStr], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "martix_rules.json";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        showStatus(t("status_rules_exported"));
    } catch (err) {
        showStatus(t("status_export_error"), true);
    }
}

async function importRules(file) {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async (e) => {
        try {
            const parsed = JSON.parse(e.target.result);
            await fetchJSON("/api/rules/import", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(parsed),
            });
            showStatus(t("status_rules_imported"));
            refreshRules();
            refreshMaintenance();
        } catch (err) {
            showStatus(t("status_import_error"), true);
        }
    };
    reader.readAsText(file);
}

const btnExportRules = document.getElementById("btn-export-rules");
if (btnExportRules) btnExportRules.addEventListener("click", exportRules);

const btnImportRules = document.getElementById("btn-import-rules");
const fileInputImport = document.getElementById("import-rules-file");
if (btnImportRules && fileInputImport) {
    btnImportRules.addEventListener("click", () => fileInputImport.click());
    fileInputImport.addEventListener("change", (e) => {
        if (e.target.files && e.target.files[0]) {
            importRules(e.target.files[0]);
            fileInputImport.value = "";
        }
    });
}

function openSettings(tab) {
    if (tab) {
        document.querySelector(`.tab-btn[data-tab="${tab}"]`)?.click();
    }
    settingsModal.showModal();
}

// ---- Onboarding Welcome Modal Controller ----------------------------------
const welcomeModal = document.getElementById("welcome-modal");
const btnCloseWelcome = document.getElementById("btn-close-welcome");
const btnHelp = document.getElementById("btn-help");
const btnOnboardPrev = document.getElementById("btn-onboard-prev");
const btnOnboardNext = document.getElementById("btn-onboard-next");
const btnOnboardFinish = document.getElementById("btn-onboard-finish");

let currentOnboardSlide = 1;
const totalOnboardSlides = 4;

function setOnboardSlide(step) {
    currentOnboardSlide = step;
    const badge = document.getElementById("onboard-step-badge");
    if (badge) {
        badge.textContent = t("step_prefix", "Paso {step} de 4").replace("{step}", step);
    }
    document.querySelectorAll(".onboard-slide").forEach(s => {
        const isCurrent = parseInt(s.dataset.slide, 10) === step;
        s.style.display = isCurrent ? "flex" : "none";
        s.classList.toggle("active", isCurrent);
    });
    document.querySelectorAll(".slide-dots .dot").forEach(d => {
        d.classList.toggle("active", parseInt(d.dataset.step, 10) === step);
    });
    if (btnOnboardPrev) btnOnboardPrev.disabled = (step === 1);
    if (btnOnboardNext) btnOnboardNext.style.display = (step === totalOnboardSlides ? "none" : "inline-flex");
    if (btnOnboardFinish) btnOnboardFinish.style.display = (step === totalOnboardSlides ? "inline-flex" : "none");
}

function markOnboarded() {
    localStorage.setItem("martix_onboarded", "1");
    localStorage.setItem("sortix_onboarded", "1");
    fetch("/api/settings", withToken({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ onboarded: true })
    })).catch(() => {});
}

function openWelcomeModal() {
    setOnboardSlide(1);
    markOnboarded();
    if (welcomeModal) {
        welcomeModal.showModal();
        if (btnCloseWelcome) btnCloseWelcome.blur();
        if (btnOnboardNext) btnOnboardNext.focus();
    }
}

if (welcomeModal) {
    welcomeModal.addEventListener("close", markOnboarded);
    welcomeModal.addEventListener("cancel", markOnboarded);
}

if (btnHelp) btnHelp.addEventListener("click", openWelcomeModal);
if (btnCloseWelcome) btnCloseWelcome.addEventListener("click", () => {
    markOnboarded();
    if (welcomeModal) welcomeModal.close();
});
if (btnOnboardPrev) btnOnboardPrev.addEventListener("click", () => {
    if (currentOnboardSlide > 1) setOnboardSlide(currentOnboardSlide - 1);
});
if (btnOnboardNext) btnOnboardNext.addEventListener("click", () => {
    if (currentOnboardSlide < totalOnboardSlides) setOnboardSlide(currentOnboardSlide + 1);
});
if (btnOnboardFinish) btnOnboardFinish.addEventListener("click", () => {
    markOnboarded();
    if (welcomeModal) welcomeModal.close();
});

document.querySelectorAll(".slide-dots .dot").forEach(dot => {
    dot.addEventListener("click", () => {
        const step = parseInt(dot.dataset.step, 10);
        if (step) setOnboardSlide(step);
    });
});

// ---- arranque ------------------------------------------------------------

const langSelect = document.getElementById("lang-select");
if (langSelect) {
    langSelect.addEventListener("change", async (e) => {
        currentLang = e.target.value;
        localStorage.setItem("martix_lang", currentLang);
        applyLanguage();
        await Promise.all([refreshTopics(), refreshRules(), refreshMaintenance(), refreshWatchedFolders(), loadTree()]);
        renderBreadcrumbs();
        await renderContent();
    });
}

const themeBtn = document.getElementById("btn-theme");
if (themeBtn) {
    themeBtn.addEventListener("click", toggleTheme);
}

// ---- Zoom controller (Ctrl + Wheel, Ctrl + / - / 0) ---------------------
let zoomScale = parseFloat(localStorage.getItem("martix_zoom") || localStorage.getItem("sortix_zoom") || "1.0");

function setZoom(scale) {
    zoomScale = Math.min(Math.max(scale, 0.7), 1.8);
    localStorage.setItem("martix_zoom", zoomScale.toString());
    document.body.style.zoom = zoomScale;
}

window.addEventListener("wheel", (e) => {
    if (e.ctrlKey || e.metaKey) {
        e.preventDefault();
        setZoom(zoomScale + (e.deltaY < 0 ? 0.06 : -0.06));
    }
}, { passive: false });

window.addEventListener("keydown", (e) => {
    if (e.ctrlKey || e.metaKey) {
        if (e.key === "+" || e.key === "=") {
            e.preventDefault();
            setZoom(zoomScale + 0.1);
        } else if (e.key === "-") {
            e.preventDefault();
            setZoom(zoomScale - 0.1);
        } else if (e.key === "0") {
            e.preventDefault();
            setZoom(1.0);
        }
    }
});

/* ==========================================================================
   DISK SPACE ANALYZER MODULE
   ========================================================================== */
let diskAnalyzerData = null;
let diskAnalyzerSelectedItem = null;
let treemapRects = [];

const diskAnalyzerModal = document.getElementById("disk-analyzer-modal");
const btnDiskAnalyzer = document.getElementById("btn-disk-analyzer");
const btnCloseDiskAnalyzer = document.getElementById("btn-close-disk-analyzer");
const btnCloseDiskAnalyzerFooter = document.getElementById("btn-disk-analyzer-close-footer");
const btnDiskAnalyzerScan = document.getElementById("btn-disk-analyzer-scan");
const diskAnalyzerDriveSelect = document.getElementById("disk-analyzer-drive-select");
const diskAnalyzerPathInput = document.getElementById("disk-analyzer-path-input");
const diskAnalyzerTreeBody = document.getElementById("disk-analyzer-tree-body");
const diskAnalyzerExtBody = document.getElementById("disk-analyzer-ext-body");
const diskAnalyzerTreeFilter = document.getElementById("disk-analyzer-tree-filter");
const diskAnalyzerCanvas = document.getElementById("disk-analyzer-treemap-canvas");
const diskAnalyzerHoverInfo = document.getElementById("disk-analyzer-selected-hover-info");
const diskAnalyzerFooterInfo = document.getElementById("disk-analyzer-footer-info");
const btnDiskAnalyzerDelete = document.getElementById("btn-disk-analyzer-delete");

async function openDiskAnalyzerModal() {
    if (!diskAnalyzerModal) return;
    diskAnalyzerModal.showModal();
    await loadDiskAnalyzerDrives();
    runDiskAnalyzerScan();
}

function closeDiskAnalyzerModal() {
    if (diskAnalyzerModal && diskAnalyzerModal.open) {
        diskAnalyzerModal.close();
    }
}

async function loadDiskAnalyzerDrives() {
    if (!diskAnalyzerDriveSelect) return;
    try {
        const res = await fetch("/api/disk/drives", withToken());
        if (res.ok) {
            const drives = await res.json();
            diskAnalyzerDriveSelect.innerHTML = drives.map(d => `<option value="${escapeHtml(d.path)}">${escapeHtml(d.name)} (${escapeHtml(d.path)})</option>`).join("");
            if (drives.length > 0 && diskAnalyzerPathInput && !diskAnalyzerPathInput.value) {
                diskAnalyzerPathInput.value = drives[0].path;
            }
        }
    } catch (e) {
        console.error("Error cargando unidades:", e);
    }
}

if (diskAnalyzerDriveSelect) {
    diskAnalyzerDriveSelect.addEventListener("change", (e) => {
        if (diskAnalyzerPathInput) diskAnalyzerPathInput.value = e.target.value;
        runDiskAnalyzerScan();
    });
}

async function runDiskAnalyzerScan() {
    const scanPath = (diskAnalyzerPathInput ? diskAnalyzerPathInput.value : "").trim();
    const statusElem = document.getElementById("disk-analyzer-scan-status");
    if (statusElem) statusElem.textContent = t("disk_analyzer_scanning_status");
    if (diskAnalyzerTreeBody) diskAnalyzerTreeBody.innerHTML = `<tr><td colspan="7" class="disk-analyzer-empty-cell">${t("disk_analyzer_scanning_tree")}</td></tr>`;
    if (diskAnalyzerExtBody) diskAnalyzerExtBody.innerHTML = `<tr><td colspan="4" class="disk-analyzer-empty-cell">${t("disk_analyzer_scanning_ext")}</td></tr>`;

    try {
        const res = await fetch("/api/disk/scan", withToken({
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ path: scanPath })
        }));

        if (!res.ok) {
            const err = await res.json();
            if (statusElem) statusElem.textContent = `Error: ${err.error || t("disk_analyzer_scan_error")}`;
            return;
        }

        diskAnalyzerData = await res.json();
        renderDiskAnalyzerSummary();
        renderDiskAnalyzerTree();
        renderDiskAnalyzerExtensions();
        renderDiskAnalyzerTreemap();
    } catch (e) {
        console.error("Error al ejecutar escaneo de espacio:", e);
        if (statusElem) statusElem.textContent = t("disk_analyzer_scan_error");
    }
}

function renderDiskAnalyzerSummary() {
    if (!diskAnalyzerData) return;
    const statusElem = document.getElementById("disk-analyzer-scan-status");
    if (statusElem) {
        // El backend acota el escaneo por tiempo: si lo corta, hay que decirlo
        // en vez de presentar totales incompletos como si fueran definitivos.
        statusElem.textContent = diskAnalyzerData.truncated
            ? `${t("disk_scan_truncated")} (${diskAnalyzerData.scan_time_seconds} s)`
            : t("disk_analyzer_scan_done").replace("{s}", diskAnalyzerData.scan_time_seconds);
        statusElem.classList.toggle("warning", Boolean(diskAnalyzerData.truncated));
    }
    
    const totalSpaceElem = document.getElementById("disk-analyzer-total-space");
    if (totalSpaceElem) totalSpaceElem.textContent = diskAnalyzerData.disk_info.total_space_formatted || "--";
    
    const usedSpaceElem = document.getElementById("disk-analyzer-used-space");
    if (usedSpaceElem) usedSpaceElem.textContent = `${diskAnalyzerData.disk_info.used_space_formatted} (${diskAnalyzerData.disk_info.used_percent}%)`;
    const usedBar = document.getElementById("disk-analyzer-used-bar");
    if (usedBar) usedBar.style.width = `${diskAnalyzerData.disk_info.used_percent}%`;

    const freeSpaceElem = document.getElementById("disk-analyzer-free-space");
    if (freeSpaceElem) freeSpaceElem.textContent = `${diskAnalyzerData.disk_info.free_space_formatted} (${diskAnalyzerData.disk_info.free_percent}%)`;
    const freeBar = document.getElementById("disk-analyzer-free-bar");
    if (freeBar) freeBar.style.width = `${diskAnalyzerData.disk_info.free_percent}%`;
}

function renderDiskAnalyzerTree() {
    if (!diskAnalyzerData || !diskAnalyzerData.tree || !diskAnalyzerTreeBody) return;
    const filterText = (diskAnalyzerTreeFilter ? diskAnalyzerTreeFilter.value : "").toLowerCase().trim();
    diskAnalyzerTreeBody.innerHTML = "";

    function renderNode(node, depth = 0) {
        if (filterText && !node.name.toLowerCase().includes(filterText)) {
            const childMatch = (node.children || []).some(c => c.name.toLowerCase().includes(filterText));
            if (!childMatch) return;
        }

        const tr = document.createElement("tr");
        tr.dataset.path = node.path;
        tr.dataset.isDir = node.is_dir ? "true" : "false";

        const indentPx = depth * 16;
        const iconSvg = node.is_dir ?
            `<svg class="disk-analyzer-icon-folder" width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M10 4H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-8l-2-2z"/></svg>` :
            `<svg class="disk-analyzer-icon-file" width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9l-5-7z"/></svg>`;

        const expanderBtn = node.is_dir && node.children && node.children.length > 0 ?
            `<span class="disk-analyzer-expander">▼</span>` : `<span class="disk-analyzer-tree-indent"></span>`;

        tr.innerHTML = `
            <td>
                <div class="disk-analyzer-cell-name" style="padding-left: ${safeNumber(indentPx)}px">
                    ${expanderBtn}
                    ${iconSvg}
                    <span title="${escapeHtml(node.path)}">${escapeHtml(node.name)}</span>
                </div>
            </td>
            <td>
                <div class="disk-analyzer-bar-cell">
                    <div class="disk-analyzer-bar-mini">
                        <div class="disk-analyzer-bar-mini-fill" style="width: ${safeNumber(node.percent_of_parent)}%;"></div>
                    </div>
                    <span>${safeNumber(node.percent_of_parent)}%</span>
                </div>
            </td>
            <td><strong>${escapeHtml(node.size_formatted)}</strong></td>
            <td>${node.items_count !== undefined ? node.items_count.toLocaleString() : "--"}</td>
            <td>${node.files_count !== undefined ? node.files_count.toLocaleString() : "--"}</td>
            <td>${node.folders_count !== undefined ? node.folders_count.toLocaleString() : "--"}</td>
            <td>${escapeHtml(node.mtime || "--")}</td>
        `;

        tr.addEventListener("click", () => {
            selectDiskAnalyzerItem(node);
            document.querySelectorAll("#disk-analyzer-tree-body tr").forEach(r => r.classList.remove("selected"));
            tr.classList.add("selected");
        });

        diskAnalyzerTreeBody.appendChild(tr);

        if (depth < 2 && node.children) {
            node.children.forEach(child => renderNode(child, depth + 1));
        }
    }

    renderNode(diskAnalyzerData.tree, 0);
}

function renderDiskAnalyzerExtensions() {
    if (!diskAnalyzerData || !diskAnalyzerData.extensions || !diskAnalyzerExtBody) return;
    diskAnalyzerExtBody.innerHTML = diskAnalyzerData.extensions.map(ext => `
        <tr>
            <td>
                <div class="disk-analyzer-cell-name">
                    <strong>${escapeHtml(ext.extension)}</strong>
                </div>
            </td>
            <td>${escapeHtml(ext.type_name)}</td>
            <td><strong>${escapeHtml(ext.size_formatted)}</strong></td>
            <td>
                <div class="disk-analyzer-bar-cell">
                    <div class="disk-analyzer-bar-mini">
                        <div class="disk-analyzer-bar-mini-fill" style="width: ${safeNumber(ext.percent)}%;"></div>
                    </div>
                    <span>${safeNumber(ext.percent)}%</span>
                </div>
            </td>
        </tr>
    `).join("");
}

// ---- True Squarified Treemap Layout Engine ----
function renderDiskAnalyzerTreemap() {
    if (!diskAnalyzerCanvas || !diskAnalyzerData || !diskAnalyzerData.treemap) return;
    const container = diskAnalyzerCanvas.parentElement;
    const width = container.clientWidth || 800;
    const height = container.clientHeight || 300;
    
    diskAnalyzerCanvas.width = width;
    diskAnalyzerCanvas.height = height;
    
    const ctx = diskAnalyzerCanvas.getContext("2d");
    ctx.clearRect(0, 0, width, height);

    treemapRects = [];
    const items = diskAnalyzerData.treemap;
    if (items.length === 0) return;

    const maxSize = Math.max(...items.map(it => Number(it.size) || 0), 1);
    const darkUi = document.documentElement.classList.contains("dark");

    function tileTone(item) {
        const weight = Math.sqrt(Math.max(Number(item.size) || 0, 0) / maxSize);
        const light = darkUi ? 18 + weight * 26 : 78 - weight * 32;
        return { light, fill: `hsl(32 12% ${light}%)` };
    }

    function squarify(rects, x, y, w, h) {
        if (rects.length === 0 || w <= 2 || h <= 2) return;
        if (rects.length === 1) {
            treemapRects.push({ x, y, w, h, item: rects[0] });
            return;
        }

        const total = rects.reduce((sum, r) => sum + r.size, 0);
        if (total <= 0) return;

        let half = 0;
        let splitIdx = 0;
        for (let i = 0; i < rects.length; i++) {
            half += rects[i].size;
            splitIdx = i;
            if (half >= total / 2) break;
        }

        const group1 = rects.slice(0, splitIdx + 1);
        const group2 = rects.slice(splitIdx + 1);

        const group1Size = group1.reduce((s, r) => s + r.size, 0);
        const ratio = group1Size / total;

        if (w >= h) {
            const g1W = Math.round(w * ratio);
            const g2W = w - g1W;
            squarify(group1, x, y, g1W, h);
            squarify(group2, x + g1W, y, g2W, h);
        } else {
            const g1H = Math.round(h * ratio);
            const g2H = h - g1H;
            squarify(group1, x, y, w, g1H);
            squarify(group2, x, y + g1H, w, g2H);
        }
    }

    squarify(items, 0, 0, width, height);

    treemapRects.forEach((r, idx) => {
        const gap = 2;
        const rx = r.x + gap;
        const ry = r.y + gap;
        const rw = Math.max(1, r.w - gap * 2);
        const rh = Math.max(1, r.h - gap * 2);

        const tone = tileTone(r.item);
        ctx.fillStyle = tone.fill;
        ctx.beginPath();
        if (ctx.roundRect) {
            ctx.roundRect(rx, ry, rw, rh, 5);
        } else {
            ctx.rect(rx, ry, rw, rh);
        }
        ctx.fill();

        ctx.strokeStyle = darkUi ? "rgba(255,255,255,0.12)" : "rgba(255,255,255,0.45)";
        ctx.lineWidth = 1;
        ctx.stroke();

        if (rw > 40 && rh > 18) {
            const ink = tone.light > 48 ? "rgba(28,24,20,0.88)" : "rgba(252,248,244,0.92)";
            ctx.fillStyle = ink;
            ctx.font = "600 11px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
            ctx.shadowBlur = 0;

            const maxChars = Math.floor(rw / 7);
            let nameStr = r.item.name;
            if (nameStr.length > maxChars) nameStr = nameStr.substring(0, Math.max(2, maxChars - 2)) + "..";

            ctx.fillText(nameStr, rx + 7, ry + 16);

            if (rh > 34 && rw > 60) {
                ctx.font = "500 10px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
                ctx.globalAlpha = 0.72;
                ctx.fillText(r.item.size_formatted, rx + 7, ry + 30);
                ctx.globalAlpha = 1;
            }
        }
    });
}

if (diskAnalyzerCanvas) {
    diskAnalyzerCanvas.addEventListener("mousemove", (e) => {
        const rect = diskAnalyzerCanvas.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;

        const found = treemapRects.find(r => mouseX >= r.x && mouseX <= r.x + r.w && mouseY >= r.y && mouseY <= r.y + r.h);
        if (found && diskAnalyzerHoverInfo) {
            diskAnalyzerHoverInfo.textContent = `${found.item.name} (${found.item.size_formatted}) — ${found.item.path}`;
        }
    });

    diskAnalyzerCanvas.addEventListener("click", (e) => {
        const rect = diskAnalyzerCanvas.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;

        const found = treemapRects.find(r => mouseX >= r.x && mouseX <= r.x + r.w && mouseY >= r.y && mouseY <= r.y + r.h);
        if (found) {
            selectDiskAnalyzerItem(found.item);
            const treeRow = document.querySelector(`#disk-analyzer-tree-body tr[data-path="${CSS.escape(found.item.path)}"]`);
            if (treeRow) {
                document.querySelectorAll("#disk-analyzer-tree-body tr").forEach(r => r.classList.remove("selected"));
                treeRow.classList.add("selected");
                treeRow.scrollIntoView({ behavior: "smooth", block: "center" });
            }
        }
    });
}

function selectDiskAnalyzerItem(item) {
    diskAnalyzerSelectedItem = item;
    if (diskAnalyzerFooterInfo) {
        diskAnalyzerFooterInfo.innerHTML = `<strong>${escapeHtml(t("disk_analyzer_selected"))}:</strong> ${escapeHtml(item.name)} (${item.size_formatted || formatBytes(item.size)}) — <code>${escapeHtml(item.path)}</code>`;
    }
    if (btnDiskAnalyzerDelete) {
        btnDiskAnalyzerDelete.disabled = false;
    }
}

if (btnDiskAnalyzerDelete) {
    btnDiskAnalyzerDelete.addEventListener("click", async () => {
        if (!diskAnalyzerSelectedItem) return;
        const targetPath = diskAnalyzerSelectedItem.path;
        if (!confirm(t("disk_analyzer_confirm_delete").replace("{path}", targetPath))) {
            return;
        }

        try {
            const deletedName = diskAnalyzerSelectedItem.name;
            const postDelete = async (confirm) => await fetch("/api/disk/delete", withToken({
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ path: targetPath, confirm })
            }));

            let res = await postDelete(false);

            // El backend exige confirmacion explicita para carpetas con muchos
            // archivos: un clic accidental no puede vaciar una carpeta entera.
            if (res.status === 409) {
                const info = await res.json();
                if (info.needs_confirmation) {
                    const msg = t("confirm_delete_folder").replace("{n}", info.file_count);
                    if (!window.confirm(msg)) return;
                    res = await postDelete(true);
                }
            }

            if (res.ok) {
                showStatus(`${t("status_moved_to_trash")}: ${deletedName}`);
                diskAnalyzerSelectedItem = null;
                btnDiskAnalyzerDelete.disabled = true;
                if (diskAnalyzerFooterInfo) diskAnalyzerFooterInfo.textContent = t("disk_analyzer_no_selection");
                runDiskAnalyzerScan();
            } else {
                const err = await res.json().catch(() => ({}));
                alert(`Error al eliminar: ${err.error || res.status}`);
            }
        } catch (e) {
            alert(`Error de red al eliminar: ${e}`);
        }
    });
}

if (btnDiskAnalyzer) btnDiskAnalyzer.addEventListener("click", openDiskAnalyzerModal);
if (btnCloseDiskAnalyzer) btnCloseDiskAnalyzer.addEventListener("click", closeDiskAnalyzerModal);
if (btnCloseDiskAnalyzerFooter) btnCloseDiskAnalyzerFooter.addEventListener("click", closeDiskAnalyzerModal);
if (btnDiskAnalyzerScan) btnDiskAnalyzerScan.addEventListener("click", runDiskAnalyzerScan);
if (diskAnalyzerTreeFilter) diskAnalyzerTreeFilter.addEventListener("input", renderDiskAnalyzerTree);

if (diskAnalyzerModal) {
    diskAnalyzerModal.addEventListener("cancel", (e) => {
        e.preventDefault();
        closeDiskAnalyzerModal();
    });
    diskAnalyzerModal.addEventListener("click", (e) => {
        if (e.target === diskAnalyzerModal) {
            closeDiskAnalyzerModal();
        }
    });
}

async function checkAppUpdates() {
    try {
        const res = await fetch("/api/update/check", withToken());
        if (res.ok) {
            const data = await res.json();
            const btnUpdate = document.getElementById("btn-update-check");
            if (btnUpdate) {
                if (data.update_available) {
                    btnUpdate.classList.remove("hidden");
                } else {
                    btnUpdate.classList.add("hidden");
                }
            }
        }
    } catch (e) {
        console.warn("Error comprobando actualizaciones:", e);
    }
}

const btnUpdateCheck = document.getElementById("btn-update-check");
if (btnUpdateCheck) {
    btnUpdateCheck.addEventListener("click", async () => {
        if (confirm(t("update_confirm_dialog"))) {
            try {
                showStatus(t("status_updating"));
                const res = await fetch("/api/update/apply", withToken({ method: "POST", headers: { "Content-Type": "application/json" } }));
                if (res.ok) {
                    showStatus(t("status_updating"));
                    setTimeout(() => { location.reload(); }, 4000);
                }
            } catch (e) {
                alert("Error al iniciar actualización: " + e);
            }
        }
    });
}

async function init() {
    applyLanguage();
    updateThemeButton();
    if (zoomScale !== 1.0) setZoom(zoomScale);

    let isAlreadyOnboarded = !!(localStorage.getItem("martix_onboarded") || localStorage.getItem("sortix_onboarded"));

    try {
        const settingsRes = await fetch("/api/settings", withToken());
        if (settingsRes.ok) {
            const settingsData = await settingsRes.json();
            if (settingsData.onboarded) {
                isAlreadyOnboarded = true;
                localStorage.setItem("martix_onboarded", "1");
            }
        }
    } catch (e) {}

    await Promise.all([refreshStatus(), refreshCleanupSuggestions(), loadTree(), refreshTopics(), refreshRules(), refreshGeneralSettings(), refreshMaintenance(), refreshWatchedFolders()]);
    renderBreadcrumbs();
    await renderContent();
    checkAppUpdates();
    setInterval(refreshStatus, 5000);
    setInterval(refreshCleanupSuggestions, 15000);
    setInterval(checkAppUpdates, 60000);

    if (!isAlreadyOnboarded) {
        openWelcomeModal();
    }
}

init();

