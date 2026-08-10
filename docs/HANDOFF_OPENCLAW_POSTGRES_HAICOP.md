# Passation complète — OpenClaw entreprise + PostgreSQL + HAICOP

> **Archive de mise en œuvre.** Le collecteur, PostgreSQL, le traitement des
> documents et le pont d'analyse sont maintenant implémentés. Ne plus exécuter
> la section « travail à faire » comme une nouvelle mission. Utiliser le
> `README.md` et `database/README.md` pour l'état actuel et les commandes.

Ce fichier remplace le long message du TUI qui a été affiché partiellement.
Il ne contient aucun mot de passe. Les secrets doivent être lus depuis le
fichier local `.env`, qui est ignoré par Git.

## Comment utiliser cette passation

1. Démarrer Docker Desktop.
2. Dans PowerShell :

```powershell
cd C:\Users\khaye\.openclaw-company\workspace
docker compose up -d
docker compose ps
.\scripts\apply-database.ps1
.\scripts\test-database.ps1
```

3. Démarrer le gateway entreprise dans une première invite de commandes :

```cmd
cd C:\Users\khaye\.openclaw-company
openclaw gateway run
```

4. Ouvrir le TUI entreprise dans une seconde invite de commandes :

```cmd
cd C:\Users\khaye\.openclaw-company
openclaw tui
```

5. Envoyer seulement ce message court dans le TUI :

```text
Lis complètement le fichier C:\Users\khaye\.openclaw-company\workspace\docs\HANDOFF_OPENCLAW_POSTGRES_HAICOP.md, puis exécute la section « Instruction complète pour l’OpenClaw entreprise » de manière autonome. Utilise les fichiers réels comme source de vérité, ne révèle aucun secret et ne pousse rien sur GitHub.
```

## Architecture visée

OpenClaw ne charge pas directement PostgreSQL dans son « cerveau ».
L’intégration correcte est :

```text
OpenClaw entreprise
→ skill collecte-haicop-ao
→ package/collecteur Python
→ API publique HAICOP
→ PostgreSQL
→ résultats structurés renvoyés à OpenClaw
```

## Instruction complète pour l’OpenClaw entreprise

Tu travailles sur mon projet de stage OneTech :

« Developpement d'un systeme IA agentique pour la gestion des appels d'offres publics »

Ton workspace officiel est :

```text
C:\Users\khaye\.openclaw-company\workspace
```

### OBJECTIF

Intègre le PostgreSQL Docker déjà configuré dans ton workflow OpenClaw/HAICOP.

L’intégration doit être :

```text
OpenClaw entreprise
→ skill collecte-haicop-ao
→ package/collecteur Python
→ API publique HAICOP
→ PostgreSQL
→ réponse structurée à l’utilisateur
```

Ne cherche pas à connecter l’OpenClaw personnel. Tout doit rester dans le
workspace entreprise.

### ÉTAT ACTUEL

Le dépôt local est sur la branche `main`, avec un worktree propre au moment de
la rédaction de cette passation.

Dernier commit connu :

```text
405b1a9 feat(database): add HAICOP tender schema and upsert tests
```

Vérifie à nouveau `git status` et `git log` avant toute modification.

- Ne pousse rien sur GitHub.
- Ne configure aucun remote.
- Les commits doivent rester locaux.

Docker Compose :

```text
C:\Users\khaye\.openclaw-company\workspace\compose.yaml
```

Services :

- `postgres`
- `pgadmin`

Conteneurs :

- `onetech-postgres`
- `onetech-pgadmin`

Volumes persistants :

- `onetech_postgres_data`
- `onetech_pgadmin_data`

Connexion PostgreSQL depuis un programme exécuté sur Windows/OpenClaw :

- Host : `127.0.0.1`
- Port : valeur `POSTGRES_PORT` dans `.env`, normalement `5432`
- Database : valeur `POSTGRES_DB`, actuellement `onetech_ao`
- Username : valeur `POSTGRES_USER`, actuellement `onetech`
- Password : lire `POSTGRES_PASSWORD` depuis `.env`

