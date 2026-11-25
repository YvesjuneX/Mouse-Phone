"""Permisos restrictivos para archivos locales en Windows."""
import getpass
import os
from pathlib import Path
import subprocess


def restrict_to_current_user(path: Path) -> None:
    """El cifrado sigue protegiendo los secretos si el ACL no puede ajustarse."""
    if os.name != "nt": return
    user = getpass.getuser()
    try:
        subprocess.run(["icacls", str(path), "/inheritance:r", "/grant:r", f"{user}:(F)", "/c", "/q"], check=True, capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError):
        pass
