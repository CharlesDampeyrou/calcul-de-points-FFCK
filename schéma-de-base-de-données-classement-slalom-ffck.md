# Schéma de base de données : classement slalom (FFCK)

```mermaid
erDiagram
    COMPETITION ||--o{ COURSE : " organise "
    COURSE ||--|| COURSE_METHODE_FFCK : " paramètres méthode FFCK "
    COURSE ||--o{ RESULTAT : " produit "
    BATEAU ||--o{ RESULTAT : " engage "
    COMPETITEUR ||--o{ BATEAU_COMPETITEUR : " membre "
    BATEAU ||--o{ BATEAU_COMPETITEUR : " equipe "
    CLUB ||--o{ BATEAU_COMPETITEUR : " club du membre "
    TYPE_BATEAU ||--o{ RESULTAT : " type "
    TYPE_BATEAU ||--o{ BATEAU : " type "
    RESULTAT ||--|| RESULTAT_METHODE_FFCK : " points méthode FFCK "
    RESULTAT ||--o{ MANCHE : " détaille "
    MANCHE ||--o{ PENALITE : " détaille "

    COMPETITION {
        int id PK
        string id_api UK " id renvoyé par l'API "
        string id_externe UK " foreignId, ex ffck-FFCK20260985, null avant 2019 "
        string nom
        string lieu
        date date_debut " startDate, parfois null sur 2001-2015 "
        date date_fin " date, parfois null sur 2001-2015 "
        int niveau " 1 régional, 2 N3, 4 N1, 5 Chpts "
    }
    COURSE {
        int id PK
        string id_api UK
        int competition_id FK
        string nom " ex Course n°1, Qualification "
        date date
        int nb_portes " gateNumber, peut être null "
        bool penalites_completes " fullPenalties, absent 2001-2023 "
        string points_calculation_method_id " brut API, ex 2026, null avant 2025 — simple texte, sans table de référence "
        string phase_competition " qualification / demi-finale / finale, NULL = pas de phase ; lu dans phases_courses.json (pas de déduction automatique) "
        decimal phase_ordre " priorité de traitement : 0 = pas de phase, 0.k = Course n°k, 1/2/3 = qualification/demi-finale/finale "
    }
    COURSE_METHODE_FFCK {
        int course_id PK, FK " 1 ligne par course "
        string details " JSON sérialisé, ex. tpsBase + coefficientCourse ; même forme que course_methode_<nom> des autres méthodes "
    }
    BATEAU {
        int id PK
        string id_api UK " ex C1H270346, identifiant stable "
        string libelle " noms séparés par un saut de ligne si équipage C2, parfois null "
        string type_code FK
        int annee_naissance " fiche /ffck/boats, champ slalom.year "
        string niveau " niveau national du bateau, ex N2 ou Reg "
        int surclassement " -1, 0 ou 1 "
    }
    COMPETITEUR {
        int id PK
        string id_api UK " id de la fiche personne, ex 270346 "
        string nom
        string prenom
    }
    BATEAU_COMPETITEUR {
        int bateau_id PK, FK
        int competiteur_id PK, FK
        int position " 1 ou 2 selon l'ordre dans le libellé "
        int club_id FK " club du membre pour ce bateau ; C2 mixte = clubs différents "
    }
    CLUB {
        int id PK
        string id_api UK " ex 080003 "
        string nom " parfois chaîne vide "
    }
    TYPE_BATEAU {
        int id PK
        string code UK " K1H, K1D, C1H, C2M, INV... "
        string nom
    }
    RESULTAT {
        int id PK
        string id_api UK
        int course_id FK
        int bateau_id FK
        string categorie_code " code brut API (J, S, U15...), SANS table de référence ; catégorie d'âge recalculable via annee_naissance "
        string type_code FK " boatType du résultat "
        int dossard " bibNumber "
        string phase " vide, A ou B selon les années "
        decimal score " temps final retenu (avec pénalités) "
        decimal score_scratch
        bool compte_dans_classement " countInRanking "
        string statut " OK, DNS, DNF, DSQ "
    }
    RESULTAT_METHODE_FFCK {
        int resultat_id PK, FK " 1 ligne par résultat "
        decimal points " calculés par la méthode FFCK, null ou -1 si non calculés "
        decimal valeur " valeur nationale brute, parfois -1 "
    }
    MANCHE {
        int id PK
        int resultat_id FK
        int numero " 1 ou 2 selon la course "
        decimal temps " time, sans pénalités "
        int penalites
        decimal total " temps + pénalités "
        string statut
    }
    PENALITE {
        int manche_id PK, FK
        int numero_porte PK " index dans penaltiesDetail "
        int valeur " 0, 2 ou 50 "
    }
```

