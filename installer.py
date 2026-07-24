#!/usr/bin/env python3
"""Instalador completo y unificado para Martix.
Configura el entorno virtual, instala dependencias, crea accesos directos
de escritorio (~/.local/share/applications/martix.desktop), inicio automatico
(~/.config/autostart/martix.desktop), servicio de usuario systemd y el comando 'martix'.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = PROJECT_ROOT / "backend"
VENV_DIR = BACKEND_DIR / ".venv"
DEPLOY_DIR = BACKEND_DIR / "deploy"


def run_cmd(cmd, check=True):
    print(f"==> Ejecutando: {' '.join(cmd)}")
    return subprocess.run(cmd, check=check)


def install_martix():
    print("\n=======================================================")
    print("        🚀 INSTALADOR DE MARTIX FILE EXPLORER")
    print("=======================================================\n")

    # 1. Verificar version de Python
    if sys.version_info < (3, 10):
        print("❌ Error: Se requiere Python 3.10 o superior.")
        sys.exit(1)

    print("✅ Python 3.10+ verificado:", sys.version.split()[0])

    # 2. Crear entorno virtual si no existe
    if not VENV_DIR.exists():
        print("==> Creando entorno virtual Python en:", VENV_DIR)
        run_cmd([sys.executable, "-m", "venv", str(VENV_DIR)])

    python_bin = VENV_DIR / ("Scripts/python.exe" if os.name == "nt" else "bin/python3")

    # 3. Instalar dependencias
    print("==> Instalando / actualizando dependencias...")
    run_cmd([str(python_bin), "-m", "pip", "install", "--quiet", "--upgrade", "pip"], check=False)
    
    req_file = BACKEND_DIR / "requirements.txt"
    if req_file.exists():
        run_cmd([str(python_bin), "-m", "pip", "install", "--quiet", "-r", str(req_file)])

    req_desktop = BACKEND_DIR / "requirements-desktop.txt"
    if req_desktop.exists():
        try:
            run_cmd([str(python_bin), "-m", "pip", "install", "--quiet", "-r", str(req_desktop)], check=False)
        except Exception:
            pass

    # 4. En Linux: Instalar lanzador de escritorio, autostart y servicio systemd
    if sys.platform.startswith("linux"):
        home = Path.home()
        apps_dir = home / ".local/share/applications"
        autostart_dir = home / ".config/autostart"
        systemd_dir = home / ".config/systemd/user"
        bin_dir = home / ".local/bin"

        apps_dir.mkdir(parents=True, exist_ok=True)
        autostart_dir.mkdir(parents=True, exist_ok=True)
        systemd_dir.mkdir(parents=True, exist_ok=True)
        bin_dir.mkdir(parents=True, exist_ok=True)

        exec_cmd = f"{python_bin} {BACKEND_DIR / 'desktop.py'}"

        # 4a. martix.desktop
        desktop_content = f"""[Desktop Entry]
Type=Application
Name=Martix File Explorer
Comment=Organizador inteligente de archivos en tiempo real y analizador de disco WizTree
Exec={exec_cmd}
Icon=folder-download
Terminal=false
Categories=Utility;FileManager;System;
StartupNotify=true
"""
        desktop_file = apps_dir / "martix.desktop"
        autostart_file = autostart_dir / "martix.desktop"

        desktop_file.write_text(desktop_content, encoding="utf-8")
        autostart_file.write_text(desktop_content, encoding="utf-8")

        desktop_file.chmod(0o755)
        autostart_file.chmod(0o755)
        print("✅ Acceso directo creado en menú de aplicaciones:", desktop_file)
        print("✅ Inicio automático configurado al encender el PC:", autostart_file)

        # 4b. martix.service systemd
        service_content = f"""[Unit]
Description=Martix File Organizer Daemon
After=network.target

[Service]
Type=simple
WorkingDirectory={BACKEND_DIR}
ExecStart={python_bin} {BACKEND_DIR / 'main.py'}
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
"""
        service_file = systemd_dir / "martix.service"
        service_file.write_text(service_content, encoding="utf-8")
        print("✅ Servicio systemd creado en:", service_file)

        try:
            subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
            subprocess.run(["systemctl", "--user", "enable", "--now", "martix.service"], check=False)
            print("✅ Servicio systemd 'martix.service' activado e iniciado.")
        except Exception as e:
            print("⚠️ Nota sobre systemctl:", e)

        # 4c. Comando CLI 'martix' en ~/.local/bin/martix
        cli_wrapper = bin_dir / "martix"
        cli_script = f"""#!/usr/bin/env bash
