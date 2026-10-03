"""
src.business
~~~~~~~~~~~~
Logique métier du projet :

* **Calcul du solde** d’un élève (total dû – somme des paiements).
* **Validation d’un paiement** : le montant ne doit pas dépasser le solde
  restant.
* **Génération du numéro de reçu** séquentiel et unique.
* **Services** (EleveService, PaiementService) exposés aux vues UI.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

# ----------------------------------------------------------------------
# Utilitaires de haut niveau
# ----------------------------------------------------------------------
STATUS_MAP = {
    "non_payé": "Non payé",
    "partiel": "Partiel",
    "payé": "Payé",
}


def format_currency(value: float, currency: str = "EUR") -> str:
    """Formate un montant monétaire avec un séparateur de milliers."""
    amount = float(value)
    return f"{amount:,.2f} {currency}"


_receipt_counter = 0


def generate_receipt_number() -> str:
    """Génère un numéro de reçu unique et séquentiel."""
    global _receipt_counter
    _receipt_counter += 1
    today = datetime.now().strftime("%Y%m%d")
    return f"RCPT-{today}-{_receipt_counter:06d}"


class EleveService:
    """Service métier pour gérer le solde d'un élève et ses paiements."""

    def __init__(self, eleve: Optional[Dict[str, Any]] = None):
        self.eleve: Dict[str, Any] = eleve or {
            "id": None,
            "nom": "",
            "total_du": 0.0,
            "paiements": [],
        }

    @property
    def total_du(self) -> float:
        return float(self.eleve.get("total_du", 0.0))

    @total_du.setter
    def total_du(self, value: float) -> None:
        self.eleve["total_du"] = float(value)

    @property
    def paiements(self) -> List[Dict[str, Any]]:
        if "paiements" not in self.eleve:
            self.eleve["paiements"] = []
        return self.eleve["paiements"]

    def calculer_solde(self) -> float:
        """Calcule le solde restant à payer : total dû - paiements effectués."""
        total_paye = sum(float(p.get("montant", 0.0)) for p in self.paiements)
        return self.total_du - total_paye

    def get_solde(self) -> float:
        return self.calculer_solde()

    def valider_paiement(self, montant: float) -> bool:
        """Vérifie qu'un paiement ne dépasse pas le solde restant."""
        montant = float(montant)
        if montant < 0:
            raise ValueError("Le montant du paiement ne peut pas être négatif.")
        if montant > self.get_solde():
            raise ValueError(
                "Le montant du paiement dépasse le solde restant de l'élève."
            )
        return True

    def enregistrer_paiement(
        self,
        montant: float,
        reference: Optional[str] = None,
        date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Enregistre un paiement et retourne le reçu correspondant."""
        self.valider_paiement(montant)
        paiement = {
            "id": generate_receipt_number(),
            "montant": float(montant),
            "reference": reference or "PAIEMENT",
            "date": date or datetime.now(),
        }
        self.paiements.append(paiement)
        return paiement

    def get_statut(self) -> str:
        solde = self.get_solde()
        if solde <= 0:
            return "payé"
        if solde < self.total_du:
            return "partiel"
        return "non_payé"

    def as_dict(self) -> Dict[str, Any]:
        return {
            **self.eleve,
            "solde": self.get_solde(),
            "statut": self.get_statut(),
        }


class PaiementService:
    """Service métier centralisant la validation et l'enregistrement des paiements."""

    def __init__(self, eleve_service: Optional[EleveService] = None):
        self.eleve_service = eleve_service or EleveService()

    def valider_paiement(self, montant: float) -> bool:
        if self.eleve_service is None:
            raise ValueError("Aucun élève associé au service de paiement.")
        return self.eleve_service.valider_paiement(montant)

    def enregistrer(
        self,
        montant: float,
        eleve: Optional[Dict[str, Any]] = None,
        reference: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Enregistre un paiement pour un élève donné ou l'élève courant."""
        if eleve is not None:
            self.eleve_service = EleveService(eleve)
        if self.eleve_service is None:
            raise ValueError("Aucun élève associé au paiement à enregistrer.")
        return self.eleve_service.enregistrer_paiement(montant, reference=reference)

    def get_solde(self) -> float:
        if self.eleve_service is None:
            return 0.0
        return self.eleve_service.get_solde()


__all__ = [
    "EleveService",
    "PaiementService",
    "generate_receipt_number",
    "format_currency",
    "STATUS_MAP",
]