## Recalculer rang et catégorie d'âge

```sql
-- Rang dans la course, par type de bateau et phase (A/B séparées) :
-- ~96% de concordance avec le champ "rank" de l'API sur les données collectées.
SELECT r.id,
       RANK() OVER (PARTITION BY r.course_id, r.type_code, r.phase
                    ORDER BY COALESCE(NULLIF(r.score_scratch, 0), r.score) ASC) AS rang
FROM resultat r
WHERE r.compte_dans_classement = 1;

-- Catégorie d'âge à une année donnée (ex. 2025, codes U12/U15/U18 depuis 2021) :
SELECT r.id,
       CASE WHEN 2025 - b.annee_naissance < 12 THEN 'U12'
            WHEN 2025 - b.annee_naissance < 15 THEN 'U15'
            WHEN 2025 - b.annee_naissance < 18 THEN 'U18' END AS categorie_age
FROM resultat r JOIN bateau b ON b.id = r.bateau_id
WHERE b.annee_naissance IS NOT NULL;
```

## Phases des courses (qualification / demi-finale / finale)

L'API n'a pas de champ "phase" dédié au niveau course : la phase se lit dans le **nom de la course** (`race.name`). Comme il y a des subtilités (des courses appelées "Finale" qui comportent en réalité plusieurs phases), la phase **n'est pas déduite automatiquement** :

- le mapping nom → phase est stocké dans **`phases_courses.json`** (clé = nom normalisé — casse/accents/espaces ignorés ; valeur = `{"brut": ..., "phase": ...}`) ;
- il est initialisé depuis `old_scrapper_infos/phase_simplification.pkl` (`python3 collecte_bdd.py --init-phases`) : `(no_phase_list, qualif_list, demi_list, final_list) = pickle.load(f)` ;
- pendant la collecte, un **nom inconnu** fait émettre un bip au script, qui demande la phase interactivement et l'enregistre dans le JSON pour les prochaines fois ;
- avec `--no-interactif` (run en arrière-plan sans terminal), les noms inconnus passent à `NULL` et sont loggés dans `phases_inconnues.log` ;
- après un run `--no-interactif` (ou une édition manuelle du JSON), lancer **`python3 collecte_bdd.py --revoir-phases`** (post-traitement intégré à la collecte) : il rejoue les noms du log interactivement (bip + saisie), enregistre les réponses dans `phases_courses.json`, répercute dans la base (`UPDATE course SET phase_competition, phase_ordre`) et archive le log en `.old`. Options : `--revoir-phases-tout` (revoir tous les noms de la base), `--dry-run` (JSON seul, base inchangée).

Stockage sur `COURSE` :

| colonne | valeurs |
|---|---|
| `phase_competition` | `'qualification'`, `'demi-finale'`, `'finale'`, ou `NULL` (pas de phase) |
| `phase_ordre` | `0` = pas de phase, `0.k` = nom "Course n°k" (0.1, 0.2, 0.3...), `1`/`2`/`3` = qualification/demi-finale/finale. Saisie manuelle possible : répondre `0.k` (ex `0.3`) lors de l'interaction → `phase_competition = NULL` + `phase_ordre = 0.k` explicite (champ `"ordre"` dans le JSON), prioritaire sur le calcul auto |

