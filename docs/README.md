# Documentación de Martix

## Por dónde empezar

| Si quieres… | Lee |
|---|---|
| Instalar y usar Martix | [README del proyecto](../README.md) |
| Entender cómo funciona por dentro | [arquitectura.md](arquitectura.md) |
| Saber de qué se defiende y cómo | [seguridad.md](seguridad.md) |
| Ajustar su comportamiento | [configuracion.md](configuracion.md) |
| Integrarte con la API | [api.md](api.md) |
| Contribuir código | [desarrollo.md](desarrollo.md) y [CONTRIBUTING.md](../CONTRIBUTING.md) |

## Todos los documentos

### Cómo funciona

- **[arquitectura.md](arquitectura.md)** — Módulos, flujo completo de un
  archivo desde que aparece en Descargas hasta que queda archivado, modelo de
  datos, concurrencia y cómo extenderlo.
- **[api.md](api.md)** — Referencia de los 40+ endpoints REST, con los formatos
  de petición y los códigos de error.
- **[configuracion.md](configuracion.md)** — Variables de entorno, categorías,
  ajustes de la interfaz y dependencias opcionales.

### Seguridad

- **[seguridad.md](seguridad.md)** — Modelo de amenazas, defensas por vector,
  riesgos aceptados y recomendaciones de despliegue.
- **[SECURITY.md](../SECURITY.md)** — Cómo reportar una vulnerabilidad.

### Historia y decisiones

- **[decisiones.md](decisiones.md)** — Registro de decisiones de arquitectura
  (ADR): el contexto, la decisión y lo que costó.
- **[auditoria-2026-07.md](auditoria-2026-07.md)** — La auditoría de julio de
  2026: 16 bugs y 2 vulnerabilidades explotables, cómo se encontraron y cómo se
  cerraron.
- **[CHANGELOG.md](../CHANGELOG.md)** — Historial de versiones.
- **[hoja-de-ruta.md](hoja-de-ruta.md)** — Estado del proyecto, comparativa con
  alternativas y backlog priorizado.

### Contribuir

- **[desarrollo.md](desarrollo.md)** — Puesta en marcha, estructura, tests y
  convenciones del proyecto.

---

## Tres cosas que conviene saber antes de tocar el código

1. **Ninguna ruta de la interfaz se usa sin pasar por
   `browser.resolve_safe_path()`.** Resuelve los enlaces simbólicos antes de
   comprobar que cae dentro de la carpeta personal.
2. **Ningún borrado usa `unlink()` ni `rmtree()`.** Todo pasa por
   `trash.move_to_trash()`. Martix administra documentos personales; un error
   no puede ser irreversible.
3. **Los tests ejecutan el ataque, no comprueban la mitigación.** Si añades una
   defensa, añade también la sonda que intenta saltársela.
