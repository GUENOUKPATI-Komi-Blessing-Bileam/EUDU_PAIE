"""Dialogue d’enregistrement d’un paiement et de génération de reçu PDF."""

from datetime import date
from pathlib import Path
from typing import Any

from PySide6.QtCore import QDate, QLocale, QUrl, Qt, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
	QComboBox,
	QDateEdit,
	QDialog,
	QDialogButtonBox,
	QDoubleSpinBox,
	QFormLayout,
	QLabel,
	QMessageBox,
	QPushButton,
	QVBoxLayout,
)


class PaiementDialog(QDialog):
	"""Saisit un paiement ou réédite un reçu sans requête SQL dans l’UI."""

	paiement_enregistre = Signal(int)

	def __init__(
		self,
		eleve_id: int | None = None,
		paiement_id: int | None = None,
		parent=None,
	) -> None:
		super().__init__(parent)
		if (eleve_id is None) == (paiement_id is None):
			raise ValueError("Fournir soit eleve_id, soit paiement_id.")
		self.eleve_id = eleve_id
		self.paiement_id = paiement_id
		self.mode_reimpression = paiement_id is not None
		self._eleve: dict[str, Any] = {}
		self._paiement: dict[str, Any] = {}
		self.setWindowTitle("Réimprimer un reçu" if self.mode_reimpression else "Enregistrer un paiement")
		self.setModal(True)
		self.setMinimumWidth(470)
		self._construire_interface()
		if self.mode_reimpression:
			self._charger_paiement()
		else:
			self._charger_eleve()

	def _construire_interface(self) -> None:
		layout = QVBoxLayout(self)
		layout.setContentsMargins(24, 22, 24, 20)
		layout.setSpacing(16)

		titre = QLabel(
			"Réédition du reçu" if self.mode_reimpression else "Nouveau versement"
		)
		titre.setObjectName("dialogTitle")
		layout.addWidget(titre)

		self.identite = QLabel("Chargement de l’élève…")
		self.identite.setObjectName("studentName")
		self.identite.setWordWrap(True)
		layout.addWidget(self.identite)

		self.solde_label = QLabel("")
		self.solde_label.setObjectName("balanceLabel")
		layout.addWidget(self.solde_label)

		formulaire = QFormLayout()
		formulaire.setHorizontalSpacing(16)
		formulaire.setVerticalSpacing(12)
		self.montant = QDoubleSpinBox()
		self.montant.setLocale(QLocale("fr_FR"))
		self.montant.setRange(0, 1_000_000_000)
		self.montant.setDecimals(2)
		self.montant.setSingleStep(1000)
		self.montant.setSuffix(" FCFA")
		self.montant.setKeyboardTracking(False)
		self.date_paiement = QDateEdit()
		self.date_paiement.setCalendarPopup(True)
		self.date_paiement.setDisplayFormat("dd/MM/yyyy")
		self.date_paiement.setDate(QDate.currentDate())
		self.mode = QComboBox()
		self.mode.addItems(["Espèces", "Chèque", "Virement", "Mobile money"])
		formulaire.addRow("Montant versé *", self.montant)
		formulaire.addRow("Date du paiement *", self.date_paiement)
		formulaire.addRow("Mode de paiement *", self.mode)
		layout.addLayout(formulaire)

		self.erreur = QLabel("")
		self.erreur.setObjectName("formError")
		self.erreur.setWordWrap(True)
		self.erreur.hide()
		layout.addWidget(self.erreur)

		self.boutons = QDialogButtonBox()
		self.bouton_action = QPushButton(
			"Générer le reçu PDF" if self.mode_reimpression else "Enregistrer et générer le reçu"
		)
		self.bouton_action.setObjectName("primaryAction")
		self.bouton_annuler = self.boutons.addButton(
			QDialogButtonBox.StandardButton.Cancel
		)
		self.bouton_annuler.setText("Fermer" if self.mode_reimpression else "Annuler")
		self.boutons.addButton(self.bouton_action, QDialogButtonBox.ButtonRole.AcceptRole)
		self.bouton_action.clicked.connect(self._valider_action)
		self.bouton_annuler.clicked.connect(self.reject)
		layout.addWidget(self.boutons)

		if self.mode_reimpression:
			self.montant.setReadOnly(True)
			self.date_paiement.setReadOnly(True)
			self.date_paiement.setButtonSymbols(QDateEdit.ButtonSymbols.NoButtons)
			self.mode.setEnabled(False)

		self.setStyleSheet(
			"""
			QDialog { background: #F4F7F5; color: #1D2A29; }
			QLabel#dialogTitle { font-size: 19px; font-weight: 700; color: #173B39; }
			QLabel#studentName { color: #254B46; font-size: 14px; font-weight: 600; }
			QLabel#balanceLabel { padding: 10px 12px; color: #176B67; background: #E4F1EC; border-radius: 4px; font-weight: 600; }
			QDoubleSpinBox, QDateEdit, QComboBox { min-height: 36px; padding: 0 9px; background: #FFFFFF; border: 1px solid #D6E0DC; border-radius: 4px; }
			QLabel#formError { color: #A53F38; }
			QPushButton { min-height: 34px; padding: 0 12px; }
			QPushButton#primaryAction { color: #FFFFFF; background: #176B67; border: none; border-radius: 4px; font-weight: 600; }
			QPushButton#primaryAction:hover { background: #125A57; }
			"""
		)

	def _charger_eleve(self) -> None:
		try:
			from buisiness.service import EleveService

			self._eleve = EleveService.obtenir(int(self.eleve_id))
		except Exception as exc:
			self._afficher_erreur(f"Les informations de l’élève sont indisponibles. {exc}")
			self.bouton_action.setEnabled(False)
			return
		self._afficher_identite()
		self.montant.setMaximum(max(0.0, float(self._eleve["solde"])))
		self.solde_label.setText(f"Solde restant : {self._monnaie(float(self._eleve['solde']))}")
		if float(self._eleve["solde"]) <= 0:
			self.bouton_action.setEnabled(False)
			self._afficher_erreur("Cet élève est déjà soldé.")

	def _charger_paiement(self) -> None:
		try:
			from buisiness.service import PaiementService

			resultat = PaiementService.obtenir_paiement(int(self.paiement_id))
			self._eleve, self._paiement = self._normaliser_recu(resultat)
		except Exception as exc:
			self._afficher_erreur(f"Les données du reçu sont indisponibles. {exc}")
			self.bouton_action.setEnabled(False)
			return

		self._afficher_identite()
		self.solde_label.setText(
			f"Reçu R-{int(self._paiement['numero_recu']):06d} · Solde après paiement : "
			f"{self._monnaie(float(self._paiement['solde_apres']))}"
		)
		self.montant.setValue(float(self._paiement["montant"]))
		self.date_paiement.setDate(self._date_qdate(self._paiement["date_paiement"]))
		index_mode = self.mode.findText(str(self._paiement["mode"]), Qt.MatchFlag.MatchFixedString)
		if index_mode < 0:
			index_mode = self.mode.findText(str(self._paiement["mode"]), Qt.MatchFlag.MatchContains)
		if index_mode >= 0:
			self.mode.setCurrentIndex(index_mode)

	def _valider_action(self) -> None:
		if self.mode_reimpression:
			chemin = self._generer_pdf()
			if chemin is not None:
				QMessageBox.information(
					self,
					"Reçu généré",
					f"Le reçu R-{int(self._paiement['numero_recu']):06d} est disponible ici :\n{chemin}",
				)
				self._ouvrir_pdf(chemin)
			return
		montant = self.montant.value()
		if montant <= 0:
			self._afficher_erreur("Le montant doit être supérieur à zéro.")
			return
		try:
			from buisiness.service import PaiementService, ReceiptGenerationError

			date_paiement = date(
				self.date_paiement.date().year(),
				self.date_paiement.date().month(),
				self.date_paiement.date().day(),
			)
			paiement_id = PaiementService.enregistrer_paiement(
				int(self.eleve_id),
				montant,
				date_paiement,
				self.mode.currentText(),
			)
			self.paiement_id = int(paiement_id)
			self._paiement = PaiementService.obtenir_paiement(self.paiement_id)
			self._eleve, self._paiement = self._normaliser_recu(self._paiement)
		except ReceiptGenerationError as exc:
			self.paiement_id = exc.paiement_id
			try:
				recu = PaiementService.obtenir_paiement(self.paiement_id)
				self._eleve, self._paiement = self._normaliser_recu(recu)
			except Exception:
				self._afficher_erreur(str(exc))
				return
			self.paiement_enregistre.emit(self.paiement_id)
			QMessageBox.warning(
				self,
				"Paiement enregistré, reçu indisponible",
				f"Le paiement est enregistré sous le reçu R-{int(self._paiement['numero_recu']):06d}, "
				f"mais le PDF n’a pas pu être créé.\n\n{exc}\n\n"
				"Le reçu pourra être régénéré depuis l’historique.",
			)
			self.accept()
			return
		except ValueError as exc:
			self._afficher_erreur(str(exc))
			return
		except Exception as exc:
			QMessageBox.critical(
				self,
				"Paiement non enregistré",
				f"Le paiement n’a pas pu être enregistré.\n\n{exc}",
			)
			return

		from buisiness.service import PaiementService
		chemin = PaiementService.chemin_recu(self.paiement_id)
		QMessageBox.information(
			self,
			"Paiement enregistré",
			f"Le paiement est enregistré.\nReçu : R-{int(self._paiement['numero_recu']):06d}\nPDF : {chemin}",
		)
		self._ouvrir_pdf(chemin)
		self.paiement_enregistre.emit(int(self.paiement_id))
		self.accept()

	def _generer_pdf(self) -> Path | None:
		try:
			from buisiness.service import PaiementService

			return PaiementService.generer_recu_pdf(int(self.paiement_id))
		except Exception as exc:
			self._afficher_erreur(f"Le PDF du reçu n’a pas pu être généré. {exc}")
			return None

	@staticmethod
	def _ouvrir_pdf(chemin: Path) -> None:
		"""Ouvre le reçu généré avec l’application PDF par défaut."""
		if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(chemin.resolve()))):
			QMessageBox.warning(
				None,
				"Ouverture impossible",
				f"Le reçu a été généré, mais aucun lecteur PDF n’a pu l’ouvrir.\n\n{chemin}",
			)

	def _afficher_identite(self) -> None:
		self.identite.setText(
			f"{self._eleve.get('prenom', '')} {self._eleve.get('nom', '')} · "
			f"{self._eleve.get('classe', '')} · {self._eleve.get('annee_scolaire', '')}"
		)

	def _afficher_erreur(self, message: str) -> None:
		self.erreur.setText(message)
		self.erreur.show()

	@staticmethod
	def _normaliser_recu(resultat: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
		if "eleve" in resultat and "paiement" in resultat:
			return dict(resultat["eleve"]), dict(resultat["paiement"])
		return dict(resultat), dict(resultat)

	@staticmethod
	def _date_qdate(valeur: Any) -> QDate:
		if isinstance(valeur, QDate):
			return valeur
		if isinstance(valeur, date):
			return QDate(valeur.year, valeur.month, valeur.day)
		return QDate.fromString(str(valeur), "yyyy-MM-dd")

	@staticmethod
	def _monnaie(montant: float) -> str:
		texte = f"{montant:,.2f}".replace(",", " ").replace(".", ",")
		return f"{texte} FCFA"