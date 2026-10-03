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
import sqlite3
from pathlib import Path
from typing import Generator

# ----------------------------------------------------------------------
# Chemin du fichier .db (placé à la racine du projet, côté exécutable)
# ----------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent   # src/
DB_PATH = BASE_DIR / "school_payments.db"           # ./school_payments.db
SCHEMA_PATH = BASE_DIR / "schema.sql"               # ./schema.sql

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
    Applique le schéma SQL à chaque démarrage afin de créer les tables
    manquantes sans modifier celles qui existent déjà.
    *force* : si True, recrée la base vide (usage réservé aux tests).
    """
    if force:
        close_connection()
        if DB_PATH.exists():
            DB_PATH.unlink()

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
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