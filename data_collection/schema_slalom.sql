-- ============================================================
-- Base de données : classement slalom FFCK (CNA Slalom) — schéma v2
-- Compatible SQLite ; les commentaires expliquent les choix.
-- Utilisation : sqlite3 classement.db < schema_slalom_v2.sql
--
-- Changements par rapport à la v1 (schema_slalom.sql) :
--  * COURSE ne contient plus temps_base / coefficient / methode_points_id.
--    Ces éléments appartiennent à la méthode de calcul des points de la
--    FFCK : ils sont stockés dans COURSE_METHODE_FFCK. L'identifiant brut
--    de la méthode API ("pointsCalculationMethodId", ex "2026") est
--    conservé en texte libre dans COURSE.points_calculation_method_id.
--  * RESULTAT ne contient plus rang / points / valeur :
--    - rang est recalculable à la volée (voir commentaire sur RESULTAT) ;
--    - points / valeur, calculés par la méthode FFCK, sont stockés dans
--      RESULTAT_METHODE_FFCK.
--  * Tables CATEGORIE et METHODE_POINTS supprimées : categorie_code reste
--    un code brut (texte libre) sur RESULTAT ; la catégorie d'âge se
--    recalcule depuis bateau.annee_naissance + l'année de la compétition.
--
-- Pour tester une AUTRE méthode de classement, aucune modification de ce
-- schéma n'est nécessaire : créer des tables dédiées à cette méthode
-- (ex. course_methode_test, resultat_methode_test) avec la forme propre
-- à la méthode — voir exemple_methode_test.py.
-- ============================================================

PRAGMA foreign_keys = ON;

-- ------------------------------------------------------------
-- Référentiels
-- ------------------------------------------------------------

CREATE TABLE competiteur (
    id      INTEGER PRIMARY KEY,
    id_api  TEXT UNIQUE,            -- id de la fiche personne sur l'API (ex "270346")
    nom     TEXT NOT NULL,
    prenom  TEXT
);

CREATE TABLE club (
    id      INTEGER PRIMARY KEY,
    id_api  TEXT UNIQUE,            -- code club FFCK (ex "080003")
    nom     TEXT                    -- parfois chaîne vide dans la source
);

-- Types de bateau : K1H, K1D, C1H, C2H, C2M, INV, variantes M (mixtes)...
CREATE TABLE type_bateau (
    id      INTEGER PRIMARY KEY,
    code    TEXT UNIQUE NOT NULL,   -- ex "K1H"
    nom     TEXT
);

-- ------------------------------------------------------------
-- Compétitions et courses
-- ------------------------------------------------------------

CREATE TABLE competition (
    id          INTEGER PRIMARY KEY,
    id_api      TEXT UNIQUE NOT NULL,   -- id de l'API (ex "4623")
    id_externe  TEXT UNIQUE,            -- "foreignId" (ex "ffck-FFCK20260985") ; NULL si absent ou "0"
                                        -- (les vieux events ont foreignId "0" répété ; le script stocke NULL)
    nom         TEXT,
    lieu        TEXT,
    date_debut  TEXT,                   -- "startDate", parfois null (2001-2015)
    date_fin    TEXT,                   -- "date", parfois null (2001-2015)
    niveau      INTEGER                  -- 1 régional, 2 N3, 4 N1, 5 Championnats...
);

CREATE TABLE course (
    id                  INTEGER PRIMARY KEY,
    id_api              TEXT UNIQUE NOT NULL,  -- id de la course (ex "20121031")
    competition_id      INTEGER NOT NULL REFERENCES competition(id),
    nom                 TEXT,                  -- "Course n°1", "Qualification"...
    date                TEXT,
    nb_portes           INTEGER,               -- "gateNumber", parfois null
    penalites_completes INTEGER,               -- "fullPenalties" (booléen 0/1)
    points_calculation_method_id TEXT,         -- "pointsCalculationMethodId" brut (ex "2026"), null avant 2025
    -- Phase de compétition, déduite du NOM de la course via le mapping
    -- phases_courses.json (pas de classification automatique) :
    phase_competition   TEXT CHECK (phase_competition IN ('qualification', 'demi-finale', 'finale')),
                                            -- NULL = pas de phase
    -- Priorité de traitement des courses d'une compétition :
    phase_ordre         REAL NOT NULL DEFAULT 0
                                            -- 0 = pas de phase, 0.k = "Course n°k"
                                            -- (0.1, 0.2, 0.3...), 1 = qualification,
                                            -- 2 = demi-finale, 3 = finale
);

-- Paramètres de la méthode de calcul FFCK propres à chaque course.
-- (avant v2 : colonnes temps_base / coefficient de COURSE)
-- Un seul champ details (JSON sérialisé), cohérent avec les autres méthodes
-- de points (course_methode_<nom>) :
--   {"tpsBase": <baseTime>, "coefficientCourse": <coefficient>}
CREATE TABLE course_methode_ffck (
    course_id   INTEGER PRIMARY KEY REFERENCES course(id) ON DELETE CASCADE,
    details     TEXT      -- JSON sérialisé, ex {"tpsBase": 76.79, "coefficientCourse": 0.999}
);

