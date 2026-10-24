"""Ubicaciones de recursos y datos locales para desarrollo y paquete instalado."""

import os
import sys
from pathlib import Path


APP_NAME = "Cancha"


def project_root():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def resource_path(name):
    """Resuelve recursos desde el proyecto o desde el bundle de PyInstaller."""
    bundle_root = Path(getattr(sys, "_MEIPASS", project_root()))
    return bundle_root / name


def database_path(filename="cancha_reservas.db"):
    """Usa el directorio del proyecto al desarrollar y AppData al instalar."""
    if not getattr(sys, "frozen", False):
        return project_root() / filename
    base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / APP_NAME
    base.mkdir(parents=True, exist_ok=True)
    return base / filename
