"""Dialogue de création et de modification d’un élève."""

from typing import Any

from PySide6.QtCore import QLocale, Signal
from PySide6.QtWidgets import (
	QDialog,
	QDialogButtonBox,
	QComboBox,
	QDoubleSpinBox,
	QFormLayout,
	QLabel,
	QLineEdit,
	QMessageBox,
	QVBoxLayout,
)

from buisiness.service import EleveService


class EleveFormDialog(QDialog):
	"""Formulaire réutilisable pour ajouter ou modifier un élève."""

	enregistrement_reussi = Signal(int)

	def __init__(
		self,
		eleve: dict[str, Any] | None = None,
		parent=None,
	) -> None:
		super().__init__(parent)
		self.eleve_id = int(eleve["id"]) if eleve and eleve.get("id") is not None else None
		self.setWindowTitle("Modifier un élève" if self.eleve_id is not None else "Ajouter un élève")
		self.setModal(True)
		self.setMinimumWidth(430)
		self._construire_interface()
		if eleve is not None:
			self._charger_eleve(eleve)

	def _construire_interface(self) -> None:
		layout = QVBoxLayout(self)
		layout.setContentsMargins(24, 22, 24, 20)
		layout.setSpacing(16)

		titre = QLabel("Informations de l’élève")
		titre.setObjectName("dialogTitle")
		layout.addWidget(titre)

		formulaire = QFormLayout()
		formulaire.setLabelAlignment(formulaire.labelAlignment())
		formulaire.setHorizontalSpacing(16)
		formulaire.setVerticalSpacing(12)
		self.nom = QLineEdit()
		self.nom.setMaxLength(80)
		self.nom.setPlaceholderText("Nom de famille")
		self.prenom = QLineEdit()
		self.prenom.setMaxLength(80)
		self.prenom.setPlaceholderText("Prénom")
		self.classe = QComboBox()
		self.classe.setEditable(True)
		self.classe.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
		self.classe.setMaxCount(40)
		self.classe.addItems(
			[
				"CP",
				"CE1",
				"CE2",
				"CM1",
				"CM2",
				"6e",
				"5e",
				"4e",
				"3e",
				"Seconde",
				"Première",
				"Terminale",
			]
		)
		self.classe.setEditable(True)
		self.classe.setMinimumContentsLength(12)
		self.annee_scolaire = QLineEdit()
		self.annee_scolaire.setMaxLength(20)
		self.annee_scolaire.setPlaceholderText("Ex. 2025-2026")
		self.total_du = QDoubleSpinBox()
		self.total_du.setLocale(QLocale("fr_FR"))
		self.total_du.setRange(0, 1_000_000_000)
		self.total_du.setDecimals(2)
		self.total_du.setSingleStep(1000)
		self.total_du.setSuffix(" FCFA")
		self.total_du.setKeyboardTracking(False)

		formulaire.addRow("Nom *", self.nom)
		formulaire.addRow("Prénom *", self.prenom)
		formulaire.addRow("Classe *", self.classe)
		formulaire.addRow("Année scolaire *", self.annee_scolaire)
		formulaire.addRow("Frais dus *", self.total_du)
		layout.addLayout(formulaire)

		self.erreur = QLabel("")
		self.erreur.setObjectName("formError")
		self.erreur.setWordWrap(True)
		self.erreur.hide()
		layout.addWidget(self.erreur)

		self.boutons = QDialogButtonBox(
			QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
		)
		self.boutons.button(QDialogButtonBox.StandardButton.Save).setText("Enregistrer")
		self.boutons.button(QDialogButtonBox.StandardButton.Cancel).setText("Annuler")
		self.boutons.accepted.connect(self._enregistrer)
		self.boutons.rejected.connect(self.reject)
		layout.addWidget(self.boutons)

		self.setStyleSheet(
			"""
			QDialog { background: #F4F7F5; color: #1D2A29; }
			QLabel#dialogTitle { font-size: 19px; font-weight: 700; color: #173B39; }
			QLineEdit, QComboBox, QDoubleSpinBox { min-height: 36px; padding: 0 9px; background: #FFFFFF; border: 1px solid #D6E0DC; border-radius: 4px; }
			QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus { border: 1px solid #2878A0; }
			QLabel#formError { color: #A53F38; }
			QPushButton { min-height: 34px; padding: 0 12px; }
			"""
		)

	def _charger_eleve(self, eleve: dict[str, Any]) -> None:
		self.nom.setText(str(eleve.get("nom", "")))
		self.prenom.setText(str(eleve.get("prenom", "")))
		self.classe.setCurrentText(str(eleve.get("classe", "")))
		self.annee_scolaire.setText(str(eleve.get("annee_scolaire", "")))
		self.total_du.setValue(float(eleve.get("total_du", 0)))

	def _enregistrer(self) -> None:
		champs = (
			("nom", self.nom.text()),
			("prénom", self.prenom.text()),
			("classe", self.classe.currentText()),
			("année scolaire", self.annee_scolaire.text()),
		)
		manquant = next((libelle for libelle, valeur in champs if not valeur.strip()), None)
		if manquant is not None:
			self._afficher_erreur(f"Le champ « {manquant} » est obligatoire.")
			return

		montant = self.total_du.value()
		if montant <= 0:
			self._afficher_erreur("Le montant total des frais doit être supérieur à zéro.")
			return

		try:
			if self.eleve_id is None:
				eleve_id = EleveService.ajouter(
					self.nom.text().strip(),
					self.prenom.text().strip(),
					self.classe.currentText().strip(),
					self.annee_scolaire.text().strip(),
					montant,
				)
			else:
				details = EleveService.obtenir(self.eleve_id)
				total_paye = sum(float(paiement["montant"]) for paiement in details["paiements"])
				if montant < total_paye:
					self._afficher_erreur(
						f"Le total des frais ne peut pas être inférieur aux paiements déjà reçus ({self._monnaie(total_paye)})."
					)
					return
				EleveService.modifier(
					self.eleve_id,
					self.nom.text().strip(),
					self.prenom.text().strip(),
					self.classe.currentText().strip(),
					self.annee_scolaire.text().strip(),
					montant,
				)
				eleve_id = self.eleve_id
		except (ValueError, OSError) as exc:
			self._afficher_erreur(str(exc))
			return
		except Exception as exc:
			QMessageBox.critical(
				self,
				"Enregistrement impossible",
				f"L’élève n’a pas pu être enregistré.\n\n{exc}",
			)
			return

		self.enregistrement_reussi.emit(int(eleve_id))
		self.accept()

	def _afficher_erreur(self, message: str) -> None:
		self.erreur.setText(message)
		self.erreur.show()

	@staticmethod
	def _monnaie(montant: float) -> str:
		texte = f"{montant:,.2f}".replace(",", " ").replace(".", ",")
		return f"{texte} FCFA"
