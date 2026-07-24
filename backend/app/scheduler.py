"""Task Scheduler: Ejecuta de forma periódica el mantenimiento y la organización
de carpetas vigiladas en segundo plano."""

import logging
import threading
import time
from pathlib import Path

from app import db
from app.organizer import organize_directory, run_maintenance_cleanup
from config.settings import DOWNLOADS_DIR

logger = logging.getLogger("martix.scheduler")

DEFAULT_INTERVAL_MINUTES = 60


class TaskScheduler:
    """Gestiona tareas periódicas de mantenimiento y barrido de carpetas."""

    def __init__(self, interval_minutes: int = DEFAULT_INTERVAL_MINUTES):
        self._interval_minutes = interval_minutes
        self._enabled = True
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    def load_config(self) -> None:
        try:
            enabled_str = db.get_setting("scheduler_enabled", "1")
            self._enabled = enabled_str in ("1", "true", "yes")

            interval_str = db.get_setting("scheduler_interval_minutes", str(DEFAULT_INTERVAL_MINUTES))
            try:
                self._interval_minutes = max(1, int(interval_str))
            except ValueError:
                self._interval_minutes = DEFAULT_INTERVAL_MINUTES
        except Exception as e:
            logger.error("Error al cargar configuracion del scheduler: %s", e)

    def start(self) -> None:
        with self._lock:
            if self.is_running():
                return
            self.load_config()
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._run_loop,
                daemon=True,
                name="MartixSchedulerThread"
            )
            self._thread.start()
            logger.info("TaskScheduler iniciado (intervalo: %d min, enabled: %s)", self._interval_minutes, self._enabled)

    def stop(self) -> None:
        with self._lock:
            if self._thread is not None:
                self._stop_event.set()
                self._thread.join(timeout=3)
                self._thread = None
                logger.info("TaskScheduler detenido")

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, val: bool) -> None:
        self._enabled = bool(val)
        try:
            db.set_setting("scheduler_enabled", "1" if self._enabled else "0")
        except Exception as e:
            logger.error("Error al guardar scheduler_enabled en BD: %s", e)

    @property
    def interval_minutes(self) -> int:
        return self._interval_minutes

    @interval_minutes.setter
    def interval_minutes(self, minutes: int) -> None:
        val = max(1, int(minutes))
        self._interval_minutes = val
        try:
            db.set_setting("scheduler_interval_minutes", str(val))
        except Exception as e:
            logger.error("Error al guardar scheduler_interval_minutes en BD: %s", e)

    get_config = lambda self: {
        "enabled": self._enabled,
        "active": self._enabled and self.is_running(),
        "interval_minutes": self._interval_minutes,
        "interval": self._interval_minutes,
        "running": self.is_running(),
    }

    def run_now(self) -> dict:
        """Ejecuta inmediatamente el mantenimiento y barrido de carpetas."""
        logger.info("Ejecutando tareas programadas (run_now)")
        deleted = []
        try:
            deleted = run_maintenance_cleanup()
        except Exception as e:
            logger.exception("Error en mantenimiento programado: %s", e)

        moved = []
        try:
            from app import browser
            moved.extend(organize_directory(DOWNLOADS_DIR))
            watched = db.list_watched_folders()
            for wf in watched:
                if wf.get("active", 1):
                    folder_path_str = wf.get("folder_path", "")
                    resolved = browser.resolve_safe_path(folder_path_str)
                    if resolved and resolved.exists() and resolved.is_dir():
                        moved.extend(organize_directory(resolved))
        except Exception as e:
            logger.exception("Error en barrido de carpetas programado: %s", e)

        return {
            "maintenance_deleted": len(deleted),
            "files_organized": len(moved),
            "deleted_items": deleted,
            "organized_items": moved,
        }

    def _run_loop(self) -> None:
        # La primera ejecucion espera un intervalo completo: arrancar Martix no
        # debe disparar de inmediato un barrido y un borrado por mantenimiento
        # (el usuario tiene "Ejecutar ahora" para eso).
        last_run = time.monotonic()
        while not self._stop_event.is_set():
            interval_seconds = max(60, self._interval_minutes * 60)
            elapsed = time.monotonic() - last_run
            remaining = interval_seconds - elapsed

            if remaining > 0:
                # Se espera lo que de verdad queda, no se hace busy-wait cada
                # 0,5 s: eso eran 172.800 despertares al dia que impedian a la
                # CPU entrar en estados de bajo consumo.
                # El tope de 60 s permite que un cambio de intervalo desde la
                # interfaz se note sin tener que reiniciar el hilo.
                self._stop_event.wait(min(remaining, 60.0))
                continue

            if self._enabled:
                try:
                    self.run_now()
                except Exception:
                    logger.exception("fallo en la ejecucion programada")
            last_run = time.monotonic()


scheduler = TaskScheduler()
