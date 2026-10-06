# Architecture et décisions

Besoin → données → règles → API → authentification → autorisation → validation → sécurité → transaction → idempotence → tests.

## 1. Besoin
Des usagers déposent des demandes d'actes (naissance, casier, résidence) ; un agent les traite. L'API doit : déposer, consulter
(récent → ancien, filtre statut), faire avancer selon le cycle de vie.

## 2. Données
- `User` (modèle personnalisé) : `role` USAGER/AGENT, `npi` unique ; un usager a toujours un NPI (CHECK).
- `Demande` : UUID (non devinable), `npi`, `type_acte`, `nombre_copies`, `statut`, `motif_rejet`, `created_by`, `idempotency_key`, dates.
- `HistoriqueStatut` : audit de chaque changement (ancien → nouveau, acteur, motif).
- Pas de table « Usager » : l'énoncé identifie l'usager par son NPI, on évite une entité inutile.
- Contraintes PostgreSQL : CHECK sur NPI (longueur 10), copies 1..5, statut/type valides, rejet motivé ; UNIQUE partielle
  `(created_by, idempotency_key)` ; index `(npi, -created_at)` justifié par la requête de liste.
  *Risque évité : se fier au seul code applicatif (race conditions, scripts, futurs développeurs).*

## 3. Règles métier (`services.py`)
Table `TRANSITIONS` explicite ; tout ce qui n'y figure pas → 409 « Transition interdite ». Les états finaux n'y figurent pas → immuables.

## 4. API
ViewSet fin : parse, autorise, délègue aux services. Actions explicites (`prendre-en-charge`, `valider`, `rejeter`) plutôt qu'un PATCH
libre de `statut` : chaque action a sa règle et sa permission. Statuts HTTP différenciés.

## 5. Authentification
JWT : access 15 min, refresh 1 j avec rotation + blacklist, logout = révocation. Mots de passe hachés par Django (PBKDF2) + validateurs.
Aucun cookie → pas de surface CSRF ; le middleware CSRF reste activé (on ne le désactive pas « pour que ça marche »).

## 6. Autorisation
Authentifié ≠ autorisé. `IsAgent` pour les transitions. Anti-IDOR : un usager ne peut ni créer, ni lister, ni lire pour un autre NPI :
403 quand il demande explicitement un autre NPI, 404 pour un `id` hors de son périmètre (ne révèle pas l'existence).

## 7. Validation
Serializers côté serveur : NPI `^[0-9]{10}$`, entier 1..5 (refuse `"abc"`, `2.5`, `true`), choix fermés, motif non vide, filtres validés.

## 8. Sécurité (OWASP)
Injection : ORM uniquement. Secrets : variables d'environnement, refus de démarrer sans `DJANGO_SECRET_KEY` hors debug. Erreurs : handler
unique, aucune stack trace. Logs : NPI masqué (`******7890`), jamais de mot de passe ni de token. Rate limiting : login 5/min,
register 10/h, 300/min par utilisateur → 429. XSS : l'écran insère tout via `textContent`, jeton gardé en mémoire.
Dépendances : 5 paquets, versions épinglées. CORS : non nécessaire (même origine), donc non activé.

## 9. Transactions
Changement de statut = `transaction.atomic()` + `select_for_update()` (deux agents simultanés sont sérialisés) + écriture de
l'historique. Si l'historique échoue, le statut n'est pas modifié (`test_transition_is_atomic`). Même principe à la création.

## 10. Idempotence
`POST /demandes/` accepte `Idempotency-Key`. Même clé + même contenu → 200 avec la demande existante ; même clé + autre contenu → 409.
La garantie finale est la contrainte UNIQUE : si deux requêtes concurrentes passent le pré-contrôle, la perdante reçoit
`IntegrityError` et rejoue. Répéter `valider` renvoie 409 (état déjà atteint).

## 11. Tests (64)
Nominal, entrées invalides, champs manquants, doublons, 401/403/404, IDOR, cycle de vie et états finaux, pagination, stats, absence de N+1,
idempotence + course simulée, atomicité à mi-chemin, contraintes DB, rate limiting, révocation de token, format d'erreur.
