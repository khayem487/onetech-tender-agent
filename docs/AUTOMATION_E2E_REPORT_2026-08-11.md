# Validation complète — automatisation quotidienne OneTech AO

Date : 11 août 2026
Portée : HAICOP -> PostgreSQL -> documents -> analyse OpenClaw -> digest -> n8n

## Résultat

L'automatisation quotidienne est opérationnelle en mode de diffusion local
sécurisé. Le scheduler n8n est activé pour les jours ouvrés à 08:00
`Europe/Paris`. La diffusion par défaut est Mailpit, donc aucun email Gmail ni
message Telegram n'est envoyé par cette validation.

```text
n8n
  -> ao-worker authentifié (réseau Docker interne)
  -> gateway OpenClaw entreprise, port 18790
  -> collecte HAICOP / PostgreSQL / documents / analyse-ao
  -> digest Markdown dans data/digests/
  -> preuve de diffusion dans diffusions_digest
  -> Mailpit local, port 8025
```

## Services validés

| Service | Etat | Adresse locale |
| --- | --- | --- |
| PostgreSQL | healthy | `127.0.0.1:5432` |
| pgAdmin | running | `http://localhost:5050` |
| Mailpit | healthy | `http://localhost:8025` |
| ao-worker | healthy | interne Docker, port `8080` |
| n8n | running, workflow actif | `http://localhost:5678` |
| Gateway OpenClaw entreprise | accessible | `127.0.0.1:18790` |

Workflow n8n actif : `OneTech AO - Daily Digest`.

## Validation réelle de bout en bout

Une exécution réelle a été traitée avec la clé `daily:2026-08-11` :

- exécution PostgreSQL : ID `4`, statut `terminee` ;
- un candidat préparé et une analyse produite ;
- digest généré : `data/digests/2026-08-11_run-4.md` ;
- une seule ligne de diffusion Mailpit conservée ;
- un seul message présent dans Mailpit après nettoyage des messages de test
  obsolètes ;
- un second appel à `daily-finish --run-id 4 --mailpit` a renvoyé
  `deja_envoyee` sans créer de ligne ni de message supplémentaire.

Le marché utilisé dans ce premier test technique (`Tender-103262`) concernait
des équipements de formation au gaz. Il a permis de détecter un faux positif
de filtrage. Le profil OneTech validé pénalise les achats matériels sans
composante numérique : le filtre a été renforcé avec une recherche par mots
entiers, des réseaux informatiques explicites et une pénalité matériel. Ce
marché obtient maintenant `-14` et ne sera plus proposé par les prochains
digests automatisés. Le seuil de sélection est maintenant `6`; au moment de
la validation, aucune AO ouverte ne le dépassait, ce qui est le comportement
attendu plutôt qu'un faux positif forcé.

## Protection anti-doublon

Deux niveaux sont appliqués :

1. La date de fin d'une exécution est figée avant le rendu du digest. Son hash
   reste identique sur un retry.
2. PostgreSQL applique l'unicité
   `(execution_id, canal, destinataire_hash)` dans `diffusions_digest`.
   Une exécution ne peut donc pas redistribuer un digest au même destinataire,
   même si un contenu change accidentellement pendant une tentative.

La migration `database/init/006_delivery_idempotence.sql` renforce cette
contrainte et consolide les anciens messages de test en une preuve de diffusion
unique.

## Tests exécutés

```text
39 tests Python : succès
3 tests d'intégration PostgreSQL : succès
5 scripts SQL smoke test : succès
Healthcheck ao-worker : {"status":"ok"}
Workflow n8n : actif après redémarrage
Retry Mailpit : 1 ligne avant = 1 ligne après, 1 message avant = 1 message après
```

Les commandes de contrôle sont :

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pytest -m integration -q
.\scripts\test-database.ps1
docker compose ps
docker compose exec -T n8n n8n list:workflow --active=true
```

## Opérations courantes

Avant le premier lancement quotidien, démarrer le gateway entreprise :

```powershell
C:\Users\khaye\.openclaw-company\start-company-gateway.cmd
```

Pour importer/activer le workflow sans le dupliquer :

```powershell
.\scripts\activate-daily-automation.ps1
```

Pour examiner le message local de test :

```text
http://localhost:8025
```

Pour lancer un test manuel dans n8n, ouvrir `http://localhost:5678`, choisir
`OneTech AO - Daily Digest`, puis utiliser le déclencheur manuel.

## Sécurité et limites volontaires

- Les secrets restent dans `.env` et la configuration locale du gateway ; aucun
  secret n'est présent dans ce rapport ou dans Git.
- Le worker n'accepte qu'une route métier authentifiée, pas des prompts
  arbitraires.
- Mailpit est local. Gmail et Telegram existent dans le code mais ne sont pas
  activés : leur premier envoi doit être choisi et vérifié séparément.
- `docker compose down -v` supprimerait les volumes PostgreSQL, n8n et Mailpit;
  ne pas l'utiliser pour une simple relance.

## Suite recommandée

Le MVP d'automatisation est terminé. Les prochaines améliorations ne bloquent
pas son fonctionnement : test contrôlé Gmail/Telegram, OCR des documents
scannés, puis MCP/Odoo si OneTech le demande.
