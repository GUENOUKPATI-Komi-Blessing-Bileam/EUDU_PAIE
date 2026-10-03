"""Création des reçus PDF EduPaie avec les outils d’impression Qt."""

from html import escape
from pathlib import Path
from typing import Any

from PySide6.QtCore import QStandardPaths
from PySide6.QtGui import QTextDocument
from PySide6.QtPrintSupport import QPrinter


def create_receipt_pdf(
	eleve: dict[str, Any],
	paiement: dict[str, Any],
	output_path: str | Path | None = None,
) -> Path:
	"""Génère un reçu PDF lisible et le retourne sous forme de chemin.

	Le dictionnaire ``paiement`` doit contenir ``numero_recu``, ``montant``,
	``date_paiement``, ``mode`` et ``solde_apres``. Le dictionnaire ``eleve``
	contient au minimum ``nom`` et ``prenom``.
	"""
	champs_paiement = ("numero_recu", "montant", "date_paiement", "mode", "solde_apres")
	champs_eleve = ("nom", "prenom")
	manquants = [
		f"paiement.{cle}" for cle in champs_paiement if cle not in paiement
	] + [f"eleve.{cle}" for cle in champs_eleve if cle not in eleve]
	if manquants:
		raise ValueError("Données de reçu manquantes : " + ", ".join(manquants))

	numero = int(paiement["numero_recu"])
	if numero <= 0:
		raise ValueError("Le numéro du reçu doit être positif.")

	output = receipt_pdf_path(numero, output_path)
	output.parent.mkdir(parents=True, exist_ok=True)
	printer = QPrinter(QPrinter.PrinterMode.HighResolution)
	printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
	printer.setOutputFileName(str(output))
	document = QTextDocument()
	document.setHtml(_receipt_html(eleve, paiement))
	document.print_(printer)
	return output


def receipt_pdf_path(
	numero_recu: int,
	output_path: str | Path | None = None,
) -> Path:
	"""Retourne le chemin prévu pour le reçu, sans créer le fichier."""
	if numero_recu <= 0:
		raise ValueError("Le numéro du reçu doit être positif.")
	if output_path is None:
		documents = Path(
			QStandardPaths.writableLocation(
				QStandardPaths.StandardLocation.DocumentsLocation
			)
		)
		return documents / "EduPaie" / "Recus" / f"Recu-{numero_recu:06d}.pdf"

	output = Path(output_path)
	return output if output.suffix.lower() == ".pdf" else output.with_suffix(".pdf")


def generer_recu_pdf(
	eleve: dict[str, Any],
	paiement: dict[str, Any],
	chemin_sortie: str | Path | None = None,
) -> Path:
	"""Alias français de ``create_receipt_pdf``."""
	return create_receipt_pdf(eleve, paiement, chemin_sortie)


def _receipt_html(eleve: dict[str, Any], paiement: dict[str, Any]) -> str:
	numero = int(paiement["numero_recu"])
	nom = escape(f"{eleve['prenom']} {eleve['nom']}".strip())
	classe = escape(str(eleve.get("classe", "")))
	annee = escape(str(eleve.get("annee_scolaire", "")))
	date_paiement = escape(_format_date(paiement["date_paiement"]))
	mode = escape(str(paiement["mode"]))
	montant = _format_currency(float(paiement["montant"]))
	solde = _format_currency(float(paiement["solde_apres"]))
	return f"""
	<html><head><meta charset="utf-8"><style>
	body {{ font-family: Arial, sans-serif; color: #1D2A29; font-size: 11pt; }}
	h1 {{ color: #176B67; font-size: 24pt; margin-bottom: 4px; }}
	.muted {{ color: #687875; }}
	.amount {{ font-size: 20pt; font-weight: bold; color: #173B39; }}
	table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
	td {{ padding: 10px 6px; border-bottom: 1px solid #D6E0DC; }}
	</style></head><body>
	<h1>REÇU DE PAIEMENT</h1>
	<p class="muted">EduPaie · Gestion des paiements scolaires</p>
	<p><b>Numéro :</b> R-{numero:06d}</p>
	<table>
	<tr><td>Élève</td><td><b>{nom}</b></td></tr>
	<tr><td>Classe</td><td>{classe}</td></tr>
	<tr><td>Année scolaire</td><td>{annee}</td></tr>
	<tr><td>Date du paiement</td><td>{date_paiement}</td></tr>
	<tr><td>Mode de paiement</td><td>{mode}</td></tr>
	<tr><td>Montant versé</td><td class="amount">{montant}</td></tr>
	<tr><td>Solde restant après paiement</td><td><b>{solde}</b></td></tr>
	</table>
	<p class="muted">Reçu généré par EduPaie. À conserver comme justificatif de paiement.</p>
	</body></html>
	"""


def _format_date(value: Any) -> str:
	date_iso = str(value)
	if len(date_iso) >= 10 and date_iso[4] == "-":
		return f"{date_iso[8:10]}/{date_iso[5:7]}/{date_iso[:4]}"
	return date_iso


def _format_currency(amount: float) -> str:
	formatted = f"{amount:,.2f}".replace(",", " ").replace(".", ",")
	return f"{formatted} €"


__all__ = ["create_receipt_pdf", "generer_recu_pdf", "receipt_pdf_path"]
