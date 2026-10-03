"""Tableau de bord et liste filtrable des élèves."""

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
	QComboBox,
	QFrame,
	QGridLayout,
	QHBoxLayout,
	QLabel,
	QLineEdit,
	QMessageBox,
	QTableWidget,
	QTableWidgetItem,
	QVBoxLayout,
	QWidget,
)

from buisiness.service import EleveService


class DashboardWidget(QWidget):
	"""Affiche les indicateurs de caisse et les élèves à suivre."""

	eleve_selectionne = Signal(int)

	def __init__(self, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self.setObjectName("dashboard")
		self._eleves: list[dict[str, Any]] = []
		self._construire_interface()
		self.rafraichir()

	def _construire_interface(self) -> None:
		layout = QVBoxLayout(self)
		layout.setContentsMargins(28, 24, 28, 28)
		layout.setSpacing(18)

		titre = QLabel("Vue d’ensemble")
		titre.setObjectName("pageTitle")
		sous_titre = QLabel("Suivi des inscriptions et des encaissements")
		sous_titre.setObjectName("pageSubtitle")
		layout.addWidget(titre)
		layout.addWidget(sous_titre)

		indicateurs = QGridLayout()
		indicateurs.setHorizontalSpacing(12)
		indicateurs.setVerticalSpacing(12)
		self._valeurs_indicateurs: dict[str, QLabel] = {}
		cartes = (
			("eleves", "Élèves inscrits", "#176B67"),
			("encaisse", "Total encaissé", "#2878A0"),
			("reste", "Reste à encaisser", "#C47A22"),
			("non_soldes", "Élèves non soldés", "#B64A42"),
		)
		for index, (cle, libelle, couleur) in enumerate(cartes):
			carte, valeur = self._creer_carte(libelle, couleur)
			self._valeurs_indicateurs[cle] = valeur
			indicateurs.addWidget(carte, 0, index)
		layout.addLayout(indicateurs)

		filtres = QHBoxLayout()
		filtres.setSpacing(10)
		self.recherche = QLineEdit()
		self.recherche.setClearButtonEnabled(True)
		self.recherche.setPlaceholderText("Rechercher un élève ou une classe")
		self.filtre_classe = QComboBox()
		self.filtre_classe.addItem("Toutes les classes", "")
		self.filtre_statut = QComboBox()
		self.filtre_statut.addItem("Tous les états", "")
		for statut in ("Non payé", "Partiellement payé", "Soldé"):
			self.filtre_statut.addItem(statut, statut)
		filtres.addWidget(self.recherche, 1)
		filtres.addWidget(self.filtre_classe)
		filtres.addWidget(self.filtre_statut)
		layout.addLayout(filtres)

		self.table = QTableWidget(0, 6)
		self.table.setHorizontalHeaderLabels(
			["Élève", "Classe", "Année scolaire", "Frais dus", "Reste dû", "État"]
		)
		self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
		self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
		self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
		self.table.setAlternatingRowColors(True)
		self.table.setShowGrid(False)
		self.table.verticalHeader().setVisible(False)
		self.table.horizontalHeader().setStretchLastSection(True)
		self.table.horizontalHeader().setSectionResizeMode(
			0, self.table.horizontalHeader().ResizeMode.Stretch
		)
		self.table.setMinimumHeight(300)
		layout.addWidget(self.table, 1)

		self.recherche.textChanged.connect(self._afficher_eleves)
		self.filtre_classe.currentIndexChanged.connect(self._afficher_eleves)
		self.filtre_statut.currentIndexChanged.connect(self._afficher_eleves)
		self.table.cellDoubleClicked.connect(self._ouvrir_fiche)

		self.setStyleSheet(
			"""
			QWidget#dashboard { background: #F4F7F5; color: #1D2A29; }
			QLabel#pageTitle { font-size: 25px; font-weight: 700; color: #173B39; }
			QLabel#pageSubtitle { color: #687875; font-size: 13px; }
			QFrame[metricCard="true"] { background: #FFFFFF; border: 1px solid #E0E8E5; border-radius: 6px; }
			QLineEdit, QComboBox { min-height: 36px; padding: 0 10px; background: #FFFFFF; border: 1px solid #D6E0DC; border-radius: 4px; }
			QTableWidget { background: #FFFFFF; alternate-background-color: #F7FAF8; border: 1px solid #E0E8E5; border-radius: 5px; selection-background-color: #DDEEEA; selection-color: #173B39; }
			QHeaderView::section { background: #EAF1EE; color: #40534F; padding: 9px 8px; border: none; font-weight: 600; }
			"""
		)

	@staticmethod
	def _creer_carte(libelle: str, couleur: str) -> tuple[QFrame, QLabel]:
		carte = QFrame()
		carte.setProperty("metricCard", True)
		carte.setMinimumHeight(92)
		carte.setStyleSheet(
			f"QFrame[metricCard='true'] {{ border-top: 3px solid {couleur}; }}"
		)
		contenu = QVBoxLayout(carte)
		contenu.setContentsMargins(14, 12, 14, 12)
		contenu.setSpacing(6)
		nom = QLabel(libelle)
		nom.setStyleSheet("color: #687875; font-size: 12px;")
		valeur = QLabel("—")
		valeur.setStyleSheet(f"color: {couleur}; font-size: 21px; font-weight: 700;")
		contenu.addWidget(nom)
		contenu.addWidget(valeur)
		return carte, valeur

	def rafraichir(self) -> None:
		"""Recharge les données et actualise les indicateurs et les filtres."""
		try:
			self._eleves = EleveService.lister()
		except Exception as exc:
			QMessageBox.critical(
				self,
				"Chargement impossible",
				f"Les données du tableau de bord n’ont pas pu être chargées.\n\n{exc}",
			)
			self._eleves = []

		total_encaisse = sum(
			max(0.0, float(eleve["total_du"]) - float(eleve["solde"]))
			for eleve in self._eleves
		)
		total_restant = sum(float(eleve["solde"]) for eleve in self._eleves)
		non_soldes = sum(eleve["statut"] != "Soldé" for eleve in self._eleves)
		self._valeurs_indicateurs["eleves"].setText(str(len(self._eleves)))
		self._valeurs_indicateurs["encaisse"].setText(self._monnaie(total_encaisse))
		self._valeurs_indicateurs["reste"].setText(self._monnaie(total_restant))
		self._valeurs_indicateurs["non_soldes"].setText(str(non_soldes))

		classe_selectionnee = self.filtre_classe.currentData()
		classes = sorted({str(eleve["classe"]) for eleve in self._eleves}, key=str.casefold)
		self.filtre_classe.blockSignals(True)
		self.filtre_classe.clear()
		self.filtre_classe.addItem("Toutes les classes", "")
		for classe in classes:
			self.filtre_classe.addItem(classe, classe)
		index = self.filtre_classe.findData(classe_selectionnee)
		self.filtre_classe.setCurrentIndex(max(index, 0))
		self.filtre_classe.blockSignals(False)
		self._afficher_eleves()

	def _afficher_eleves(self, *_: object) -> None:
		recherche = self.recherche.text().strip().casefold()
		classe = self.filtre_classe.currentData()
		statut = self.filtre_statut.currentData()
		eleves = [
			eleve
			for eleve in self._eleves
			if (not recherche or recherche in f"{eleve['nom']} {eleve['prenom']} {eleve['classe']}".casefold())
			and (not classe or eleve["classe"] == classe)
			and (not statut or eleve["statut"] == statut)
		]
		self.table.setRowCount(len(eleves))
		for row, eleve in enumerate(eleves):
			valeurs = (
				f"{eleve['prenom']} {eleve['nom']}",
				str(eleve["classe"]),
				str(eleve["annee_scolaire"]),
				self._monnaie(float(eleve["total_du"])),
				self._monnaie(float(eleve["solde"])),
				str(eleve["statut"]),
			)
			for column, texte in enumerate(valeurs):
				item = QTableWidgetItem(texte)
				item.setData(Qt.ItemDataRole.UserRole, int(eleve["id"]))
				if column in (3, 4):
					item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
				if column == 5:
					couleur = {
						"Soldé": "#176B67",
						"Partiellement payé": "#A76312",
						"Non payé": "#A53F38",
					}.get(str(eleve["statut"]), "#40534F")
					item.setForeground(QColor(couleur))
				self.table.setItem(row, column, item)

	def _ouvrir_fiche(self, row: int, _column: int) -> None:
		item = self.table.item(row, 0)
		if item is not None:
			self.eleve_selectionne.emit(int(item.data(Qt.ItemDataRole.UserRole)))

	@staticmethod
	def _monnaie(montant: float) -> str:
		texte = f"{montant:,.2f}".replace(",", " ").replace(".", ",")
		return f"{texte} €"
