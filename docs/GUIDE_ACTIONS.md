# Où faire quoi ?

## Écran (http://127.0.0.1:8000/) 

| Vue | Adresse | Contenu |
|---|---|---|
| **Liste** | `#/` | Demandes (récentes en haut), recherche + « Filtres » par statut avec compteurs, pager `1-20 / N` |
| **Création** | `#/new` | Formulaire : NPI, type d'acte, copies 1 à 5, bouton « Enregistrer » |
| **Fiche** | `#/d/<id>` | Détail, barre de statut, boutons d'action (agent), historique |

| Je veux… | Qui | Où |
|---|---|---|
| Me connecter | tous | Formulaire initial (usager : son NPI ; agent : `agent1`) |
| Déposer une demande | usager, agent | Liste → **Nouveau** (`Alt+N`) → **Enregistrer** |
| Filtrer par statut | tous | Liste → **Filtres ▾** |
| Chercher un usager | agent | Liste → barre de recherche : NPI (10 chiffres) + Entrée |
| Voir détail + historique | tous | Clic sur une ligne de la liste |
| Prendre en charge | agent | Fiche → **Prendre en charge** (Déposée → En cours) |
| Valider | agent | Fiche → **Valider** (En cours → Validée) |
| Rejeter | agent | Fiche → **Rejeter** → motif obligatoire → **Rejeter** |
| Revenir à la liste | tous | Fil d'Ariane « Demandes » ou `Échap` |
| Aide | tous | **Aide** (`?`) en haut à droite |

Une demande Validée ou Rejetée est close : aucun bouton d'action.

## API (mêmes actions)

| Action | Appel |
|---|---|
| Compte usager | `POST /api/auth/register/` |
| Connexion / rafraîchir / déconnexion | `POST /api/auth/token/` · `…/token/refresh/` · `…/logout/` |
| Déposer | `POST /api/demandes/` (+ `Idempotency-Key`) |
| Lister / filtrer / paginer | `GET /api/demandes/?npi=&statut=&page=` |
| Détail + historique | `GET /api/demandes/{id}/` |
| Compteurs par statut | `GET /api/demandes/stats/` |
| Traiter | `POST /api/demandes/{id}/prendre-en-charge/` · `valider/` · `rejeter/` `{"motif":"..."}` |

## Si ça refuse
401 session expirée · 403 réservé aux agents ou NPI qui n'est pas le vôtre · 404 demande hors périmètre ·
409 transition interdite · 400 champ invalide (le message indique lequel).
