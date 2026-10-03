"""Fenêtre principale EduPaie et orchestration des vues."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
	QHBoxLayout,
	QLabel,
	QMainWindow,
	QMessageBox,
	QPushButton,
	QStackedWidget,
	QStatusBar,
	QVBoxLayout,
	QWidget,
)

from buisiness.service import EleveService
from .dashboard import DashboardWidget
from .eleve_detail import EleveDetailWidget
from .elve_form import EleveFormDialog


class MainWindow(QMainWindow):
	"""Fenêtre de navigation entre le tableau de bord et les fiches élèves."""

	def __init__(self) -> None:
		super().__init__()
		self.setWindowTitle("EduPaie | Gestion des paiements scolaires")
		self.setMinimumSize(1050, 680)
		self.resize(1240, 780)
		self._eleve_id_courant: int | None = None
		self._construire_interface()

	def _construire_interface(self) -> None:
		contenu = QWidget()
		contenu.setObjectName("appRoot")
		principal = QHBoxLayout(contenu)
		principal.setContentsMargins(0, 0, 0, 0)
		principal.setSpacing(0)

		barre_laterale = QWidget()
		barre_laterale.setObjectName("sidebar")
		barre_laterale.setFixedWidth(218)
		navigation = QVBoxLayout(barre_laterale)
		navigation.setContentsMargins(18, 22, 18, 18)
		navigation.setSpacing(10)

		marque = QLabel("EduPaie")
		marque.setObjectName("brand")
		sous_marque = QLabel("GESTION SCOLAIRE")
		sous_marque.setObjectName("brandCaption")
		navigation.addWidget(marque)
		navigation.addWidget(sous_marque)
		navigation.addSpacing(26)

		self.bouton_tableau = QPushButton("Vue d’ensemble")
		self.bouton_tableau.setObjectName("navButton")
		self.bouton_eleves = QPushButton("Élèves et paiements")
		self.bouton_eleves.setObjectName("navButton")
		self.bouton_tableau.clicked.connect(self._afficher_tableau)
		self.bouton_eleves.clicked.connect(self._afficher_tableau)
		navigation.addWidget(self.bouton_tableau)
		navigation.addWidget(self.bouton_eleves)
		navigation.addStretch(1)

		pied_navigation = QLabel("Suivi des frais de scolarité")
		pied_navigation.setObjectName("sidebarFooter")
		pied_navigation.setWordWrap(True)
		navigation.addWidget(pied_navigation)
		principal.addWidget(barre_laterale)

		zone_principale = QWidget()
		zone_layout = QVBoxLayout(zone_principale)
		zone_layout.setContentsMargins(0, 0, 0, 0)
		zone_layout.setSpacing(0)

		barre_haute = QWidget()
		barre_haute.setObjectName("topbar")
		barre_haute.setFixedHeight(66)
		barre_layout = QHBoxLayout(barre_haute)
		barre_layout.setContentsMargins(24, 10, 24, 10)
		self.titre_section = QLabel("Vue d’ensemble")
		self.titre_section.setObjectName("sectionHeading")
		self.bouton_supprimer = QPushButton("Supprimer l’élève")
		self.bouton_supprimer.setObjectName("dangerButton")
		self.bouton_supprimer.clicked.connect(self._supprimer_selection)
		self.bouton_supprimer.hide()
		self.bouton_ajouter = QPushButton("＋  Ajouter un élève")
		self.bouton_ajouter.setObjectName("primaryButton")
		self.bouton_ajouter.clicked.connect(self._ajouter_eleve)
		barre_layout.addWidget(self.titre_section)
		barre_layout.addStretch(1)
		barre_layout.addWidget(self.bouton_supprimer)
		barre_layout.addWidget(self.bouton_ajouter)
		zone_layout.addWidget(barre_haute)

		self.pages = QStackedWidget()
		self.tableau = DashboardWidget()
		self.tableau.eleve_selectionne.connect(self._ouvrir_fiche)
		self.pages.addWidget(self.tableau)
		zone_layout.addWidget(self.pages, 1)
		principal.addWidget(zone_principale, 1)

		self.setCentralWidget(contenu)
		self.setStatusBar(QStatusBar())
		self.statusBar().showMessage("Prêt")
		self.setStyleSheet(
			"""
			QWidget#appRoot { background: #F4F7F5; color: #1D2A29; }
			QWidget#sidebar { background: #173B39; color: #FFFFFF; }
			QLabel#brand { color: #FFFFFF; font-size: 25px; font-weight: 700; }
			QLabel#brandCaption { color: #BBD0CB; font-size: 10px; font-weight: 600; }
			QLabel#sidebarFooter { color: #BBD0CB; font-size: 11px; }
			QPushButton#navButton { min-height: 40px; padding: 0 12px; text-align: left; color: #E7F0ED; background: transparent; border: none; border-radius: 4px; }
			QPushButton#navButton:hover { background: #285651; }
			QWidget#topbar { background: #FFFFFF; border-bottom: 1px solid #E0E8E5; }
			QLabel#sectionHeading { color: #173B39; font-size: 16px; font-weight: 700; }
			QPushButton#primaryButton { min-height: 38px; padding: 0 14px; color: #FFFFFF; background: #176B67; border: none; border-radius: 4px; font-weight: 600; }
			QPushButton#primaryButton:hover { background: #125A57; }
			QPushButton#dangerButton { min-height: 38px; padding: 0 12px; color: #A53F38; background: #FFFFFF; border: 1px solid #E5C9C5; border-radius: 4px; }
			QPushButton#dangerButton:hover { background: #F8E7E4; }
			"""
		)

	def _afficher_tableau(self) -> None:
		self._eleve_id_courant = None
		self.pages.setCurrentWidget(self.tableau)
		self.titre_section.setText("Vue d’ensemble")
		self.bouton_ajouter.show()
		self.bouton_supprimer.hide()
		self.tableau.rafraichir()

	def _ouvrir_fiche(self, eleve_id: int) -> None:
		self._eleve_id_courant = eleve_id
		fiche = EleveDetailWidget(eleve_id)
		fiche.retour_demande.connect(self._afficher_tableau)
		fiche.modification_demandee.connect(self._modifier_eleve)
		fiche.paiement_demande.connect(self._enregistrer_paiement)
		fiche.reimpression_recu_demandee.connect(self._reimprimer_recu)
		ancienne_page = self.pages.currentWidget()
		if ancienne_page is not self.tableau:
			self.pages.removeWidget(ancienne_page)
			ancienne_page.deleteLater()
		self.pages.addWidget(fiche)
		self.pages.setCurrentWidget(fiche)
		self.titre_section.setText("Fiche élève")
		self.bouton_ajouter.hide()
		self.bouton_supprimer.show()

	def _ajouter_eleve(self) -> None:
		dialogue = EleveFormDialog(parent=self)
		dialogue.enregistrement_reussi.connect(self._eleve_enregistre)
		dialogue.exec()

	def _modifier_eleve(self, eleve_id: int) -> None:
		try:
			eleve = EleveService.obtenir(eleve_id)
		except Exception as exc:
			self._afficher_erreur("Chargement impossible", exc)
			return
		dialogue = EleveFormDialog(eleve=eleve, parent=self)
		dialogue.enregistrement_reussi.connect(self._eleve_enregistre)
		dialogue.exec()

	def _eleve_enregistre(self, eleve_id: int) -> None:
		self.statusBar().showMessage("Les informations de l’élève ont été enregistrées.", 5000)
		self.tableau.rafraichir()
		if self._eleve_id_courant == eleve_id:
			self._ouvrir_fiche(eleve_id)

	def _supprimer_eleve(self, eleve_id: int) -> None:
		confirmation = QMessageBox.warning(
			self,
			"Supprimer cet élève ?",
			"Cette suppression peut également effacer son historique de paiements et les reçus associés. Continuer ?",
			QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
			QMessageBox.StandardButton.No,
		)
		if confirmation != QMessageBox.StandardButton.Yes:
			return
		try:
			EleveService.supprimer(eleve_id)
		except Exception as exc:
			self._afficher_erreur("Suppression impossible", exc)
			return
		self.statusBar().showMessage("L’élève a été supprimé.", 5000)
		self._afficher_tableau()

	def _supprimer_selection(self) -> None:
		if self._eleve_id_courant is not None:
			self._supprimer_eleve(self._eleve_id_courant)

	def _enregistrer_paiement(self, eleve_id: int) -> None:
		try:
			from .paiement_dialogue import PaiementDialog

			dialogue = PaiementDialog(eleve_id=eleve_id, parent=self)
		except (ImportError, TypeError) as exc:
			self._afficher_erreur(
				"Dialogue de paiement indisponible",
				f"Le dialogue doit accepter eleve_id et parent.\n\n{exc}",
			)
			return
		if dialogue.exec():
			self.statusBar().showMessage("Le paiement a été enregistré.", 5000)
			self.tableau.rafraichir()
			self._ouvrir_fiche(eleve_id)

	def _reimprimer_recu(self, paiement_id: int) -> None:
		"""Demande au dialogue de paiement de réouvrir le reçu existant."""
		try:
			from .paiement_dialogue import PaiementDialog

			dialogue = PaiementDialog(paiement_id=paiement_id, parent=self)
		except (ImportError, TypeError) as exc:
			self._afficher_erreur(
				"Réimpression indisponible",
				f"Le dialogue doit accepter paiement_id et parent.\n\n{exc}",
			)
			return
		dialogue.exec()

	@staticmethod
	def _afficher_erreur(titre: str, erreur: Exception | str) -> None:
		QMessageBox.critical(None, titre, str(erreur))
