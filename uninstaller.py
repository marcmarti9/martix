#!/usr/bin/env python3
"""Desinstalador completo y unificado para Martix.
Detiene procesos y servicios de Martix, y elimina accesos directos,
lanzadores autostart y archivos del sistema.
"""

import os
import signal
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

# Lineas de comando que identifican de verdad al servidor de Martix. Antes se
# usaba `pkill -f martix`, que casa con CUALQUIER proceso cuya linea de
# comandos contenga "martix" -- incluido el propio desinstalador, que se
# ejecuta como `python3 /ruta/a/martix/uninstaller.py`. El desinstalador se
# mataba a si mismo en este punto y nunca llegaba a borrar los accesos
# directos, el autostart ni el servicio. Tambien mataba editores o terminales
# que tuvieran el proyecto abierto.
_SERVER_MARKERS = (
    str(PROJECT_ROOT / "backend" / "main.py"),
    str(PROJECT_ROOT / "backend" / "desktop.py"),
)


def _stop_martix_processes() -> None:
    """Detiene solo los procesos del servidor de Martix, nunca a si mismo."""
    own_pid = os.getpid()
    for marker in _SERVER_MARKERS:
        try:
            result = subprocess.run(
                ["pgrep", "-f", marker], capture_output=True, text=True, check=False
            )
        except FileNotFoundError:
            print("  - 'pgrep' no disponible; omitiendo parada de procesos")
            return
        for line in result.stdout.split():
            try:
                pid = int(line)
            except ValueError:
                continue
            if pid == own_pid or pid == os.getppid():
                continue
            try:
                os.kill(pid, signal.SIGTERM)
                print(f"  - Detenido proceso {pid} ({Path(marker).name})")
            except OSError as exc:
                print(f"  - No se pudo detener el proceso {pid}: {exc}")


def uninstall_martix():
    print("\n=======================================================")
    print("        🗑️ DESINSTALADOR DE MARTIX FILE EXPLORER")
    print("=======================================================\n")

    if sys.platform.startswith("linux"):
        home = Path.home()
        desktop_app = home / ".local/share/applications/martix.desktop"
        autostart_app = home / ".config/autostart/martix.desktop"
        service_file = home / ".config/systemd/user/martix.service"
        cli_bin = home / ".local/bin/martix"

        print("==> Deteniendo procesos y servicios de Martix...")
        try:
            subprocess.run(["systemctl", "--user", "stop", "martix.service"], check=False)
            subprocess.run(["systemctl", "--user", "disable", "martix.service"], check=False)
        except Exception:
            pass

        _stop_martix_processes()

        print("==> Eliminando archivos de integración del sistema...")
        for f in (desktop_app, autostart_app, service_file, cli_bin):
            if f.exists():
                try:
                    f.unlink()
                    print(f"  - Eliminado: {f}")
                except Exception as e:
                    print(f"  - Error al eliminar {f}: {e}")

        try:
            subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
        except Exception:
            pass

    print("\n=======================================================")
    print("✅ Martix ha sido desinstalado del sistema.")
    print("Nota: El código fuente y la base de datos de configuración")
    print("se mantienen en el directorio para tu seguridad.")
    print("=======================================================\n")


if __name__ == "__main__":
    uninstall_martix()
