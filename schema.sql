PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS Eleve (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	nom TEXT NOT NULL CHECK (length(trim(nom)) > 0),
	prenom TEXT NOT NULL CHECK (length(trim(prenom)) > 0),
	classe TEXT NOT NULL CHECK (length(trim(classe)) > 0),
	annee_scolaire TEXT NOT NULL CHECK (length(trim(annee_scolaire)) > 0),
	total_du REAL NOT NULL CHECK (total_du >= 0)
);

CREATE TABLE IF NOT EXISTS Paiement (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	eleve_id INTEGER NOT NULL,
	montant REAL NOT NULL CHECK (montant > 0),
	date_paiement TEXT NOT NULL
		CHECK (date_paiement GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
	mode TEXT NOT NULL
		CHECK (mode IN ('Espèces', 'Chèque', 'Virement', 'Mobile money')),
	numero_recu INTEGER NOT NULL UNIQUE CHECK (numero_recu > 0),
	solde_apres REAL NOT NULL CHECK (solde_apres >= 0),
	FOREIGN KEY (eleve_id) REFERENCES Eleve(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_eleve_nom_prenom
	ON Eleve(nom, prenom);

CREATE INDEX IF NOT EXISTS idx_eleve_classe
	ON Eleve(classe);

CREATE INDEX IF NOT EXISTS idx_paiement_eleve_date
	ON Paiement(eleve_id, date_paiement, id);