Connexion depuis un autre conteneur Docker :

- Host : `postgres`
- Port : `5432`

Ne copie jamais le mot de passe dans le code, les logs, la documentation, les
commits ou `MEMORY.md`.

Lis les paramètres depuis :

```text
C:\Users\khaye\.openclaw-company\workspace\.env
```

Le fichier `.env` est ignoré par Git. Ne l’écrase pas.

pgAdmin :

- URL : `http://localhost:5050`
- Identifiants : `PGADMIN_DEFAULT_EMAIL` et `PGADMIN_DEFAULT_PASSWORD` dans `.env`
- Serveur déjà enregistré : `OneTech PostgreSQL`

### SCHÉMA EXISTANT

Migration :

```text
database/init/001_schema.sql
```

Documentation :

```text
database/README.md
DOCKER_SETUP.md
```

Scripts existants :

```text
scripts/apply-database.ps1
scripts/test-database.ps1
```

Tables :

#### 1. `collectes_haicop`

- `id`
- `source`
- `statut` : `en_cours`, `terminee` ou `echec`
- `demarree_le`
- `terminee_le`
- `nb_recus`
- `nb_inseres`
- `nb_mis_a_jour`
- `erreur`
- `parametres JSONB`

#### 2. `appels_offres`

- `tender_id`, clé primaire anti-doublon
- `source`
- `plan_id`
- `organisme`
- `titre`
- `date_publication`
- `date_limite`
- `reserve_pme`
- `url_detail`
- `champs_details JSONB`
- `donnees_brutes JSONB`
- `collecte_id`
- `premiere_collecte_le`
- `derniere_collecte_le`
- `mise_a_jour_le`

#### 3. `documents_ao`

- `id`
- `tender_id`, clé étrangère vers `appels_offres`
- `libelle`
- `type_document`
- `url`
- `chemin_local`
- `texte_extrait`
- `empreinte_sha256`
- `metadonnees_brutes JSONB`
- `premiere_collecte_le`
- `derniere_collecte_le`
- `mise_a_jour_le`

Contrainte anti-doublon document :

```sql
UNIQUE (tender_id, url)
```

Vue existante :

```text
v_appels_offres_ouverts
```

Le schéma contient déjà les index, triggers d’horodatage, contraintes, clés
étrangères et stockage JSONB.

### TRAVAIL À FAIRE

#### 1. Audit initial obligatoire

Lis complètement avant modification :

- `README.md`
- `HISTORY.md`
- `DOCKER_SETUP.md`
- `database/README.md`
- `database/init/001_schema.sql`
- `database/tests/001_upsert_smoke_test.sql`
- `skills/collecte-haicop-ao/SKILL.md`

#### 2. Ancien prototype

Tu peux consulter l’ancien prototype uniquement comme référence :

```text
_removed_by_claw\tender-agent-poc-20260707-004543
```

Ne le réactive pas et ne le copie pas aveuglément. Il utilisait SQLite et
mélangeait certaines responsabilités.

#### 3. Package Python maintenable

Crée un vrai package Python maintenable, par exemple :

```text
src/onetech_ao/__init__.py
src/onetech_ao/config.py
src/onetech_ao/database.py
src/onetech_ao/haicop.py
src/onetech_ao/collector.py
src/onetech_ao/cli.py
```

Ajoute la gestion des dépendances nécessaire, sans surcharger le projet.

Dépendances probables :

- `psycopg` avec support binaire
- `python-dotenv`
- `requests` ou `httpx`
- `beautifulsoup4` si nécessaire pour les pages détail
- `pytest` pour les tests Python

#### 4. Comportement du collecteur

Le collecteur doit :