-- ------------------------------------------------------------
-- Bateaux (les participants réels : monoplaces et équipages C2)
-- ------------------------------------------------------------

CREATE TABLE bateau (
    id               INTEGER PRIMARY KEY,
    id_api           TEXT UNIQUE NOT NULL,  -- ex "C1H270346"
    libelle          TEXT,                  -- noms séparés par un saut de ligne si C2
    type_code        TEXT REFERENCES type_bateau(code),
    annee_naissance  INTEGER,               -- fiche /ffck/boats, champ slalom.year
    niveau           TEXT,                  -- niveau national du bateau ("N2", "Reg"...)
    surclassement     INTEGER                -- -1, 0 ou 1 depuis la fiche
);

-- Composition d'équipage (1 ligne par membre, position 1..2).
-- club_id = club du membre pour ce bateau : depuis quelques années, un C2
-- peut réunir deux membres de clubs différents (équipages mixtes), d'où le
-- club porté par le membre (bateau_competiteur.club_id) et non par le bateau.
CREATE TABLE bateau_competiteur (
    bateau_id      INTEGER NOT NULL REFERENCES bateau(id),
    competiteur_id INTEGER NOT NULL REFERENCES competiteur(id),
    position       INTEGER NOT NULL,
    club_id        INTEGER REFERENCES club(id),
    PRIMARY KEY (bateau_id, competiteur_id)
);

-- ------------------------------------------------------------
-- Résultats, manches et pénalités
-- ------------------------------------------------------------

CREATE TABLE resultat (
    id                      INTEGER PRIMARY KEY,
    id_api                  TEXT UNIQUE,        -- "_id" dans la réponse API
    course_id               INTEGER NOT NULL REFERENCES course(id),
    bateau_id               INTEGER NOT NULL REFERENCES bateau(id),
    categorie_code          TEXT,               -- code brut API ("J", "S", "U15"...), sans référentiel ;
                                            -- la catégorie d'âge se recalcule depuis
                                            -- bateau.annee_naissance + l'année de la compétition
    type_code               TEXT REFERENCES type_bateau(code),  -- "boatType" du résultat
    dossard                 INTEGER,            -- "bibNumber"
    phase                   TEXT,               -- "", "A" ou "B" selon les époques
    score                   REAL,               -- temps final retenu (avec pénalités)
    score_scratch           REAL,
    compte_dans_classement  INTEGER NOT NULL DEFAULT 1,  -- "countInRanking"
    statut                  TEXT                -- "OK", "DNS", "DNF", "DSQ"
    -- rang supprimé (v1) : il se recalcule par
    --   RANK() OVER (PARTITION BY course_id, type_code, phase
    --                ORDER BY score_scratch ASC)
    -- parmi les résultats avec compte_dans_classement = 1.
);

CREATE INDEX idx_resultat_course_bateau
    ON resultat(course_id, bateau_id, phase);

-- Résultats calculés par la méthode FFCK (points du classement fédéral).
-- (avant v2 : colonnes points / valeur de RESULTAT)
-- Une autre méthode de classement aura sa propre table resultat_methode_<nom>.
CREATE TABLE resultat_methode_ffck (
    resultat_id INTEGER PRIMARY KEY REFERENCES resultat(id) ON DELETE CASCADE,
    points      REAL,     -- null ou -1 si non calculés
    valeur      REAL      -- "value" (valeur nationale brute, parfois -1)
);

CREATE TABLE manche (
    id           INTEGER PRIMARY KEY,
    resultat_id  INTEGER NOT NULL REFERENCES resultat(id) ON DELETE CASCADE,
    numero       INTEGER NOT NULL,     -- 1 ou 2
    temps        REAL,                 -- "time" sans pénalités
    penalites    INTEGER,              -- cumul des pénalités converties
    total        REAL,                 -- temps + pénalités
    statut       TEXT,
    UNIQUE (resultat_id, numero)
);

-- Détail des pénalités par porte (tableau "penaltiesDetail" dans l'API)
CREATE TABLE penalite (
    manche_id     INTEGER NOT NULL REFERENCES manche(id) ON DELETE CASCADE,
    numero_porte  INTEGER NOT NULL,
    valeur        INTEGER NOT NULL,     -- 0, 2 ou 50
    PRIMARY KEY (manche_id, numero_porte)
);

-- ------------------------------------------------------------
-- Index utiles pour les analyses
-- ------------------------------------------------------------

CREATE INDEX idx_competition_niveau ON competition(niveau);
CREATE INDEX idx_resultat_bateau ON resultat(bateau_id);
CREATE INDEX idx_manche_resultat ON manche(resultat_id);
