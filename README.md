# OneTech Tender Agent

Projet de stage :

> Développement d'un système IA agentique pour la gestion des appels d'offres publics

Le premier flux de bout en bout collecte les données publiques HAICOP, les
normalise, les stocke dans PostgreSQL et renvoie une shortlist locale à
OpenClaw.

## Architecture actuelle

```text
OpenClaw entreprise
        -> skill collecte-haicop-ao
        -> package Python onetech_ao
        -> API et pages publiques HAICOP
        -> PostgreSQL 16
        -> téléchargement + SHA-256 + extraction PDF/DOCX
        -> résultat JSON + shortlist locale
```

Le collecteur ne contourne aucune authentification TUNEPS. Il conserve le
payload HAICOP original dans PostgreSQL et utilise des UPSERT pour empêcher
les doublons.

## État du projet

Au 10 août 2026, le flux HAICOP vers PostgreSQL est opérationnel :

- 20 appels d'offres publics stockés ;
- 30 liens vers des documents publics stockés ;
- 2 collectes réelles terminées ;
- première exécution : 20 insertions ;
- deuxième exécution identique : 20 mises à jour et aucune nouvelle ligne ;
- aucun doublon sur les appels d'offres ou les documents.
- 30 fichiers publics téléchargés et hashés (environ 6,1 Mo) ;
- 25 documents PDF/DOCX avec texte extrait dans PostgreSQL ;
- 2 PDF sans couche texte, à traiter plus tard par OCR ;
- 3 anciens fichiers DOC conservés mais marqués `non_supporte` ;
- 0 échec de traitement et 0 document restant à traiter.

## Accès local aux services

| Service | Adresse | Identité/configuration |
| --- | --- | --- |
| PostgreSQL | `127.0.0.1:5432` | base `onetech_ao`, utilisateur `onetech` |
| pgAdmin | <http://localhost:5050> | variables `PGADMIN_DEFAULT_*` dans `.env` |
| Gateway OpenClaw entreprise | `127.0.0.1:18790` | configuration dans `C:\Users\khaye\.openclaw-company\openclaw.json` |

### Secrets locaux

Les vraies valeurs de `POSTGRES_PASSWORD`, `PGADMIN_DEFAULT_EMAIL` et
`PGADMIN_DEFAULT_PASSWORD` sont conservées uniquement dans :

```text
C:\Users\khaye\.openclaw-company\workspace\.env
```

Pour les consulter localement dans PowerShell :

```powershell
Get-Content C:\Users\khaye\.openclaw-company\workspace\.env
```

Le fichier `.env` et `pgadmin/pgpass` sont ignorés par Git. Ne jamais copier
leurs valeurs dans un commit, un ticket ou un log, même si le dépôt distant est
privé. Utiliser `.env.example` pour documenter les variables attendues.

## Installation locale

Prérequis : Docker Desktop et Python 3.11 ou plus récent.

Depuis PowerShell, à la racine du workspace entreprise :

```powershell
docker compose up -d
docker compose ps
.\scripts\apply-database.ps1

py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e '.[dev]'
```

La configuration est lue depuis le fichier local `.env`, ignoré par Git. Ne
pas l'écraser et ne jamais copier ses secrets dans le code ou les logs.

## CLI

Vérifier la connexion, les compteurs et l'intégrité :

```powershell
.\.venv\Scripts\python.exe -m onetech_ao.cli status
```

Collecter 50 AO récents :

```powershell
.\.venv\Scripts\python.exe -m onetech_ao.cli collect --limit 50
```

Collecter les pages détail et les liens documentaires publics :

```powershell
.\.venv\Scripts\python.exe -m onetech_ao.cli collect --limit 20 --with-details
```

Télécharger, hasher et extraire les documents en attente :

```powershell
.\.venv\Scripts\python.exe -m onetech_ao.cli process-documents --limit 50
```

Collecter puis traiter les documents dans la même commande :

```powershell
.\.venv\Scripts\python.exe -m onetech_ao.cli collect --limit 20 --with-details --process-documents
```

Options utiles :

- `--since-days N` : ne retenir que les publications récentes ;
- `--dry-run` : interroger HAICOP sans écrire en base ;
- `--with-details` : enrichir les AO et stocker les documents publics.
- `--process-documents` : télécharger et extraire les documents après collecte ;
- `process-documents --retry-errors` : relancer uniquement les erreurs précédentes.

Lister les AO ouverts stockés :

```powershell
.\.venv\Scripts\python.exe -m onetech_ao.cli list-open --limit 20
```

Toutes les commandes renvoient du JSON UTF-8 exploitable par OpenClaw.

## Tests

```powershell
.\scripts\test-database.ps1
.\.venv\Scripts\python.exe -m pytest -m 'not integration and not network'
.\.venv\Scripts\python.exe -m pytest -m integration
```

Le test d'intégration vérifie la connexion et deux UPSERT identiques, puis
supprime ses données factices. Le contrôle `status` doit signaler zéro doublon
et zéro payload brut vide.

## Dépannage

- PostgreSQL indisponible : lancer `docker compose up -d`, attendre l'état
  `healthy`, puis réessayer `status`.
- Tables absentes : lancer `.\scripts\apply-database.ps1`. Les migrations sont
  idempotentes.
- Module Python introuvable : réinstaller le projet avec
  `.\.venv\Scripts\python.exe -m pip install -e '.[dev]'`.
- Erreur HAICOP temporaire : conserver la ligne `collectes_haicop` en échec et
  relancer plus tard ; ne pas utiliser un endpoint privé en contournement.
- Cahier des charges absent : il peut nécessiter une session TUNEPS autorisée.
- `sans_texte` : le PDF est probablement scanné et nécessitera un OCR.
- `non_supporte` : le format DOC binaire est conservé mais pas extrait ; préférer
  une conversion contrôlée en DOCX/PDF.

Voir [`database/README.md`](database/README.md) pour le schéma,
[`DOCKER_SETUP.md`](DOCKER_SETUP.md) pour Docker et [`HISTORY.md`](HISTORY.md)
pour l'historique du projet.

## Prochaine étape

Brancher `texte_extrait` sur l'analyse structurée `analyse-ao` afin de produire
automatiquement une fiche, un score Go/No-Go provisoire et un digest OneTech.
Ajouter ensuite l'OCR des deux PDF scannés et, si nécessaire, une conversion
contrôlée des trois anciens fichiers DOC.