- Lire sa configuration depuis `.env`.
- Vérifier la connexion PostgreSQL.
- Utiliser uniquement les endpoints publics HAICOP documentés dans la skill.
- Ajouter des timeouts HTTP, un User-Agent et une gestion d’erreurs.
- Collecter les appels d’offres DataTables.
- Normaliser les identifiants, dates, booléens et champs texte.
- Conserver le payload HAICOP original dans `donnees_brutes`.
- Enrichir avec la page détail lorsque demandé.
- Extraire les liens publics `/storage/tender/`.
- Ne jamais contourner TUNEPS ou une authentification.
- Créer une ligne `collectes_haicop` au début.
- Effectuer des UPSERT sur `appels_offres` avec `tender_id`.
- Effectuer des UPSERT sur `documents_ao` avec `(tender_id, url)`.
- Mettre à jour `derniere_collecte_le`.
- Terminer `collectes_haicop` avec les bons compteurs.
- En cas d’échec, enregistrer `statut=echec` et une erreur concise sans secret.

#### 5. CLI

Ajoute une CLI claire, par exemple :

```powershell
python -m onetech_ao.cli collect --limit 50
python -m onetech_ao.cli collect --limit 20 --with-details
python -m onetech_ao.cli status
python -m onetech_ao.cli list-open --limit 20
```

Prévois éventuellement :

- `--dry-run`
- `--since-days`
- `--with-details`

#### 6. Skill OpenClaw

Mets à jour :

```text
skills/collecte-haicop-ao/SKILL.md
```

La skill doit utiliser le nouveau collecteur Python/PostgreSQL au lieu de
seulement décrire manuellement l’endpoint.

Quand je demande :

```text
collecte les AO HAICOP récentes
```

OpenClaw doit :

- vérifier que PostgreSQL est accessible ;
- lancer la CLI ;
- stocker les résultats ;
- retourner le nombre reçu, inséré, mis à jour et les erreurs ;
- proposer une shortlist concise.

#### 7. Tests obligatoires

- Tests unitaires de parsing/normalisation.
- Test de connexion PostgreSQL.
- Test d’upsert.
- Première vraie collecte.
- Deuxième collecte identique.
- Confirmer qu’il n’existe aucun doublon.
- Confirmer que les compteurs de `collectes_haicop` sont corrects.
- Confirmer que le payload brut est conservé.
- Confirmer que les documents sont uniques par `tender_id + url`.

#### 8. Critères d’acceptation

- Docker/PostgreSQL reste `healthy`.
- Les migrations restent idempotentes.
- Le collecteur peut être lancé indépendamment d’OpenClaw.
- La skill OpenClaw sait ensuite l’appeler.
- Deux exécutions ne créent aucun doublon.
- Aucun mot de passe n’est committé ou affiché.
- Aucune donnée de test factice ne reste en production.
- Le README explique installation, lancement, architecture et dépannage.
- Le worktree final est propre.
- Crée des commits locaux logiques, mais ne pousse rien.

#### 9. Ne commence pas encore

- Odoo
- MCP
- n8n
- email automatique
- Telegram/Discord
- Microsoft Phi

Ces briques viendront après validation complète de :

```text
HAICOP → PostgreSQL → digest local
```

#### 10. Rapport final obligatoire

À la fin :

- donne-moi les commandes exactes exécutées ;
- les fichiers créés/modifiés ;
- les tests et résultats ;
- les nombres de lignes avant/après les deux collectes ;
- le ou les hashes des commits locaux ;
- un point de reprise clair pour la prochaine étape.

Commence par auditer les fichiers existants, puis implémente tout ce workflow
de manière autonome.

## Règle de sécurité importante

Ne donne pas le mot de passe PostgreSQL dans le chat. Il se trouve déjà dans
`.env`, dans le workspace entreprise.

## Réparation facultative de l’index mémoire

La recherche mémoire sémantique OpenClaw peut être en pause si l’index a été
construit avec un ancien fournisseur ou modèle d’embeddings. Vérifier d’abord :

```powershell
openclaw memory status --index
```

Puis reconstruire si nécessaire :

```powershell
openclaw memory index --force
```

Cette réparation n’est pas nécessaire pour réaliser l’intégration PostgreSQL :
les fichiers réels de ce workspace restent la source de vérité.
