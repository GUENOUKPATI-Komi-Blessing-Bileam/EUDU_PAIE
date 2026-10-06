"""
src.data.database
~~~~~~~~~~~~~~~~~
Gestion centralisée de la connexion SQLite.
* `get_connection()` renvoie une connexion **singleton** (une seule
  instance pendant toute la durée de vie de l’application).
* `init_db()` crée les tables si elles n’existent pas et charge le script
  `schema.sql` fourni dans le répertoire racine du projet.
* Toutes les DAO utilisent ces fonctions – aucune DAO ne doit créer
  sa propre connexion.
"""

import os
import shutil
import sqlite3
import sys
from pathlib import Path
from typing import Generator

# ----------------------------------------------------------------------
# Chemin persistant de la base utilisateur
# ----------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
SCHEMA_PATH = BASE_DIR / "schema.sql"
APP_DATA_DIR = Path(
    os.environ.get("APPDATA")
    or os.environ.get("LOCALAPPDATA")
    or (Path.home() / ".local" / "share")
) / "EduPaie"
DB_PATH = APP_DATA_DIR / "school_payments.db"
LEGACY_DB_PATHS = (
    BASE_DIR / "school_payments.db",
    Path(sys.executable).resolve().parent / "school_payments.db",
    Path(sys.executable).resolve().parent.parent / "school_payments.db",
)

# ----------------------------------------------------------------------
# Singleton SQLite connection
# ----------------------------------------------------------------------
_connection: sqlite3.Connection | None = None


def get_connection() -> sqlite3.Connection:
    """
    Retourne la connexion SQLite unique de l’application.
    La connexion est ouverte avec `detect_types=sqlite3.PARSE_DECLTYPES`
    pour permettre le stockage automatique de `datetime` si besoin.
    """
    global _connection
    if _connection is None:
        # `check_same_thread=False` permet d’utiliser la même connexion
        # depuis plusieurs threads PySide (ex. : QThread workers).
        _connection = sqlite3.connect(
            DB_PATH,
            detect_types=sqlite3.PARSE_DECLTYPES,
            isolation_level=None,      # autocommit → on gère les transactions manuellement
            check_same_thread=False,
        )
        _connection.row_factory = sqlite3.Row   # accès par nom de colonne
        # Activer les foreign‑keys (désactivé par défaut dans SQLite)
        _connection.execute("PRAGMA foreign_keys = ON;")
    return _connection


# ----------------------------------------------------------------------
# Context manager pour les transactions
# ----------------------------------------------------------------------
class transaction:
    """
    Usage :

    >>> with transaction():
    ...     dao.add_eleve(...)
    ...     dao.add_paiement(...)
    """
    def __enter__(self):
        self.conn = get_connection()
        self.conn.execute("BEGIN;")
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.conn.execute("COMMIT;")
        else:
            self.conn.execute("ROLLBACK;")
        # ne pas supprimer la connexion – elle reste disponible


# ----------------------------------------------------------------------
# Initialisation de la base (appelée au démarrage de l’app)
# ----------------------------------------------------------------------
def init_db(force: bool = False) -> None:
    """
    Ouvre la base utilisateur persistante et applique le schéma SQL.
    Au premier lancement, récupère une ancienne base locale si disponible.
    *force* : si True, recrée la base vide (usage réservé aux tests).
    """
    if force:
        close_connection()
        if DB_PATH.exists():
            DB_PATH.unlink()

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not force and not DB_PATH.exists():
        for ancienne_base in LEGACY_DB_PATHS:
            if ancienne_base.is_file() and ancienne_base.resolve() != DB_PATH.resolve():
                shutil.copy2(ancienne_base, DB_PATH)
                break

    if not SCHEMA_PATH.is_file():
        raise FileNotFoundError(f"Fichier de schéma introuvable : {SCHEMA_PATH}")

    conn = get_connection()
    sql_script = SCHEMA_PATH.read_text(encoding="utf-8")
    conn.executescript(sql_script)
    conn.execute("PRAGMA foreign_keys = ON;")


# ----------------------------------------------------------------------
# Helper – fermeture propre (appelé à la fin du programme)
# ----------------------------------------------------------------------
def close_connection() -> None:
    """Ferme la connexion SQLite si elle a été ouverte."""
    global _connection
    if _connection is not None:
        _connection.close()
        _connection = None


# ----------------------------------------------------------------------
# Export du module
# ----------------------------------------------------------------------
__all__ = [
    "get_connection",
    "transaction",
    "init_db",
    "close_connection",
    "DB_PATH",
]