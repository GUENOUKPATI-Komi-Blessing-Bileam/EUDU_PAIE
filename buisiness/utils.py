"""
src.business.utils
~~~~~~~~~~~~~~~~~~
Fonctions utilitaires utilisées par les services métier et les vues.
Elles regroupent :

* génération du **numéro de reçu** séquentiel (unique dans la base)
* formatage monétaire (affichage « 12,34 FCFA »)
* calcul du **statut de paiement** (Soldé / Partiellement payé / Non payé)
* quelques petites aides de conversion de dates
"""

import datetime
from pathlib import Path
from typing import Tuple

from data.paiement_dao import PaiementDAO


# ----------------------------------------------------------------------
# Numéro de reçu
# ----------------------------------------------------------------------
def generate_receipt_number() -> int:
    """
    Retourne le prochain numéro de reçu à utiliser.

    La fonction interroge la table `Paiement` pour connaître le plus grand
    `numero_recu` déjà enregistré puis incrémente de 1.
    Elle est encapsulée dans une transaction au niveau du service
    `PaiementService.enregistrer_paiement` afin d’éviter les collisions
    en cas d’appels concurrents (ex. : deux threads UI).
    """
    last_num = PaiementDAO.last_receipt_number()
    return last_num + 1


# ----------------------------------------------------------------------
# Formattage monétaire
# ----------------------------------------------------------------------
def format_currency(amount: float, locale: str = "fr_FR") -> str:
    """
    Formatte un montant en FCFA avec deux décimales et le séparateur
    décimal français.  Exemple : 1234.5 → « 1 234,50 FCFA ».

    Le paramètre `locale` n’est utilisé que pour choisir le séparateur.
    Si la locale n’est pas disponible, on retombe sur le format
    « 1234,56 FCFA ».
    """
    # On évite d’importer le module `locale` (qui dépend du système).
    # On se contente d’un remplacement simple.
    integer_part, decimal_part = f"{amount:,.2f}".split(".")
    # Le séparateur de milliers anglais (',') devient un espace insécable
    integer_part = integer_part.replace(",", " ")
    # Le point décimal devient une virgule
    formatted = f"{integer_part},{decimal_part} FCFA"
    return formatted


# ----------------------------------------------------------------------
# Statut de paiement
# ----------------------------------------------------------------------
def STATUS_MAP(solde: float, total_du: float) -> str:
    """
    Retourne une chaîne lisible décrivant le statut de paiement :

    * **Soldé**            → solde == 0
    * **Partiellement payé** → 0 < solde < total_du
    * **Non payé**        → solde == total_du

    Les valeurs sont arrondies à 2 décimales pour éviter les effets de
    flottants.
    """
    solde = round(solde, 2)
    total_du = round(total_du, 2)

    if solde == 0:
        return "Soldé"
    if solde == total_du:
        return "Non payé"
    return "Partiellement payé"


# ----------------------------------------------------------------------
# Conversion de date <-> string (ISO 8601)
# ----------------------------------------------------------------------
def date_to_str(d: datetime.date) -> str:
    """ISO‑8601 (YYYY‑MM‑DD) – utilisé pour le stockage SQLite."""
    return d.isoformat()


def str_to_date(s: str) -> datetime.date:
    """Parse une chaîne ISO‑8601 en `datetime.date`."""
    return datetime.datetime.strptime(s, "%Y-%m-%d").date()


# ----------------------------------------------------------------------
# Chemin du répertoire des ressources (icônes, templates PDF, …)
# ----------------------------------------------------------------------
def resources_path(*subpaths: str) -> Path:
    """
    Retourne le chemin absolu du répertoire `resources/` (situé à la racine
    du projet) quel que soit le contexte d’exécution (script ou exécutable
    PyInstaller).

    Exemple :
        tmpl = resources_path("templates", "receipt_template.html")
    """
    base = Path(__file__).resolve().parent.parent / "resources"
    return base.joinpath(*subpaths)


# ----------------------------------------------------------------------
# Export du module
# ----------------------------------------------------------------------
__all__ = [
    "generate_receipt_number",
    "format_currency",
    "STATUS_MAP",
    "date_to_str",
    "str_to_date",
    "resources_path",
]