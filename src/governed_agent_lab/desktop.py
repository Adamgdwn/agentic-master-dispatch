from __future__ import annotations

import socket
import threading
import time
import webbrowser
from contextlib import closing
from pathlib import Path
from typing import Any

from .server import create_server


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
REPO_ROOT = Path(__file__).resolve().parents[2]
ICON_PATH = REPO_ROOT / "web" / "icon.svg"


def build_app_url(host: str, port: int) -> str:
    return f"http://{host}:{port}"


def find_available_port(host: str = DEFAULT_HOST, preferred_port: int = DEFAULT_PORT) -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if sock.connect_ex((host, preferred_port)) != 0:
            return preferred_port
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def _run_qt_window(url: str) -> bool:
    try:
        from PyQt5.QtCore import QUrl
        from PyQt5.QtGui import QIcon
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtWebEngineWidgets import QWebEngineView
    except Exception:
        return False

    app = QApplication.instance() or QApplication([])
    if ICON_PATH.exists():
        app.setWindowIcon(QIcon(str(ICON_PATH)))
    view = QWebEngineView()
    view.setWindowTitle("Governed Agent Lab")
    if ICON_PATH.exists():
        view.setWindowIcon(QIcon(str(ICON_PATH)))
    view.resize(1440, 960)
    view.load(QUrl(url))
    view.show()
    app.exec_()
    return True


def _run_pywebview_window(url: str) -> bool:
    try:
        import webview  # type: ignore
    except Exception:
        return False

    try:
        webview.create_window(
            "Governed Agent Lab",
            url,
            width=1440,
            height=960,
            min_size=(1100, 720),
            text_select=True,
        )
        webview.start(debug=False)
        return True
    except Exception:
        return False


def _open_browser_fallback(url: str) -> None:
    print("Desktop shell unavailable. Opening in your browser instead.")
    webbrowser.open(url)
    while True:
        time.sleep(1)


def run_desktop_app(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> dict[str, Any]:
    actual_port = find_available_port(host=host, preferred_port=port)
    url = build_app_url(host, actual_port)
    server = create_server(host=host, port=actual_port)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    print(f"Serving Governed Agent Lab UI at {url}")

    try:
        if _run_qt_window(url):
            return {"mode": "desktop-qt", "url": url, "port": actual_port}
        if _run_pywebview_window(url):
            return {"mode": "desktop-webview", "url": url, "port": actual_port}
        _open_browser_fallback(url)
        return {"mode": "browser", "url": url, "port": actual_port}
    except KeyboardInterrupt:
        return {"mode": "interrupted", "url": url, "port": actual_port}
    finally:
        server.shutdown()
        server.server_close()
