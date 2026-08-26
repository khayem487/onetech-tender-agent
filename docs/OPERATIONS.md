# Exploitation locale — OneTech Tender Agent

Ce document couvre le démarrage, la supervision, Telegram et la reprise après
incident. Il ne contient aucun mot de passe : les secrets restent dans `.env`.

## Démarrage et vérification

```powershell
cd C:\Users\khaye\.openclaw-company\workspace
.\scripts\start-onetech-stack.ps1 -StartGateway -StartOllama
.\scripts\healthcheck-onetech-stack.ps1 `
  -RequireGateway -RequireOllama -RequireWorkflows -RequireMcp
```

Le démarrage lance Docker Desktop si nécessaire, applique les migrations SQL,
active le digest n8n, démarre Ollama et supervise uniquement le gateway
entreprise sur `127.0.0.1:18790`. Le gateway personnel n'est jamais touché.

Les journaux persistants se trouvent sous `logs/operations/`.

## Démarrage manuel

Le projet ne crée aucune tâche planifiée Windows. Il est lancé à la demande
avec `start-onetech-stack.ps1`, puis contrôlé ponctuellement avec
`healthcheck-onetech-stack.ps1`. Cette exploitation manuelle évite tout
démarrage de Docker ou d’OpenClaw à l’ouverture de la session Windows.

## Telegram : canal opérationnel

Le bot OneTech et le groupe dédié sont configurés localement. Les valeurs
sensibles restent dans `.env` et ne sont jamais versionnées :

```env
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=<token_du_bot_onetech>
TELEGRAM_CHAT_ID=-1001234567890
AUTOMATION_DELIVERY_ARGS=--mailpit --email --telegram
```

Pour réactiver le canal après une reconstruction de la stack :

```powershell
docker compose up -d --force-recreate ao-worker n8n
.\scripts\activate-telegram-automation.ps1
```

Le démarrage refuse automatiquement un chat privé, un token invalide ou le
token du bot personnel. Dans ces cas, il force le workflow Telegram à l'état
inactif. Le bot ne répond qu'aux commandes, mentions ou réponses à ses propres
messages ; les autres conversations du groupe sont ignorées.

## Sauvegarde complète

```powershell
.\scripts\backup-onetech-stack.ps1
```

Chaque sauvegarde v2 horodatée sous `backups/` contient :

- dump PostgreSQL au format custom et compteurs de contrôle ;
- définitions des workflows n8n et état SQLite cohérent ;
- documents, contextes d'analyse, digests et fiches ;
- prompts, migrations et définitions de workflows du projet ;
- configuration OpenClaw assainie ;
- `manifest.json` et checksums SHA-256 de tous les fichiers.

L'état n8n est brièvement arrêté pendant sa copie afin d'obtenir un snapshot
cohérent. `.env`, les tokens, mots de passe et clés de chiffrement ne sont
jamais sauvegardés. Mailpit est facultatif :

```powershell
.\scripts\backup-onetech-stack.ps1 -IncludeMailpit
```

## Drill de restauration sans toucher à la production

```powershell
.\scripts\test-onetech-backup-restore.ps1
```

Le script sélectionne la dernière sauvegarde valide, restaure PostgreSQL dans
une base temporaire au nom strict, compare les compteurs, écrit un rapport JSON
et supprime la base temporaire même après un échec.

## Restauration explicite

Restaurer PostgreSQL dans une base isolée :

```powershell
.\scripts\restore-onetech-stack.ps1 `
  -BackupDirectory .\backups\onetech-YYYYMMDD-HHMMSS `
  -RestorePostgres `
  -TargetDatabase onetech_restore_review `
  -ConfirmRestore 'RESTORE:onetech_restore_review'
```

La restauration en place est volontairement plus stricte :

```powershell
.\scripts\restore-onetech-stack.ps1 `
  -BackupDirectory .\backups\onetech-YYYYMMDD-HHMMSS `
  -RestorePostgres `
  -TargetDatabase onetech_ao `
  -ReplaceTargetDatabase `
  -AllowInPlaceDatabaseRestore `
  -ConfirmRestore 'RESTORE-IN-PLACE:onetech_ao'
```

Le script crée d'abord un dump de sécurité, arrête les services dépendants,
restaure puis vérifie les compteurs. Les autres composants s'activent
séparément avec `-RestoreN8nState`, `-RestoreN8nWorkflows`,
`-RestoreProjectData` ou `-RestoreCompanyConfig` et la confirmation exacte
`RESTORE:COMPONENTS`.

Une configuration OpenClaw assainie ne peut jamais écraser directement
`openclaw.json` : restaure-la vers un fichier de revue, puis réinjecte les
secrets locaux manuellement. La restauration des données projet conserve les
fichiers remplacés sous `.onetech-restore-safety/`.

## Diagnostic rapide

```powershell
docker compose ps
docker exec onetech-ao-worker python -m onetech_ao.cli status
docker exec onetech-n8n n8n list:workflow --active=true
ollama list
C:\Users\khaye\.openclaw-company\openclaw.cmd mcp doctor
```

Le digest n8n doit être actif. Telegram doit être actif uniquement après une
configuration dédiée valide.