if [ "${{1:-}}" = "update" ] || [ "${{1:-}}" = "actualizar" ]; then
    {sys.executable} "{PROJECT_ROOT / 'installer.py'}" update
else
    {python_bin} "{BACKEND_DIR / 'desktop.py'}" "$@"
fi
"""
        cli_wrapper.write_text(cli_script, encoding="utf-8")
        cli_wrapper.chmod(0o755)
        print("✅ Comando de consola 'martix' instalado en:", cli_wrapper)

    print("\n=======================================================")
    print("🎉 ¡INSTALACIÓN DE MARTIX COMPLETADA CON ÉXITO!")
    print("=======================================================")
    print("• Puedes abrir Martix desde tu menú de aplicaciones o escribiendo 'martix' en la terminal.")
    print("• Escribe 'martix update' en la terminal para buscar e instalar actualizaciones.")
    print("• Interfaz Web Dashboard: http://127.0.0.1:5000")
    print("• Martix se ejecutará automáticamente en segundo plano al iniciar tu sesión.")
    print("=======================================================\n")


def update_martix():
    print("\n=======================================================")
    print("        🔄 ACTUALIZADOR DE MARTIX FILE EXPLORER")
    print("=======================================================\n")

    # 1. git fetch & pull
    print("==> Buscando actualizaciones en el repositorio remoto...")
    try:
        subprocess.run(["git", "fetch", "origin", "main"], cwd=str(PROJECT_ROOT), check=False)
        res_head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(PROJECT_ROOT), capture_output=True, text=True, check=False)
        res_remote = subprocess.run(["git", "rev-parse", "origin/main"], cwd=str(PROJECT_ROOT), capture_output=True, text=True, check=False)
        
        head_commit = res_head.stdout.strip()
        remote_commit = res_remote.stdout.strip()

        if head_commit == remote_commit and head_commit != "":
            print(f"✅ Martix ya está actualizado en la versión más reciente ({head_commit[:7]}).")
        else:
            print("==> Nueva versión detectada. Descargando cambios de git...")
            pull_res = subprocess.run(["git", "pull", "origin", "main"], cwd=str(PROJECT_ROOT), capture_output=True, text=True, check=False)
            if pull_res.returncode == 0:
                print("✅ Código actualizado correctamente desde git origin/main.")
            else:
                print("⚠️ Aviso al hacer git pull:", pull_res.stderr or pull_res.stdout)
    except Exception as exc:
        print("⚠️ No se pudo comprobar git:", exc)

    # 2. Re-instalar / verificar dependencias
    python_bin = VENV_DIR / ("Scripts/python.exe" if os.name == "nt" else "bin/python3")
    if VENV_DIR.exists():
        print("==> Verificando dependencias en entorno virtual...")
        req_file = BACKEND_DIR / "requirements.txt"
        if req_file.exists():
            subprocess.run([str(python_bin), "-m", "pip", "install", "--quiet", "-r", str(req_file)], check=False)
        req_desktop = BACKEND_DIR / "requirements-desktop.txt"
        if req_desktop.exists():
            subprocess.run([str(python_bin), "-m", "pip", "install", "--quiet", "-r", str(req_desktop)], check=False)

    # 3. Reiniciar servicio systemd en Linux si existe
    if sys.platform.startswith("linux"):
        try:
            subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
            subprocess.run(["systemctl", "--user", "restart", "martix.service"], check=False)
            print("✅ Servicio systemd 'martix.service' reiniciado con la versión nueva.")
        except Exception as e:
            print("⚠️ Nota sobre systemctl:", e)

    print("\n=======================================================")
    print("🎉 ¡MARTIX HA SIDO ACTUALIZADO CORRECTAMENTE!")
    print("=======================================================\n")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].lower() in ("update", "actualizar", "--update", "-u"):
        update_martix()
    else:
        install_martix()

