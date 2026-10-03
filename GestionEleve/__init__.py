"""Interface PySide6 de l'application EduPaie.

Les vues sont chargées à la demande pour éviter les imports circulaires
et permettre d'importer le package sans initialiser toutes les fenêtres.
"""

from importlib import import_module
from typing import Any

_EXPORTS = {
	"MainWindow": ".main_window",
	"DashboardWidget": ".dashboard",
	"EleveDetailWidget": ".eleve_detail",
	"EleveFormDialog": ".elve_form",
	"PaiementDialog": ".paiement_dialogue",
}

__all__ = list(_EXPORTS)


def __getattr__(name: str) -> Any:
	"""Charge une vue uniquement lorsqu'elle est demandée."""
	module_name = _EXPORTS.get(name)
	if module_name is None:
		raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

	module = import_module(module_name, __name__)
	try:
		return getattr(module, name)
	except AttributeError as exc:
		raise AttributeError(
			f"La classe {name!r} doit être définie dans {module_name}.py"
		) from exc
