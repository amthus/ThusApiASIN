# API de suivi des demandes d'actes administratifs

Étude de cas ASIN / DEP 2026 — Développeur(se) junior(e).
Stack : Python 3.12, Django 5.2, Django REST Framework, JWT (simplejwt), PostgreSQL (SQLite en démarrage rapide), pytest.

## Démarrage rapide (recette du jury, sans Docker, SQLite)

```bash
python -m venv .venv && source .venv/bin/activate      # Windows : .venv\Scripts\activate
pip install -r requirements-dev.txt
export DJANGO_DEBUG=1                                   # PowerShell : $env:DJANGO_DEBUG="1"
python manage.py migrate
python manage.py seed_demo --password 'Demo-Pass-2026!'  # crée agent1 (agent) et 0123456789 (usager)
python manage.py runserver
```

- API : http://127.0.0.1:8000/api/ — écran de consultation : http://127.0.0.1:8000/
- Tests : `python -m pytest` (64 tests)

## Démarrage avec PostgreSQL (Docker)

```bash
cp .env.example .env     # puis renseigner DJANGO_SECRET_KEY et POSTGRES_PASSWORD
docker compose --env-file .env up --build
```
Sans `POSTGRES_DB`, l'application utilise SQLite. Pour créer les comptes de démo avec Docker, mettre `DJANGO_DEBUG=1` dans `.env` puis :
`docker compose exec web python manage.py seed_demo --password '...'`.

## Variables d'environnement

| Variable | Rôle |
|---|---|
| `DJANGO_SECRET_KEY` | Obligatoire hors `DJANGO_DEBUG=1` (signe aussi les JWT) |
| `DJANGO_DEBUG` | `1` en local uniquement |
| `DJANGO_ALLOWED_HOSTS` | Hôtes autorisés, séparés par des virgules |
| `POSTGRES_DB/USER/PASSWORD/HOST/PORT` | Active PostgreSQL |
| `DJANGO_HTTPS` | `1` derrière un proxy HTTPS (redirection SSL + HSTS) |

## Scénario de recette (curl)

```bash
B=http://127.0.0.1:8000
# Connexion (usager = son NPI, agent = agent1)
U=$(curl -s -X POST $B/api/auth/token/ -H 'Content-Type: application/json' \
     -d '{"username":"0123456789","password":"Demo-Pass-2026!"}' | python -c "import sys,json;print(json.load(sys.stdin)['access'])")
A=$(curl -s -X POST $B/api/auth/token/ -H 'Content-Type: application/json' \
     -d '{"username":"agent1","password":"Demo-Pass-2026!"}' | python -c "import sys,json;print(json.load(sys.stdin)['access'])")
# Déposer une demande (statut DEPOSEE)
curl -X POST $B/api/demandes/ -H "Authorization: Bearer $U" -H 'Content-Type: application/json' \
     -d '{"npi":"0123456789","type_acte":"ACTE_NAISSANCE","nombre_copies":2}'
# Consulter (plus récentes d'abord, filtre facultatif)
curl "$B/api/demandes/?statut=DEPOSEE" -H "Authorization: Bearer $U"
# 4. Faire avancer (agent) : prendre-en-charge -> valider | rejeter
curl -X POST $B/api/demandes/<id>/prendre-en-charge/ -H "Authorization: Bearer $A"
curl -X POST $B/api/demandes/<id>/rejeter/ -H "Authorization: Bearer $A" -H 'Content-Type: application/json' -d '{"motif":"Pièce illisible"}'
```

## API

Routes JSON, préfixe `/api/`. Authentification : `Authorization: Bearer <access>`.

| Méthode | Route | Rôle | Description |
|---|---|---|---|
| POST | `auth/register/` | public | Crée un compte usager `{npi, password}` (201 / 409 si NPI déjà pris) |
| POST | `auth/token/` | public | Connexion `{username, password}` → `access` (15 min) + `refresh` (1 j) |
| POST | `auth/token/refresh/` | public | Nouveau `access` (refresh tourné, ancien révoqué) |
| POST | `auth/logout/` | public | Révoque un `refresh` |
| POST | `demandes/` | usager (son NPI) / agent (tout NPI) | Dépose `{npi, type_acte, nombre_copies}` → 201, statut `DEPOSEE`. Header optionnel `Idempotency-Key` |
| GET | `demandes/?npi=&statut=&page=` | usager (le sien) / agent | Liste paginée (20 max), plus récente d'abord |
| GET | `demandes/{id}/` | usager (la sienne) / agent | Détail + historique des statuts |
| GET | `demandes/stats/?npi=` | usager / agent | Nombre de demandes par statut |
| POST | `demandes/{id}/prendre-en-charge/` | agent | `DEPOSEE → EN_COURS` |
| POST | `demandes/{id}/valider/` | agent | `EN_COURS → VALIDEE` |
| POST | `demandes/{id}/rejeter/` | agent | `EN_COURS → REJETEE`, `{motif}` obligatoire |

Valeurs : `type_acte` ∈ `ACTE_NAISSANCE`, `CASIER_JUDICIAIRE`, `CERTIFICAT_RESIDENCE` ; `statut` ∈ `DEPOSEE`, `EN_COURS`, `VALIDEE`, `REJETEE`.

Codes HTTP : 200/201 succès · 400 saisie invalide · 401 non authentifié · 403 interdit · 404 introuvable (ou non visible) ·
409 conflit (transition interdite, NPI déjà inscrit, clé d'idempotence réutilisée avec un autre contenu) · 429 trop de requêtes.
Format d'erreur unique : `{"error": {"code": "...", "message": "...", "details": ...}}`.

## Règles de gestion

NPI = exactement 10 chiffres · copies entre 1 et 5 · type d'acte parmi les 3 · cycle `DEPOSEE → EN_COURS → VALIDEE | REJETEE`,
états finaux immuables · rejet toujours motivé · saisie invalide ou action interdite refusée avec un message clair.
Appliquées dans l'API **et** par des contraintes CHECK en base.

## État d'avancement

| Élément | État |
|---|---|
| Socle (déposer, consulter + filtre, faire avancer) | Fait, vérifié par tests et par un parcours curl |
| Bonus : pagination 20/page, comptage par statut, tests, écran simple | Faits |
| JWT, rôles usager/agent, anti-IDOR, rate limiting, idempotence, historique | Faits (au-delà de l'énoncé) |
| Exécution sur PostgreSQL | Configuré (`docker-compose.yml`) mais non exécuté ici : testé sur SQLite |

Limites connues : (1) l'inscription par NPI + mot de passe ne **prouve pas** l'identité du NPI (il faudrait un OTP ou un fournisseur
d'identité national) ; (2) le rate limiting utilise le cache local, donc par processus (en production : Redis) ; (3) les agents sont
créés en base (`seed_demo` / shell), pas via l'API ; (4) pas de CORS : l'écran est servi par la même origine.

Choix de conception : `docs/ARCHITECTURE.md` · Où faire quoi (écran et API) : `docs/GUIDE_ACTIONS.md`.
