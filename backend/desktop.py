#!/usr/bin/env python3
"""Punto de entrada de la aplicación de escritorio de Martix.

El ejecutable distribuye el servidor y la interfaz en el mismo proceso. El
servidor solo escucha en loopback, en un puerto efímero, como canal IPC interno
para la ventana Qt; el usuario nunca necesita abrir un navegador ni conocer la
URL.
"""

from __future__ import annotations

import logging
import socket
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app import db
from app.security import API_TOKEN, listening_beyond_localhost
from app.server import create_app, resume_patrol_if_needed
from config.settings import HOST

WINDOW_TITLE = "Martix — Organizador de archivos"
WINDOW_SIZE = (1240, 800)


def _port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _start_server_in_background():
    """Start a private WSGI server on an ephemeral loopback port."""
    if listening_beyond_localhost() and not API_TOKEN:
        raise RuntimeError(
            f"HOST={HOST} expone Martix fuera de este equipo. "
            "Usa HOST=127.0.0.1 para el ejecutable de escritorio o define "
            "MARTIX_TOKEN en una instalación avanzada."
        )

    from werkzeug.serving import make_server

    db.init_db()
    application = create_app()
    resume_patrol_if_needed()
    server = make_server("127.0.0.1", 0, application, threaded=True)
    port = int(server.server_port)
    thread = threading.Thread(
        target=server.serve_forever,
        daemon=True,
        name="MartixLocalServer",
    )
    thread.start()

    for _ in range(50):
        if _port_open(port):
            return server, thread, f"http://127.0.0.1:{port}/"
        time.sleep(0.1)

    server.shutdown()
    raise RuntimeError("El servidor privado de Martix no arrancó.")


def _make_tray_icon(QIcon, QPixmap, QPainter, QColor, Qt):
    """Create a small neutral icon without requiring an external asset."""
    pixmap = QPixmap(32, 32)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#2f2f31"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(2, 2, 28, 28, 7, 7)
    painter.setPen(QColor("#ffffff"))
    font = painter.font()
    font.setBold(True)
    font.setPixelSize(18)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "M")
    painter.end()
    return QIcon(pixmap)


def _open_pyqt6_app(url: str, server) -> bool:
    """Open the only supported end-user window: a native Qt WebEngine shell."""
    try:
        from PyQt6.QtCore import QUrl, Qt
        from PyQt6.QtGui import QAction, QIcon, QPainter, QPixmap, QColor
        from PyQt6.QtWidgets import QApplication, QMainWindow, QMenu, QSystemTrayIcon
        from PyQt6.QtWebEngineCore import QWebEngineSettings
        from PyQt6.QtWebEngineWidgets import QWebEngineView
    except ImportError:
        return False

    application = QApplication.instance() or QApplication(sys.argv)
    application.setApplicationName("Martix")
    application.setOrganizationName("Martix")
    application.setQuitOnLastWindowClosed(False)

    class MartixWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle(WINDOW_TITLE)
            self.resize(*WINDOW_SIZE)
            self.view = QWebEngineView(self)
            settings = self.view.settings()
            settings.setAttribute(
                QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls,
                False,
            )
            settings.setAttribute(
                QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls,
                False,
            )
            self.view.setUrl(QUrl(url))
            self.setCentralWidget(self.view)

        def closeEvent(self, event):
            # Closing the window hides the background patrol. The tray menu is
            # the explicit path for terminating the process.
            event.ignore()
            self.hide()

    window = MartixWindow()
    icon = _make_tray_icon(QIcon, QPixmap, QPainter, QColor, Qt)
    window.setWindowIcon(icon)

    tray = QSystemTrayIcon(icon, application)
    tray.setToolTip("Martix — organización local y privada")
    menu = QMenu()

    open_action = QAction("Abrir Martix", menu)
    open_action.triggered.connect(lambda: (window.show(), window.raise_(), window.activateWindow()))
    menu.addAction(open_action)
    menu.addSeparator()

    def quit_application():
        tray.hide()
        try:
            server.shutdown()
        finally:
            application.quit()

    quit_action = QAction("Salir de Martix", menu)
    quit_action.triggered.connect(quit_application)
    menu.addAction(quit_action)
    tray.setContextMenu(menu)
    tray.activated.connect(
        lambda reason: (
            window.show(), window.raise_(), window.activateWindow()
        ) if reason == QSystemTrayIcon.ActivationReason.Trigger else None
    )
    tray.show()

    window.show()
    application.exec()
    return True


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    server = None
    try:
        server, _thread, url = _start_server_in_background()
        if _open_pyqt6_app(url, server):
            return 0
        raise RuntimeError(
            "La versión distribuida de Martix necesita PyQt6-WebEngine. "
            "No se abrirá un navegador externo; reinstala el ejecutable oficial."
        )
    except Exception as exc:
        logging.getLogger("martix.desktop").exception("No se pudo iniciar Martix")
        try:
            if server is not None:
                server.shutdown()
        except Exception:
            pass
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
