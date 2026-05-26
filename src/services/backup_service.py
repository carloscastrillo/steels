from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil

from src.utils.db import get_db_path


BASE_DIR = Path(__file__).resolve().parent.parent.parent
BACKUP_DIR = BASE_DIR / "backups"


def create_startup_backup(prefix: str = "startup") -> Path:
    """
    Crea una copia de seguridad de la DB al arrancar la app.

    Es deliberadamente simple: copia el fichero SQLite completo antes de operar.
    La app es monousuario, por lo que este backup es suficiente para uso local.
    """
    db_path = get_db_path()

    if not db_path.exists():
        raise FileNotFoundError(f"No existe la base de datos: {db_path}")

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"steel_mvp_{prefix}_{timestamp}.db"

    shutil.copy2(db_path, backup_path)

    return backup_path