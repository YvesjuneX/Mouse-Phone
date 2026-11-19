"""Lanzador compatible del servicio de escritorio.

La implementación está en ``src/mouse_phone``. Este archivo permite seguir usando
``python server.py`` durante la transición.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent / "src"))

from mouse_phone.main import main, run  # noqa: E402,F401
from mouse_phone.transport.websocket_server import handle_client  # noqa: E402,F401
from mouse_phone.input.windows import pyautogui  # noqa: E402,F401


if __name__ == "__main__":
    run()
