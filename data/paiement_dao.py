"""
src.data.paiement_dao
~~~~~~~~~~~~~~~~~~~~~
DAO dédié à la table **Paiement**.

Responsabilités :
* Insérer un nouveau paiement en respectant la règle métier :
  le solde après paiement ne doit jamais être négatif.
* Récupérer l’historique d’un élève (tri chronologique).
* Obtenir le dernier numéro de reçu afin de générer le suivant
  (fonction utilitaire dans `src.business.utils` utilise ce DAO).
* Toutes les écritures sont encapsulées dans une transaction explicite
  (`src.data.database.transaction`) afin d’assurer l’atomicité
  (mise à jour du paiement **et** mise à jour du solde dans la même
  transaction).

Aucun widget UI n’appelle directement sqlite3 ; les services métier
(`src.business.services.PaiementService`) utilisent ce DAO.
"""

from __future__ import annotations

import datetime
import sqlite3
from typing import List, Optional

from .database import get_connection, transaction
from .eleve_dao import EleveDAO


class PaiementDAO:
    """DAO pour la table `Paiement`."""

    # ------------------------------------------------------------------
    # CREATE – insertion d’un paiement avec validation du solde
    # ------------------------------------------------------------------
    @staticmethod
    def create(
        eleve_id: int,
        montant: float,
        date_paiement: datetime.date,
        mode: str,
        numero_recu: int,
    ) -> int:
        """
        Enregistre un paiement.

        - Vérifie que l’élève existe.
        - Calcule le solde actuel (total_du − somme_des_paiements).
        - Refuse le paiement si ``montant`` > solde actuel (ValueError).
        - Insère le paiement avec le champ ``solde_apres`` mis à jour.
        - Retourne l’`id` du paiement inséré.

        La fonction est exécutée dans une transaction pour que le
        calcul du solde et l’insertion restent atomiques.
        """
        # ---------- 1️⃣ Vérifier existence de l’élève ----------
        eleve = EleveDAO.get_by_id(eleve_id)
        if eleve is None:
            raise ValueError(f"L’élève d’id {eleve_id} n’existe pas.")

        # ---------- 2️⃣ Calcul du solde actuel ----------
        total_du = float(eleve["total_du"])
        somme_paye = PaiementDAO._somme_paye(eleve_id)
        solde_actuel = total_du - somme_paye

        if montant <= 0:
            raise ValueError("Le montant du paiement doit être strictement positif.")
        if montant > solde_actuel:
            raise ValueError(
                f"Montant trop élevé : solde restant {solde_actuel:.2f} €."
            )

        # ---------- 3️⃣ Insertion (transaction) ----------
        with transaction():
            sql = """
                INSERT INTO Paiement
                (eleve_id, montant, date_paiement, mode, numero_recu, solde_apres)
                VALUES (?, ?, ?, ?, ?, ?);
            """
            # le solde après paiement = solde actuel - montant
            solde_apres = solde_actuel - montant

            conn = get_connection()
            cur = conn.execute(
                sql,
                (
                    eleve_id,
                    montant,
                    date_paiement.isoformat(),
                    mode,
                    numero_recu,
                    solde_apres,
                ),
            )
            return cur.lastrowid

    # ------------------------------------------------------------------
    # READ – historique d’un élève (tri par date, puis id)
    # ------------------------------------------------------------------
    @staticmethod
    def list_by_eleve(eleve_id: int) -> List[sqlite3.Row]:
        """
        Retourne la liste des paiements d’un élève, triés du plus ancien
        au plus récent.
        """
        sql = """
            SELECT *
            FROM Paiement
            WHERE eleve_id = ?
            ORDER BY date_paiement ASC, id ASC;
        """
        cur = get_connection().execute(sql, (eleve_id,))
        return cur.fetchall()

    @staticmethod
    def get_by_id(paiement_id: int) -> Optional[sqlite3.Row]:
        """Retourne un paiement par son identifiant, ou None s’il est absent."""
        sql = "SELECT * FROM Paiement WHERE id = ?;"
        return get_connection().execute(sql, (paiement_id,)).fetchone()

    @staticmethod
    def _somme_paye(eleve_id: int) -> float:
        """Retourne le cumul des paiements de l’élève, ou zéro s’il n’en a pas."""
        sql = """
            SELECT COALESCE(SUM(montant), 0) AS total_paye
            FROM Paiement
            WHERE eleve_id = ?;
        """
        row = get_connection().execute(sql, (eleve_id,)).fetchone()
        return float(row["total_paye"]) if row is not None else 0.0

    # ------------------------------------------------------------------
    # READ – dernier numéro de reçu (pour incrémenter)
    # ------------------------------------------------------------------
    @staticmethod
    def last_receipt_number() -> int:
        """
        Retourne le plus grand ``numero_recu`` présent dans la table.
        Si aucun paiement n’existe, retourne 0.
        """
        sql = "SELECT MAX(numero_recu) AS max_num FROM Paiement;"
        cur = get_connection().execute(sql)
        row = cur.fetchone()
        return int(row["max_num"]) if row and row["max_num"] is not None else 0
