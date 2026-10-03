"""Fiche détaillée d’un élève et historique de ses paiements."""

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
	QFrame,
	QGridLayout,
	QHBoxLayout,
	QLabel,
	QMessageBox,
	QPushButton,
	QTableWidget,
	QTableWidgetItem,
	QVBoxLayout,
	QWidget,
)

from buisiness.service import EleveService


class EleveDetailWidget(QWidget):
	"""Affiche les données d’un élève sans accéder directement à SQLite."""

	retour_demande = Signal()
	paiement_demande = Signal(int)
	reimpression_recu_demandee = Signal(int)
	modification_demandee = Signal(int)

	def __init__(self, eleve_id: int, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self.eleve_id = eleve_id
		self._eleve: dict[str, Any] | None = None
		self._construire_interface()
		self.rafraichir()

	def _construire_interface(self) -> None:
		layout = QVBoxLayout(self)
		layout.setContentsMargins(28, 24, 28, 28)
		layout.setSpacing(18)

		barre_actions = QHBoxLayout()
		self.bouton_retour = QPushButton("←  Retour à la liste")
		self.bouton_modifier = QPushButton("Modifier l’élève")
		self.bouton_paiement = QPushButton("＋  Enregistrer un paiement")
		barre_actions.addWidget(self.bouton_retour)
		barre_actions.addStretch(1)
		barre_actions.addWidget(self.bouton_modifier)
		barre_actions.addWidget(self.bouton_paiement)
		layout.addLayout(barre_actions)

		header = QHBoxLayout()
		noms = QVBoxLayout()
		self.nom_complet = QLabel("Fiche élève")
		self.nom_complet.setObjectName("pageTitle")
		self.sous_titre = QLabel("")
		self.sous_titre.setObjectName("pageSubtitle")
		noms.addWidget(self.nom_complet)
		noms.addWidget(self.sous_titre)
		self.statut = QLabel("—")
		self.statut.setAlignment(Qt.AlignmentFlag.AlignCenter)
		self.statut.setMinimumWidth(150)
		header.addLayout(noms, 1)
		header.addWidget(self.statut, 0, Qt.AlignmentFlag.AlignTop)
		layout.addLayout(header)

		infos = QFrame()
		infos.setObjectName("infoPanel")
		grille = QGridLayout(infos)
		grille.setContentsMargins(18, 16, 18, 16)
		grille.setHorizontalSpacing(28)
		grille.setVerticalSpacing(12)
		self.valeurs = {
			"nom": QLabel("—"),
			"prenom": QLabel("—"),
			"classe": QLabel("—"),
			"annee": QLabel("—"),
			"total": QLabel("—"),
			"solde": QLabel("—"),
		}
		champs = (
			("Nom", "nom"),
			("Prénom", "prenom"),
			("Classe", "classe"),
			("Année scolaire", "annee"),
			("Frais de scolarité", "total"),
			("Solde restant", "solde"),
		)
		for index, (libelle, cle) in enumerate(champs):
			colonne = index % 3
			ligne = (index // 3) * 2
			nom_champ = QLabel(libelle)
			nom_champ.setObjectName("fieldLabel")
			grille.addWidget(nom_champ, ligne, colonne)
			grille.addWidget(self.valeurs[cle], ligne + 1, colonne)
		layout.addWidget(infos)

		titre_historique = QLabel("Historique des paiements")
		titre_historique.setObjectName("sectionTitle")
		layout.addWidget(titre_historique)

		self.historique = QTableWidget(0, 5)
		self.historique.setHorizontalHeaderLabels(
			["Date", "N° reçu", "Montant versé", "Mode de paiement", "Solde après versement"]
		)
		self.historique.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
		self.historique.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
		self.historique.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
		self.historique.setAlternatingRowColors(True)
		self.historique.setShowGrid(False)
		self.historique.verticalHeader().setVisible(False)
		self.historique.horizontalHeader().setStretchLastSection(True)
		self.historique.setMinimumHeight(240)
		layout.addWidget(self.historique, 1)

		bas = QHBoxLayout()
		self.nombre_paiements = QLabel("Aucun paiement enregistré")
		self.bouton_reimprimer = QPushButton("Réimprimer le reçu sélectionné")
		self.bouton_reimprimer.setEnabled(False)
		bas.addWidget(self.nombre_paiements)
		bas.addStretch(1)
		bas.addWidget(self.bouton_reimprimer)
		layout.addLayout(bas)

		self.bouton_retour.clicked.connect(self.retour_demande.emit)
		self.bouton_modifier.clicked.connect(self._demander_modification)
		self.bouton_paiement.clicked.connect(self._demander_paiement)
		self.bouton_reimprimer.clicked.connect(self._demander_reimpression)
		self.historique.itemSelectionChanged.connect(self._actualiser_action_recu)
		self.historique.cellDoubleClicked.connect(self._demander_reimpression)

		self.setStyleSheet(
			"""
			QWidget { background: #F4F7F5; color: #1D2A29; }
			QLabel#pageTitle { font-size: 25px; font-weight: 700; color: #173B39; }
			QLabel#pageSubtitle { color: #687875; font-size: 13px; }
			QLabel#sectionTitle { font-size: 16px; font-weight: 700; color: #254B46; }
			QLabel#fieldLabel { color: #687875; font-size: 12px; }
			QFrame#infoPanel { background: #FFFFFF; border: 1px solid #E0E8E5; border-radius: 5px; }
			QPushButton { min-height: 34px; padding: 0 12px; background: #FFFFFF; border: 1px solid #D6E0DC; border-radius: 4px; }
			QPushButton:hover { background: #EAF1EE; }
			QPushButton#primaryAction { background: #176B67; color: #FFFFFF; border: none; font-weight: 600; }
			QTableWidget { background: #FFFFFF; alternate-background-color: #F7FAF8; border: 1px solid #E0E8E5; border-radius: 5px; selection-background-color: #DDEEEA; selection-color: #173B39; }
			QHeaderView::section { background: #EAF1EE; color: #40534F; padding: 9px 8px; border: none; font-weight: 600; }
			"""
		)
		self.bouton_paiement.setObjectName("primaryAction")

	def rafraichir(self) -> None:
		"""Recharge la fiche et l’historique depuis le service métier."""
		try:
			self._eleve = EleveService.obtenir(self.eleve_id)
		except Exception as exc:
			QMessageBox.critical(
				self,
				"Fiche indisponible",
				f"Les informations de cet élève n’ont pas pu être chargées.\n\n{exc}",
			)
			self._eleve = None
			self.historique.setRowCount(0)
			self.bouton_paiement.setEnabled(False)
			return

		eleve = self._eleve
		self.nom_complet.setText(f"{eleve['prenom']} {eleve['nom']}")
		self.sous_titre.setText(f"Élève n° {eleve['id']}  ·  {eleve['classe']}  ·  {eleve['annee_scolaire']}")
		for cle, valeur in (
			("nom", eleve["nom"]),
			("prenom", eleve["prenom"]),
			("classe", eleve["classe"]),
			("annee", eleve["annee_scolaire"]),
			("total", self._monnaie(float(eleve["total_du"]))),
			("solde", self._monnaie(float(eleve["solde"]))),
		):
			self.valeurs[cle].setText(str(valeur))

		statut = str(eleve["statut"])
		couleurs = {
			"Soldé": ("#E4F1EC", "#176B67"),
			"Partiellement payé": ("#FBF0DD", "#A76312"),
			"Non payé": ("#F8E7E4", "#A53F38"),
		}
		fond, encre = couleurs.get(statut, ("#EAF1EE", "#40534F"))
		self.statut.setText(statut)
		self.statut.setStyleSheet(
			f"background: {fond}; color: {encre}; padding: 7px 12px; border-radius: 4px; font-weight: 600;"
		)
		self.bouton_paiement.setEnabled(float(eleve["solde"]) > 0)

		paiements = list(eleve.get("paiements", []))
		self.historique.setRowCount(len(paiements))
		for ligne, paiement in enumerate(paiements):
			date_brute = str(paiement["date_paiement"])
			date_affichee = date_brute
			try:
				date_affichee = f"{date_brute[8:10]}/{date_brute[5:7]}/{date_brute[:4]}"
			except (IndexError, TypeError):
				pass
			colonnes = (
				date_affichee,
				f"R-{int(paiement['numero_recu']):06d}",
				self._monnaie(float(paiement["montant"])),
				str(paiement["mode"]),
				self._monnaie(float(paiement["solde_apres"])),
			)
			for colonne, texte in enumerate(colonnes):
				item = QTableWidgetItem(texte)
				item.setData(Qt.ItemDataRole.UserRole, int(paiement["id"]))
				if colonne in (2, 4):
					item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
				self.historique.setItem(ligne, colonne, item)
		self.nombre_paiements.setText(
			f"{len(paiements)} paiement(s) enregistré(s)" if paiements else "Aucun paiement enregistré"
		)
		self._actualiser_action_recu()

	def _actualiser_action_recu(self) -> None:
		self.bouton_reimprimer.setEnabled(bool(self.historique.selectedItems()))

	def _demander_paiement(self) -> None:
		if self._eleve is not None and float(self._eleve["solde"]) > 0:
			self.paiement_demande.emit(self.eleve_id)

	def _demander_modification(self) -> None:
		self.modification_demandee.emit(self.eleve_id)

	def _demander_reimpression(self, *_: object) -> None:
		selection = self.historique.selectedItems()
		if selection:
			self.reimpression_recu_demandee.emit(
				int(selection[0].data(Qt.ItemDataRole.UserRole))
			)

	@staticmethod
	def _monnaie(montant: float) -> str:
		texte = f"{montant:,.2f}".replace(",", " ").replace(".", ",")
		return f"{texte} FCFA"
