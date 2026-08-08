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
        -> résultat JSON + shortlist locale
```

Le collecteur ne contourne aucune authentification TUNEPS. Il conserve le
payload HAICOP original dans PostgreSQL et utilise des UPSERT pour empêcher
les doublons.

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

Options utiles :

- `--since-days N` : ne retenir que les publications récentes ;
- `--dry-run` : interroger HAICOP sans écrire en base ;
- `--with-details` : enrichir les AO et stocker les documents publics.

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

Voir [`database/README.md`](database/README.md) pour le schéma,
[`DOCKER_SETUP.md`](DOCKER_SETUP.md) pour Docker et [`HISTORY.md`](HISTORY.md)
pour l'historique du projet.
