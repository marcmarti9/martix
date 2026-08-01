#!/usr/bin/env python3
"""Empaqueta Martix como un ejecutable Windows autocontenido.

La versión congelada abre una ventana PyQt6/WebEngine y no depende de un
navegador externo ni de un servidor iniciado por el usuario.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def build() -> None:
    backend_dir = Path(__file__).resolve().parent

    project_dir = backend_dir.parent
    if sys.platform == "win32" or os.name == "nt":
        separator = ";"
    else:
        separator = ":"

    frontend_data = f"{project_dir / 'frontend'}{separator}frontend"
    database_data = f"{project_dir / 'database'}{separator}database"
    config_data = f"{backend_dir / 'config'}{separator}config"

    desktop_script = backend_dir / "desktop.py"

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name=Martix",
        "--onefile",
        "--windowed",
        "--noconfirm",
        "--add-data",
        frontend_data,
        "--add-data",
        database_data,
        "--add-data",
        config_data,
        "--hidden-import=PyQt6.QtWebEngineWidgets",
        "--hidden-import=PyQt6.QtWebEngineCore",
        "--clean",
        str(desktop_script),
    ]

    print("Iniciando empaquetado de Martix...")
    print("Comando:", " ".join(cmd))

    result = subprocess.run(cmd, cwd=str(backend_dir))
    if result.returncode != 0:
        print(f"Error en la construccion con PyInstaller (codigo {result.returncode})", file=sys.stderr)
        sys.exit(result.returncode)

    dist_dir = backend_dir / "dist"
    executable_name = "Martix.exe" if os.name == "nt" else "Martix"
    built_executable = dist_dir / executable_name
    if not built_executable.exists():
        raise FileNotFoundError(f"No se encontro el ejecutable generado: {built_executable}")

    # El artefacto para usuarios queda en la raiz del proyecto. ``dist`` sigue
    # siendo la salida tecnica de PyInstaller, pero nadie necesita entrar en
    # backend para encontrar y abrir Martix.
    root_executable = project_dir / executable_name
    shutil.copy2(built_executable, root_executable)
    print("\nEmpaquetado completado.")
    print(f"Ejecutable para usuarios: {root_executable}")
    print(f"Copia tecnica: {built_executable}")


if __name__ == "__main__":
    build()
