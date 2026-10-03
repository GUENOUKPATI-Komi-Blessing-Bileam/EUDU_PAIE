"""
src.data
~~~~~~~~
Contient les classes DAO (Data-Access-Object) qui encapsulent tout le
SQL / SQLite. Aucun widget UI ne doit appeler directement sqlite3 ;
elles utilisent uniquement les fonctions/classes exposées ici.
"""

# Export explicite des DAO les plus utilisés – cela facilite les imports
# depuis le reste du code (ex. : from src.data import EleveDAO)
from .eleve_dao import EleveDAO
from .paiement_dao import PaiementDAO
from .database import get_connection, init_db

__all__ = ["EleveDAO", "PaiementDAO", "get_connection", "init_db"]