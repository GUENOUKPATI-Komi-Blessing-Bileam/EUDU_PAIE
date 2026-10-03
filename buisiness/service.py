"""
src.business.services
~~~~~~~~~~~~~~~~~~~~~
Implémentation des services de haut‑niveau appelés par l’interface
graphique.  Chaque service orchestre :

* appels aux DAO (`src.data.*`)
* règles métier (calcul du solde, validation, génération du numéro de reçu)
* création du PDF de reçu (via `src.receipts.create_receipt_pdf`)

Aucun widget UI ne doit toucher directement la base : ils utilisent
uniquement les deux classes ci‑dessous.
"""

import datetime
import math
from pathlib import Path
from typing import List, Tuple, Dict, Any

from data.eleve_dao import EleveDAO
from data.paiement_dao import PaiementDAO
from reçuepdf import create_receipt_pdf, receipt_pdf_path
from .utils import generate_receipt_number, format_currency, STATUS_MAP


# ----------------------------------------------------------------------
# Service Élève
# ----------------------------------------------------------------------
class EleveService:
    """Opérations liées aux élèves (CRUD + informations dérivées)."""

    @staticmethod
    def ajouter(
        nom: str,
        prenom: str,
        classe: str,
        annee_scolaire: str,
        total_du: float,
    ) -> int:
        """
        Crée un élève et retourne son `id`.
        Le DAO élève effectue les validations de base.
        """
        return EleveDAO.create(
            nom=nom,
            prenom=prenom,
            classe=classe,
            annee_scolaire=annee_scolaire,
            total_du=total_du,
        )

    @staticmethod
    def modifier(
        eleve_id: int,
        nom: str,
        prenom: str,
        classe: str,
        annee_scolaire: str,
        total_du: float,
    ) -> None:
        """Met à jour les informations d’un élève."""
        EleveDAO.update(
            eleve_id=eleve_id,
            nom=nom,
            prenom=prenom,
            classe=classe,
            annee_scolaire=annee_scolaire,
            total_du=total_du,
        )

    @staticmethod
    def supprimer(eleve_id: int) -> None:
        """Supprime l’élève ainsi que tous ses paiements (cascade)."""
        EleveDAO.delete(eleve_id)

    @staticmethod
    def lister(
        recherche: str = "",
        classe: str = "",
        order_by: str = "nom ASC",
    ) -> List[Dict[str, Any]]:
        """
        Retourne la liste des élèves enrichie de :

        * `solde`  – montant restant à payer (float)
        * `statut` – texte « Soldé », « Partiellement payé », « Non payé »

        La fonction ne fait qu’une requête sur les élèves, puis calcule
        le solde à la volée (le nombre d’élèves est faible – < 200 ).
        """
        rows = EleveDAO.list_all(recherche, classe, order_by)
        result = []
        for r in rows:
            eleve_id = r["id"]
            total_du = float(r["total_du"])
            somme_paye = PaiementDAO._somme_paye(eleve_id)
            solde = total_du - somme_paye
            statut = STATUS_MAP(solde, total_du)
            result.append(
                {
                    "id": eleve_id,
                    "nom": r["nom"],
                    "prenom": r["prenom"],
                    "classe": r["classe"],
                    "annee_scolaire": r["annee_scolaire"],
                    "total_du": total_du,
                    "solde": solde,
                    "statut": statut,
                }
            )
        return result

    @staticmethod
    def obtenir(eleve_id: int) -> Dict[str, Any]:
        """
        Retourne les informations détaillées d’un élève (idem que
        `lister` mais pour un seul id) ainsi que la liste de ses paiements.
        """
        eleve = EleveDAO.get_by_id(eleve_id)
        if eleve is None:
            raise ValueError(f"L’élève d’id {eleve_id} n’existe pas.")

        total_du = float(eleve["total_du"])
        somme_paye = PaiementDAO._somme_paye(eleve_id)
        solde = total_du - somme_paye
        statut = STATUS_MAP(solde, total_du)

        paiements = PaiementDAO.list_by_eleve(eleve_id)

        return {
            "id": eleve_id,
            "nom": eleve["nom"],
            "prenom": eleve["prenom"],
            "classe": eleve["classe"],
            "annee_scolaire": eleve["annee_scolaire"],
            "total_du": total_du,
            "solde": solde,
            "statut": statut,
            "paiements": paiements,
        }


class ReceiptGenerationError(RuntimeError):
    """Signale que le paiement est enregistré mais que son reçu PDF a échoué."""

    def __init__(self, paiement_id: int, cause: Exception) -> None:
        self.paiement_id = paiement_id
        super().__init__(
            f"Le paiement n° {paiement_id} est enregistré, mais le reçu PDF a échoué : {cause}"
        )


class PaiementService:
    """Règles métier et opérations applicatives liées aux paiements."""

    MODES_AUTORISES = ("Espèces", "Chèque", "Virement", "Mobile money")

    @staticmethod
    def enregistrer_paiement(
        eleve_id: int,
        montant: float,
        date_paiement: datetime.date,
        mode: str,
    ) -> int:
        """Valide et enregistre un versement avec un numéro de reçu unique."""
        try:
            montant = float(montant)
        except (TypeError, ValueError) as exc:
            raise ValueError("Le montant doit être un nombre valide.") from exc
        if not math.isfinite(montant) or montant <= 0:
            raise ValueError("Le montant du paiement doit être supérieur à zéro.")

        if isinstance(date_paiement, datetime.datetime):
            date_paiement = date_paiement.date()
        if not isinstance(date_paiement, datetime.date):
            raise ValueError("La date du paiement est invalide.")

        if mode not in PaiementService.MODES_AUTORISES:
            raise ValueError("Sélectionnez un mode de paiement valide.")

        numero_recu = generate_receipt_number()
        paiement_id = PaiementDAO.create(
            eleve_id=eleve_id,
            montant=montant,
            date_paiement=date_paiement,
            mode=mode,
            numero_recu=numero_recu,
        )
        try:
            PaiementService.generer_recu_pdf(paiement_id)
        except Exception as exc:
            raise ReceiptGenerationError(paiement_id, exc) from exc
        return paiement_id

    @staticmethod
    def obtenir_paiement(paiement_id: int) -> Dict[str, Any]:
        """Retourne le paiement et l’élève associés pour afficher son reçu."""
        paiement = PaiementDAO.get_by_id(paiement_id)
        if paiement is None:
            raise ValueError(f"Le paiement d’id {paiement_id} n’existe pas.")

        eleve = EleveDAO.get_by_id(int(paiement["eleve_id"]))
        if eleve is None:
            raise ValueError("L’élève associé à ce paiement n’existe plus.")

        return {"eleve": dict(eleve), "paiement": dict(paiement)}

    @staticmethod
    def generer_recu_pdf(paiement_id: int) -> Path:
        """Génère ou réimprime le PDF du paiement demandé."""
        recu = PaiementService.obtenir_paiement(paiement_id)
        numero = int(recu["paiement"]["numero_recu"])
        return create_receipt_pdf(
            recu["eleve"],
            recu["paiement"],
            receipt_pdf_path(numero),
        )

    @staticmethod
    def chemin_recu(paiement_id: int) -> Path:
        """Retourne le chemin du PDF associé à un paiement enregistré."""
        recu = PaiementService.obtenir_paiement(paiement_id)
        return receipt_pdf_path(int(recu["paiement"]["numero_recu"]))

