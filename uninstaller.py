#!/usr/bin/env python3
"""Desinstalador completo y unificado para Martix.
Detiene procesos y servicios de Martix, y elimina accesos directos,
lanzadores autostart y archivos del sistema.
"""

import os
import sys
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent


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

        try:
            subprocess.run(["pkill", "-f", "martix"], check=False)
        except Exception:
            pass

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
