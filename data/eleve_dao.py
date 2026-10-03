"""
src.data.eleve_dao
~~~~~~~~~~~~~~~~~~
DAO (Data‑Access‑Object) dédié à la table **Eleve**.
Toutes les méthodes renvoient des objets Python (dict/Row) ou lèvent
`ValueError` avec un message explicite en cas d’erreur de logique
(duplication, contrainte, etc.).  

L’UI n’appelle jamais directement sqlite3 ; elle utilise cette classe
via le service métier (`src.business.services.EleveService`).
"""

from __future__ import annotations

import sqlite3
from typing import List, Optional, Tuple

from .database import get_connection, transaction


class EleveDAO:
    """DAO pour la table `Eleve`."""

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------
    @staticmethod
    def create(
        nom: str,
        prenom: str,
        classe: str,
        annee_scolaire: str,
        total_du: float,
    ) -> int:
        """
        Insère un nouvel élève et retourne l'`id` généré.
        Lève `ValueError` si les paramètres sont invalides.
        """
        if not all([nom.strip(), prenom.strip(), classe.strip(),
                    annee_scolaire.strip()]):
            raise ValueError("Tous les champs texte sont obligatoires.")

        if total_du < 0:
            raise ValueError("Le montant total dû ne peut pas être négatif.")

        sql = """
            INSERT INTO Eleve (nom, prenom, classe, annee_scolaire, total_du)
            VALUES (?, ?, ?, ?, ?);
        """
        conn = get_connection()
        cur = conn.execute(sql, (nom, prenom, classe, annee_scolaire, total_du))
        return cur.lastrowid

    # ------------------------------------------------------------------
    # READ (single)
    # ------------------------------------------------------------------
    @staticmethod
    def get_by_id(eleve_id: int) -> Optional[sqlite3.Row]:
        """Renvoie la ligne de l’élève demandé ou None si introuvable."""
        sql = "SELECT * FROM Eleve WHERE id = ?;"
        cur = get_connection().execute(sql, (eleve_id,))
        return cur.fetchone()

    # ------------------------------------------------------------------
    # READ (list with optional filters / search)
    # ------------------------------------------------------------------
    @staticmethod
    def list_all(
        recherche: str = "",
        classe: str = "",
        order_by: str = "nom ASC",
    ) -> List[sqlite3.Row]:
        """
        Retourne la liste des élèves filtrés par :

        * `recherche` : recherche partielle (nom + prenom + classe)
        * `classe` : filtre exact sur la colonne classe
        * `order_by` : clause ORDER BY (défaut « nom ASC »)

        La fonction construit dynamiquement la clause WHERE.
        """
        base_sql = "SELECT * FROM Eleve"
        clauses: List[str] = []
        params: List = []

        if recherche:
            like = f"%{recherche.strip()}%"
            clauses.append("(nom LIKE ? OR prenom LIKE ? OR classe LIKE ?)")
            params.extend([like, like, like])

        if classe:
            clauses.append("classe = ?")
            params.append(classe.strip())

        if clauses:
            base_sql += " WHERE " + " AND ".join(clauses)

        base_sql += f" ORDER BY {order_by};"

        cur = get_connection().execute(base_sql, tuple(params))
        return cur.fetchall()

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------
    @staticmethod
    def update(
        eleve_id: int,
        nom: str,
        prenom: str,
        classe: str,
        annee_scolaire: str,
        total_du: float,
    ) -> None:
        """
        Modifie les champs d’un élève existant.
        Lève `ValueError` si l’élève n’existe pas ou si les données sont
        invalides.
        """
        if EleveDAO.get_by_id(eleve_id) is None:
            raise ValueError(f"L’élève d’id {eleve_id} n’existe pas.")

        if not all([nom.strip(), prenom.strip(), classe.strip(),
                    annee_scolaire.strip()]):
            raise ValueError("Tous les champs texte sont obligatoires.")

        if total_du < 0:
            raise ValueError("Le montant total dû ne peut pas être négatif.")

        sql = """
            UPDATE Eleve
            SET nom = ?, prenom = ?, classe = ?, annee_scolaire = ?, total_du = ?
            WHERE id = ?;
        """
        get_connection().execute(
            sql, (nom, prenom, classe, annee_scolaire, total_du, eleve_id)
        )

    @staticmethod
    def delete(eleve_id: int) -> None:
        """Supprime un élève et ses paiements associés dans une transaction."""
        with transaction() as conn:
            cur = conn.execute("DELETE FROM Eleve WHERE id = ?;", (eleve_id,))
            if cur.rowcount == 0:
                raise ValueError(f"L’élève d’id {eleve_id} n’existe pas.")
