# OneTech Tender Agent — rapport de finalisation

Date de validation : 25 août 2026

## Périmètre

Le projet est finalisé sans Odoo, conformément à la demande. Le seul
branchement externe non activé est Telegram : l'implémentation est terminée,
mais l'association finale exige une session Telegram Web humaine et un bot
OneTech distinct du bot personnel.

## Capacités opérationnelles

- Collecte publique HAICOP avec pagination, normalisation et détails.
- PostgreSQL 16 avec journal de collecte, UPSERT et contraintes anti-doublon.
- Téléchargement public borné, stockage local, SHA-256 et reprise idempotente.
- Extraction PDF/DOCX, OCR PDF/image et conversion contrôlée des anciens DOC.
- Contexte d'analyse borné, fiches Go/No-Go et scoring persisté séparément des
  faits officiels.
- Digest quotidien n8n à 08:00 Europe/Paris les jours ouvrés.
- Mailpit local et Gmail réel vers une liste de deux destinataires, avec preuve
  et anti-doublon par destinataire.
- Telegram : digest découpé, ledger par fragment, mentions/réponses, offset
  durable, contenu non stocké en clair et garde contre le bot personnel.
- Serveur MCP `onetech-tender` avec exactement cinq outils bornés.
- Ollama/Phi-4 Mini installé dans l'OpenClaw entreprise comme second avis local.
- Sauvegarde/restauration complète, manifestes et checksums SHA-256.
- Démarrage Windows au logon et watchdog toutes les cinq minutes.

## Snapshot de données validé

- 100 appels d'offres.
- 152 documents : 41 PDF, 35 DOC, 74 DOCX, 1 PNG et 1 JPEG.
- 152/152 fichiers présents.
- 152/152 empreintes SHA-256 présentes.
- 152/152 textes extraits.
- 0 doublon AO.
- 0 doublon document.
- 0 document en attente, sans texte, non supporté ou en échec.

## Vérifications exécutées

- 67/67 tests Python réussis.
- 6/6 scripts SQL réussis avec rollback des données factices.
- Smoke test réel Tesseract + LibreOffice réussi.
- MCP doctor réussi ; probe : 5 outils.
- Appel MCP en langage naturel réussi avec
  `list_open_tenders(limit=2)` et zéro échec outil.
- Healthcheck global réussi : Docker, PostgreSQL, pgAdmin, Mailpit, n8n,
  ao-worker, workflow quotidien, gateway entreprise, Ollama et MCP.
- Tâches Windows `Stack` et `Watchdog` validées avec résultat `0x0` et autorisées
  sur batterie.
- Workflow quotidien actif ; workflow Telegram inactif par conception tant que
  sa configuration dédiée n'est pas valide.

## Phi-4 Mini

Le benchmark CPU a obtenu les deux décisions `NO_GO` attendues, avec 79 à
105 secondes par AO. Le verdict reste `PARTIAL` car certaines justifications
sont inventées. Phi ne remplace donc pas le modèle de production et ne prend
jamais seul une décision finale.

Le modèle `ollama/phi4-mini:latest` est visible dans la liste des modèles de
l'OpenClaw entreprise. Son profil fournisseur est limité aux cinq outils MCP
OneTech afin d'éviter d'injecter les outils génériques inutiles.

Un tour réel complet via le gateway entreprise a terminé avec le fournisseur
Ollama après environ 241 secondes. La réponse était exploitable mais n'a pas
respecté exactement l'instruction courte demandée, ce qui confirme son statut
de modèle expérimental lent plutôt que de moteur de production.

## Sauvegarde et restauration

Sauvegarde v2 validée :

```text
backups/onetech-20260825-025129
187 fichiers — 34 455 690 octets
```

Elle contient le dump PostgreSQL, les workflows et l'état n8n cohérent, 152
documents, les contextes, digests, fiches et une configuration OpenClaw
assainie. `.env`, tokens, mots de passe et clés ne sont pas sauvegardés.

Le drill a restauré et vérifié les neuf tables dans une base temporaire, puis
l'a supprimée :

```text
backups/restore-drill-reports/restore-drill-20260825-025651.json
status=passed
temporary_database_removed=true
```

## État Telegram et action humaine restante

La valeur actuelle reste :

```env
TELEGRAM_ENABLED=false
```

Cette désactivation est volontaire : le token disponible appartient aussi au
bot personnel et l'ancien `TELEGRAM_CHAT_ID` identifiait un chat privé. Faire
tourner deux pollers aurait provoqué des conflits et des réponses du mauvais
agent.

Pour terminer le branchement externe :

1. Reconnecter Telegram Web dans le profil Chrome orange OpenClaw.
2. Créer un bot OneTech dédié via BotFather.
3. Ajouter ce bot au groupe OneTech déjà créé et le mentionner une fois.
4. Configurer son token et l'identifiant négatif du groupe.
5. Passer `TELEGRAM_ENABLED=true`, recréer `ao-worker`/n8n et lancer le test.

Le démarrage et le watchdog refuseront automatiquement un token partagé, un
chat privé ou une configuration incomplète. Le script d'activation manuelle
applique la même garde et remet le workflow à l'état inactif en cas de refus.

## Git

Commits fonctionnels séparés créés localement :

```text
b294237 feat(documents): add OCR and legacy DOC extraction
0fe4e35 feat(mcp): expose bounded tender tools
836f9b7 feat(telegram): add safe group digest and replies
3f7de48 feat(ops): add backup restore and watchdog
b7bd41f fix(telegram): guard manual workflow activation
```

Aucun push GitHub n'a été effectué pendant cette finalisation. Le cours
`docs/COURS_POSTGRES_TABLES.md` et la fiche historique générée restent locaux
et explicitement exclus du suivi Git.

## Odoo

Aucun conteneur, module, modèle ou connecteur Odoo n'a été ajouté.
