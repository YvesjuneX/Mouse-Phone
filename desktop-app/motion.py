"""Importación compatible de Motion; el código vive en src/mouse_phone/input."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent / "src"))
from mouse_phone.input.motion import Motion  # noqa: E402,F401