Ordre de traitement des courses d'une compétition :

```sql
SELECT * FROM course WHERE competition_id = ?
ORDER BY date, phase_ordre, id_api;
```

## Courses par équipe (non sauvegardées)

On ne garde que les compétitions individuelles. `team_events.json` = `{"team": [...], "non_team": [...]}` (converti depuis l'ancien `team_event_classification.pkl` ; les noms sont ceux de l'ancien scrapper).

Détection **au niveau course** (un event peut mélanger courses individuelles et par équipe, ex l'event `...Master-Equipage` avec la course `Frances par équipe`) : candidat si `equipe`/`patrouille` est dans `race.name` ou `ev.name` (normalisé = unidecode + lower). Matching contre le JSON : égalité normalisée ou préfixe avec un nom testé d'au moins 25 caractères (strict, pour éviter les faux positifs silencieux ; un faux négatif tombe sur la question interactive).

- nom connu (`team`/`non_team`) → décision appliquée, la course team **n'est pas insérée**
- candidat inconnu → bip + question `[o/n]`, réponse enregistrée dans `team_events.json` (`"event | course"`) ; en `--no-interactif` : la course est **sautée** et loggée dans `team_events_inconnus.log`

## Tester d'autres méthodes de classement

Aucune modification du schéma de base n'est nécessaire. Le pattern (voir `exemple_methode_test.py`) :

1. créer une table dédiée à la méthode, avec la forme propre à cette méthode :
   `course_methode_<nom>(course_id PK, ...)` pour ses paramètres de course,
   `resultat_methode_<nom>(resultat_id PK, ...)` pour ses résultats calculés ;
2. la remplir par calcul à partir des données brutes (`resultat`, `manche`, `penalite`, `course_methode_ffck`...) ;
3. comparer avec la méthode FFCK (`resultat_methode_ffck`).

## Évolutions du format prises en compte

- **La course est l'unité de résultats, pas la compétition.** Une compétition contient 1 à 4 courses (manches) distinctes, chacune avec son propre classement.
- **Le bateau, pas le compétiteur, participe.** Les équipes C2 ont deux membres (le champ `boat.label` les sépare par un retour à la ligne) et peuvent représenter **deux clubs différents**, d'où le club porté par chaque membre (`BATEAU_COMPETITEUR.club_id`).
- **Année de naissance** : disponible sur la fiche de chaque bateau (endpoint `/ffck/boats/{id}`, champ `slalom.year`), portée par le bateau ; sur un C2 les deux équipiers partagent la même valeur.
- **Catégories hétérogènes** : codes historiques à une lettre (J, C, S, V...) jusqu'au début des années 2020, puis U12/U15/U18/M35 depuis 2021. Le code brut est conservé dans `resultat.categorie_code` (texte libre) ; la catégorie d'âge se recalcule depuis l'année de naissance.
- **Points** : calculés par course selon la méthode FFCK (`baseTime`, `coefficient` → JSON `details` de `course_methode_ffck` ; identifiant de méthode brut → `course.points_calculation_method_id`, renseigné seulement depuis 2025). Les `points`/`valeur` de chaque résultat sont stockés dans `resultat_methode_ffck` et peuvent valoir `-1`.
- **Manches** : 1 ou 2 manches par course selon l'époque, d'où la table `MANCHE` séparée de `RESULTAT`.
- **Pénalités** : `penaltiesDetail` est un tableau indexé par porte ; il est rattaché à la manche.
- **Miscibilité** : `phase` (A/B, courses à phases), `statut` (OK/DNS/DNF/DSQ), et le type `INV` (invités, hors classement, `countInRanking` à faux) sont conservés en colonnes dédiées.
- **Traçabilité** : les colonnes `id_api` (identifiants de l'API) et `id_externe` (`foreignId`, absent avant 2019) facilitent les mises à jour incrémentales.
