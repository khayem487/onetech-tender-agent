# Passation complete pour ChatGPT / Claude

## Rapport de stage et presentation de soutenance — OneTech Tender Agent

**Date de la passation :** 26 aout 2026
**Etudiant :** Khayem Ben Ghorbel
**Depot prive :** `https://github.com/khayem487/onetech-tender-agent`
**Branche :** `main`
**Commit de reference des livrables actuels :** `b5dc182`
**Workspace local :** `C:\Users\khaye\.openclaw-company\workspace`

---

## 1. A quoi sert ce fichier

Ce document contient le contexte necessaire pour qu'un autre ChatGPT ou Claude
puisse **ameliorer serieusement le rapport de stage et la presentation de
soutenance**, regenerer les formats editables et PDF, effectuer les controles
qualite, puis pousser uniquement les changements intentionnels sur le depot
GitHub prive.

Il est volontairement autonome. Il fixe :

- les consignes officielles de CY Tech ;
- les faits verifies sur l'etudiant, l'entreprise et le stage ;
- le perimetre reellement implemente ;
- l'architecture et les resultats mesures ;
- les fichiers canoniques a lire ;
- les anciens brouillons a ignorer ;
- les affirmations interdites ;
- les livrables attendus ;
- le workflow de generation, de QA et de publication Git.

> **Regle de securite :** ce fichier ne contient aucun token, secret OAuth,
> cle de chiffrement ou valeur de `.env`. Le `README.md` du depot prive contient
> toutefois des mots de passe locaux de demonstration, ajoutes a la demande de
> l'utilisateur. Ne jamais recopier ces mots de passe dans un prompt, un
> livrable public ou une reponse. Les renouveler avant de partager le depot avec
> un tiers.

---

## 2. Prompt pret a copier-coller

Copier le bloc suivant dans ChatGPT ou Claude apres lui avoir donne acces au
depot prive, ou apres avoir televerse ce fichier et les sources listees plus bas.

```text
Tu es a la fois redacteur technique senior, designer de presentations et
ingenieur QA documentaire. Tu dois ameliorer les livrables finaux du stage de
Khayem Ben Ghorbel portant sur OneTech Tender Agent.

DEPOT ET WORKSPACE
- Depot GitHub prive : https://github.com/khayem487/onetech-tender-agent
- Branche : main
- Workspace Windows si disponible :
  C:\Users\khaye\.openclaw-company\workspace

COMMENCE PAR LIRE INTEGRALEMENT
1. docs/HANDOFF_CHATGPT_CLAUDE_RAPPORT_PRESENTATION_2026-08-26.md
2. livrables/RAPPORT_STAGE_FINAL.md
3. livrables/PRESENTATION_SOUTENANCE_FINALE.md
4. livrables/_presentation_notes.json
5. docs/DELIVERABLES_FINAL_QA_2026-08-26.md
6. docs/PROJECT_COMPLETION_REPORT_2026-08-25.md
7. config/profil_entreprise.md
8. config/automation.json
9. README.md, sans recopier ses mots de passe
10. les cinq PNG de livrables/visuals/
11. scripts/build-deliverable-visuals.py
12. scripts/build-livrables.py
13. scripts/export-livrables-office.ps1

Inspecte aussi les DOCX, PPTX et PDF actuels comme baselines visuelles.

OBJECTIF
Ameliore fortement le rapport et la presentation. Le resultat doit etre
professionnel, visuel, coherent, academique et facile a presenter. Il doit se
concentrer uniquement sur les travaux reellement realises et valides.

CONSIGNES CY TECH
- La soutenance doit avoir lieu avant le 25 septembre 2026.
- L'expose dure 15 a 20 minutes, puis peut etre suivi de questions.
- La soutenance peut etre faite a distance.
- L'expose doit presenter :
  1. l'entreprise ;
  2. la mission du stage ;
  3. les outils utilises ;
  4. les solutions apportees et taches realisees ;
  5. les competences techniques et soft skills acquises.

REGLES STRICTES
- Redige en francais professionnel et naturel.
- Concentre-toi sur les realisations et les preuves.
- Ne mentionne jamais Odoo, ni comme manque, ni comme limite, ni comme suite.
- N'ajoute pas de liste de fonctionnalites non realisees ou d'idees rejetees.
- Ne remets pas de contenu que l'utilisateur avait retire.
- Ne presente jamais Telegram comme desactive : il est actif et valide.
- Ne presente jamais le watchdog ou un demarrage Windows automatique : ils ont
  ete supprimes. Le demarrage est manuel.
- N'utilise jamais l'ancien score 100/100 : c'etait un faux positif historique.
- Ne presente pas Phi-4 Mini comme modele de production ou decideur principal.
- Ne dis pas que l'IA prend seule une decision commerciale : la validation
  humaine reste obligatoire.
- Ne pretends pas contourner TUNEPS ou collecter des donnees authentifiees.
- N'appelle pas le systeme production-ready. Utilise : MVP operationnel,
  valide et demonstrable.
- N'invente aucune donnee entreprise, ROI, gain de temps, precision, rappel,
  taux de succes, deploiement en production, tuteur academique, date de
  soutenance, adresse ou fonction professionnelle non verifiee.
- N'expose aucun secret ou mot de passe dans les livrables.
- Ne lis pas et ne versionne pas les quatre vieux brouillons non suivis indiques
  dans la passation.

RAPPORT
- Ameliore le contenu canonique au lieu de repartir aveuglement de zero.
- Conserve une structure academique substantielle.
- La baseline actuelle fait 32 pages A4 ; aucune limite de pages officielle ne
  figure dans les consignes disponibles.
- Integre des diagrammes, tableaux, encadres, metriques et illustrations utiles.
- Evite les repetitions, le remplissage et les longs blocs de code.
- Conserve un resume francais, un abstract anglais, une bibliographie, un
  glossaire et des annexes utiles.

PRESENTATION
- Produis un PowerPoint editable, visuellement riche, pour 15 a 20 minutes.
- Cible 14 a 16 diapositives et environ 16 a 18 minutes avec une courte demo.
- Ajoute des notes orateur a chaque diapositive.
- Utilise peu de texte a l'ecran et privilegie schemas, flux, chronologie,
  cartes de metriques et preuves visuelles.
- Reutilise ou ameliore les cinq visuels existants.
- N'ajoute pas de faux screenshots ou d'interfaces inventees.

REPRODUCTIBILITE
- Modifie les sources Markdown et les scripts de generation si necessaire.
- Regenere les DOCX, PPTX et PDF ; ne modifie pas seulement les binaires.
- Garde les declarations de source coherentes avec le pipeline reel.

LIVRABLES A PRODUIRE
- livrables/RAPPORT_STAGE_FINAL.md
- livrables/RAPPORT_STAGE_KHAYEM_BEN_GHORBEL.docx
- livrables/RAPPORT_STAGE_KHAYEM_BEN_GHORBEL.pdf
- livrables/PRESENTATION_SOUTENANCE_FINALE.md
- livrables/PRESENTATION_SOUTENANCE_KHAYEM_BEN_GHORBEL.pptx
- livrables/PRESENTATION_SOUTENANCE_KHAYEM_BEN_GHORBEL.pdf
- notes orateur completes
- visuels rafraichis si necessaire
- rapport QA concis

QA OBLIGATOIRE
- Rends et inspecte chaque page et chaque slide.
- Aucun chevauchement, clipping, page blanche, slide vide, accent casse,
  Markdown brut ou Mermaid brut.
- Verifie la coherence des faits et metriques dans tous les formats.
- Verifie les notes sur 100 % des slides et la duree de 15 a 20 minutes.
- Execute la suite Python et les six tests SQL si l'environnement le permet.
- Execute git diff --check.
- Scanne les fichiers modifies pour les tokens/secrets.
- Verifie que .env n'est pas suivi.
- Preserve les changements appartenant a l'utilisateur.

GIT
- Inspecte git status avant toute modification.
- N'utilise jamais git add . ; ajoute uniquement les chemins intentionnels.
- Ne versionne jamais les quatre anciens brouillons non suivis.
- Ne force-push jamais.
- Apres QA reussie, cree un commit clair, par exemple :
  docs: improve internship report and defense presentation
- Pousse main vers le remote prive existant.
- Verifie le commit distant.

COMPTE RENDU FINAL
Retourne les fichiers modifies, les tests, le nombre de pages/slides, la duree
estimee, le hash du commit, l'URL GitHub et uniquement les confirmations
utilisateur reellement indispensables.

Si une information administrative obligatoire manque, demande-la. Si elle est
optionnelle, omets-la au lieu de l'inventer.
```

---

## 3. Exigences officielles de soutenance

Le message transmis aux etudiants ING1-GI 2025-2026 indique :

- contacter le tuteur attribue afin de definir une date ;
- effectuer la soutenance avant le **25 septembre 2026** ;
- faire un expose de **15 a 20 minutes** ;
- prevoir de possibles questions apres l'expose ;
- possibilite de soutenance a distance ;
- presenter obligatoirement :
  - l'entreprise ;
  - la mission du stage ;
  - les outils utilises ;
  - les solutions apportees et les taches realisees ;
  - les competences techniques et soft skills acquises.

Le fichier `liste_tuteurs_stage.pdf.pdf` n'est pas dans le depot. Le nom du
tuteur academique et la date exacte de soutenance sont inconnus. Ne pas les
inventer.

---

## 4. Faits administratifs et identitaires verifies

| Champ | Valeur verifiee |
|---|---|
| Etudiant | Khayem Ben Ghorbel |
| Ecole | CY Tech |
| Formation | Cycle ingenieur — Informatique — ING1 / GI |
| Annee universitaire | 2025-2026 |
| Entreprise d'accueil | One Tech Business Solutions |
| Groupe | One Tech Group |
| Encadrant entreprise | Makram Ben Hamed |
| Fonction exacte de Makram | Non verifiee — ne pas inventer |
| Sujet officiel | Developpement d'un systeme IA agentique pour la gestion des appels d'offres publics |
| Nom du projet | OneTech Tender Agent |
| Periode utilisee dans les livrables | 26 juin au 26 aout 2026 |
| Source de donnees | Ressources publiques HAICOP / marchespublics.gov.tn |

Contexte administratif conserve dans les archives : stage a temps plein,
35 heures par semaine. Ne mentionner d'autres chiffres administratifs que s'ils
sont utiles et verifies dans les documents officiels fournis par l'utilisateur.

---

## 5. Profil entreprise autorise

Le profil OneTech V1 valide pour le prototype couvre :

- developpement logiciel ;
- integration de systemes et de systemes d'information ;
- IA et Data ;
- automatisation ;
- solutions numeriques et transformation digitale.

Les AO favorisees concernent logiciels, applications web, plateformes
numeriques, SI, integration, IA, Data et automatisation. Les AO clairement hors
IT sont penalisees.

Ne pas inventer :

- effectif ;
- chiffre d'affaires ;
- certifications ;
- technologies internes precises ;
- annees d'existence ;
- references commerciales ;
- organigramme ;
- fonction exacte de Makram.

Source canonique : `config/profil_entreprise.md`.

---

## 6. Histoire du projet

### 26 juin 2026 — cadrage

- Confirmation du sujet officiel.
- Objectif pedagogique : comprendre l'IA agentique, la difference entre un
  agent et son modele, et le fonctionnement d'OpenClaw.
- Choix des donnees publiques tunisiennes HAICOP comme premiere source.

### 7 juillet 2026 — premier PoC

- Methode de collecte HAICOP documentee.
- Collecte de donnees et documents publics sans contourner les limites
  d'authentification.
- Trois premieres fiches d'analyse conservees.

### 8 juillet 2026 — retour encadrant

- Retour positif sur le premier PoC.
- Exploration de briques d'entreprise : PostgreSQL, envoi quotidien, Telegram
  ou Discord, n8n, MCP et petit modele Microsoft Phi sur CPU.

### 20 juillet 2026 — choix de la premiere tranche bout en bout

```text
HAICOP -> PostgreSQL -> digest local
```

- L'idempotence et un test en deux executions sont retenus comme criteres.

### 4 aout 2026 — infrastructure donnees

- PostgreSQL 16 sous Docker Compose.
- Volumes persistants, healthcheck et pgAdmin.

### 8 aout 2026 — collecteur vers PostgreSQL

- Package Python maintenable et CLI JSON.
- Pagination, normalisation, timeouts/retries, TLS et parsing des details.
- Journal de collecte, UPSERT et conservation du JSON brut.
- Deux executions identiques prouvent l'absence de doublons.

### 10 aout 2026 — documents et analyse

- Telechargement borne et resumable.
- SHA-256, extraction PDF/DOCX et statuts de traitement.
- Contexte d'analyse PostgreSQL empreinte.
- Fiches Go/No-Go en neuf sections et analyses persistees sans doublon.

### 11 au 17 aout 2026 — automatisation quotidienne

- `ao-worker` authentifie entre n8n et OpenClaw entreprise.
- Digest planifie a 08:00 les jours ouvres, fuseau Europe/Paris.
- Mailpit puis Gmail OAuth multi-destinataires.
- Registre de diffusion anti-doublon.

### 18 au 25 aout 2026 — finalisation

- OCR Tesseract pour les scans et images.
- Conversion LibreOffice pour anciens DOC.
- Telegram groupe + reponses aux mentions.
- Serveur MCP a cinq outils.
- Evaluation Phi-4 Mini via Ollama comme second avis.
- Sauvegarde avec checksums et restauration isolee testee.
- Healthcheck manuel.

### 26 aout 2026 — livrables

- Rapport, presentation, notes, visuels et QA regeneres.
- Validation finale et push du commit `b5dc182`.

---

## 7. Architecture finale verifiee

```text
HAICOP public
  -> collecteur Python
  -> normalisation des AO, details et documents
  -> PostgreSQL 16
  -> telechargement borne
  -> empreinte SHA-256
  -> extraction native PDF / DOCX
  -> conversion LibreOffice des anciens DOC
  -> Poppler + Tesseract OCR (francais, arabe, anglais)
  -> texte extrait dans PostgreSQL
  -> skills OpenClaw entreprise
  -> contexte semantique empreinte
  -> analyse Go/No-Go en neuf sections
  -> score, decision et preuve persistes
  -> n8n + ao-worker
  -> Mailpit + Gmail + Telegram
```

### Services Docker Compose

| Service | Role |
|---|---|
| `postgres` | PostgreSQL 16, source de verite |
| `pgadmin` | administration graphique PostgreSQL |
| `mailpit` | SMTP et boite locale de test |
| `ao-worker` | bridge FastAPI/Python borne vers OpenClaw |
| `n8n` | planification et historique des workflows |

Volumes persistants :

- `onetech_postgres_data` ;
- `onetech_pgadmin_data` ;
- `onetech_n8n_data` ;
- `onetech_mailpit_data`.

Les ports sont lies a `127.0.0.1`. Les secrets sont lus depuis `.env`, ignore
par Git.

L'instance OpenClaw entreprise est separee de l'instance personnelle : gateway
local sur le port `18790`. Ollama tourne sur l'hote lorsque Phi est utilise.

Le demarrage est **manuel**. Il n'existe plus de watchdog recurrent ni de tache
d'ouverture automatique au demarrage Windows.

---

## 8. PostgreSQL et tracabilite

### Migrations

| Migration | Objets principaux |
|---|---|
| `001_schema.sql` | collectes, AO, documents, vue AO ouvertes |
| `002_document_processing.sql` | statuts, MIME, taille, extraction/OCR |
| `003_analysis.sql` | analyses et vue derniere analyse |
| `004_analysis_audit.sql` | unicite du contexte et snapshot d'audit |
| `005_automation.sql` | executions quotidiennes, candidats, diffusions |
| `006_delivery_idempotence.sql` | unicite destinataire/canal/hash |
| `007_telegram.sql` | etat du polling et interactions Telegram |

### Principes importants

- donnees HAICOP originales conservees en JSONB ;
- faits officiels, preuves documentaires et raisonnement IA separes ;
- transactions et contraintes d'integrite ;
- UPSERT sur les identifiants stables ;
- aucune duplication lors des replays ;
- audit des collectes et des diffusions ;
- fingerprint SHA-256 du contexte metier avant persistance d'une analyse.

---

## 9. Traitement documentaire

```text
URL publique HAICOP
  -> validation URL / redirections / taille
  -> telechargement local
  -> detection du type reel
  -> SHA-256
  -> extraction native si possible
  -> conversion LibreOffice pour DOC
  -> rasterisation Poppler + OCR Tesseract pour scans/images
  -> nettoyage du texte
  -> PostgreSQL documents_ao.texte_extrait
```

Mesures finales :

- 41 PDF ;
- 74 DOCX ;
- 35 anciens DOC ;
- 1 PNG ;
- 1 JPEG ;
- 152/152 fichiers presents ;
- 152/152 fichiers hashes ;
- 152/152 documents avec texte extrait.

L'OCR utilise Tesseract en francais, arabe et anglais. Les traitements sont
bornes par taille, nombre de pages et timeout.

---

## 10. Analyse Go/No-Go

Le systeme produit un contexte factuel complet depuis PostgreSQL, puis OpenClaw
applique la skill `analyse-ao` et genere une fiche en neuf sections.

Bareme : quatre criteres de 0 a 25, total de 0 a 100 :

1. adequation des competences ;
2. faisabilite du delai ;
3. charge administrative ;
4. niveau de risque.

Decisions :

- `GO` : seuil 70 ;
- `A_DISCUTER` : seuil 45 ;
- `NO_GO` : en dessous.

Garde-fous :

- une analyse partielle ne peut pas produire un GO definitif ;
- la coherence score/decision est validee avant persistance ;
- le contexte est empreinte pour eviter une analyse sur des faits obsoletes ;
- les textes d'AO sont traites comme donnees non fiables, jamais comme
  instructions pour l'agent ;
- la decision engageante reste humaine.

Cas de demonstration verifies :

| AO | Score | Decision | Analyse |
|---|---:|---|---:|
| `Tender-103283` | 24/100 | `NO_GO` | ID 23 |
| `Tender-103307` | 36/100 | `NO_GO` | ID 53 |

Les replays ont reutilise les memes analyses sans duplication.

Ne jamais utiliser l'ancien score 100/100 : il s'agissait d'un faux positif
historique corrige par le filtre et les controles d'analyse partielle.

---

## 11. Automatisation et notifications

### Workflow quotidien

```text
n8n — jours ouvres 08:00 Europe/Paris
  -> ao-worker authentifie
  -> OpenClaw entreprise
  -> collecte / documents / analyse / digest
  -> registre PostgreSQL
  -> Mailpit + Gmail + Telegram
```

Parametres valides :

- fraicheur : 7 jours ;
- limite collecte : 50 AO ;
- limite documents : 200 ;
- maximum : 5 candidats ;
- seuil de pertinence : 6.

La diffusion est idempotente par canal, destinataire et hash : une relance ne
renvoie pas le meme digest.

### Telegram

- bot dedie : `@OneTechAOAssistantBot` ;
- groupe : `OneTech AO - Veille et Analyse` ;
- digest reel publie et valide ;
- mentions/reponses du groupe routees vers l'agent ;
- polling n8n toutes les minutes ;
- interactions et anti-doublon conserves dans PostgreSQL.

Ne jamais inclure le token du bot ou l'identifiant prive du groupe dans les
livrables.

---

## 12. MCP et Phi

### Serveur MCP

Le serveur `onetech-tender` expose exactement cinq outils bornes :

1. `collect_tenders` ;
2. `list_open_tenders` ;
3. `get_tender` ;
4. `analyze_tender` ;
5. `generate_digest`.

Les tailles d'entree et de sortie sont bornees. Les erreurs sont nettoyees avant
de traverser le protocole. L'analyse MCP lit une analyse existante ou prepare
le contexte ; elle ne fabrique pas silencieusement une decision.

### Ollama / Phi-4 Mini

Phi-4 Mini a ete teste localement sur CPU comme **second avis experimental**.
Il a classe correctement les AO de test en NO_GO, mais il etait lent et pouvait
inventer certaines justifications. Il ne doit donc jamais etre presente comme
le modele principal ou comme un decideur de production.

---

## 13. Sauvegarde, restauration et exploitation

- sauvegarde PostgreSQL et configurations avec checksums ;
- restauration reelle dans une base isolee ;
- verification des volumes et compteurs ;
- healthcheck manuel ;
- scripts PowerShell dedies ;
- aucun demarrage automatique Windows ;
- aucun watchdog recurrent.

Commandes de demonstration :

```powershell
.\scripts\start-onetech-stack.ps1 -StartGateway -StartOllama
.\scripts\healthcheck-onetech-stack.ps1 `
  -RequireGateway -RequireOllama -RequireWorkflows -RequireMcp
```

---

## 14. Resultats verifies

| Indicateur | Resultat |
|---|---:|
| Appels d'offres centralises | 100 |
| Documents enregistres | 152 |
| Documents presents / hashes / extraits | 152 / 152 |
| Doublons AO | 0 |
| Doublons documents | 0 |
| Tests Python complets | 67 / 67 |
| Tests SQL | 6 / 6 |
| Outils MCP | 5 / 5 |
| Canaux valides | Mailpit, Gmail, Telegram |

Lorsque Docker est arrete, une execution locale sans tests d'integration donne
62 tests passes et 5 deselectionnes. Le resultat de reference full-stack reste
67 Python + 6 SQL, consigne dans le rapport QA final.

---

## 15. Livrables actuels

### Rapport

- `livrables/RAPPORT_STAGE_FINAL.md` — source canonique ;
- `livrables/RAPPORT_STAGE_KHAYEM_BEN_GHORBEL.docx` — editable ;
- `livrables/RAPPORT_STAGE_KHAYEM_BEN_GHORBEL.html` — source imprimable ;
- `livrables/RAPPORT_STAGE_KHAYEM_BEN_GHORBEL.pdf` — 32 pages A4.

### Presentation

- `livrables/PRESENTATION_SOUTENANCE_FINALE.md` — plan canonique ;
- `livrables/PRESENTATION_SOUTENANCE_KHAYEM_BEN_GHORBEL.pptx` — 16 slides ;
- `livrables/PRESENTATION_SOUTENANCE_KHAYEM_BEN_GHORBEL.pdf` ;
- `livrables/_presentation_notes.json` — notes sur 16/16 slides, 1 599 mots.

Durée actuelle estimee : 16 a 18 minutes, demonstration comprise.

### Annexe

- `livrables/ANNEXE_EVALUATION_STAGE_A_FAIRE_REMPLIR_PAR_MAKRAM.pdf`.

### QA

- `docs/DELIVERABLES_FINAL_QA_2026-08-26.md`.

---

## 16. Visuels disponibles

| Visuel | Fichier |
|---|---|
| Architecture bout en bout | `livrables/visuals/architecture_v2.png` |
| Pipeline documentaire | `livrables/visuals/pipeline_documents.png` |
| Tracabilite PostgreSQL | `livrables/visuals/traceability_data.png` |
| Automatisation multicanale | `livrables/visuals/automation_channels.png` |
| Tableau de resultats | `livrables/visuals/results_dashboard.png` |

Les versions HTML editables se trouvent dans le meme dossier.

Ne pas inventer de captures d'ecran. Une capture n'est acceptable que si elle
provient d'une vraie interface locale et ne revele aucun secret ou donnee
personnelle.

---

## 17. Structure conseillee du rapport

1. Page de garde
2. Remerciements
3. Resume executif en francais
4. Abstract en anglais
5. Table des matieres
6. Introduction generale
7. Entreprise, contexte et problematique
8. Etat de l'art et choix technologiques
9. Besoins, exigences et cas d'usage
10. Conception et architecture
11. Implementation detaillee
12. Validation, tests et resultats
13. Gestion de projet et demarche incrementale
14. Qualite, securite, tracabilite et IA responsable
15. Competences techniques et soft skills
16. Conclusion
17. Glossaire
18. Bibliographie
19. Annexes utiles

Principes de redaction :

- expliquer les choix plutot que lister les technologies ;
- montrer le lien besoin -> decision -> implementation -> preuve ;
- conserver des paragraphes lisibles et des tableaux utiles ;
- limiter les blocs de code ;
- ne pas repeter la meme metrique dans chaque chapitre ;
- inclure uniquement des faits verifies.

---

## 18. Structure conseillee de la presentation

1. Titre et promesse
2. Entreprise d'accueil
3. Probleme metier
4. Mission du stage
5. Agent, modele, skills et outils
6. Architecture bout en bout
7. PostgreSQL et tracabilite
8. Pipeline documentaire et OCR
9. Analyse Go/No-Go
10. n8n, Gmail et Telegram
11. MCP et interoperabilite
12. Resultats mesures
13. Demonstration courte
14. Qualite, securite et garde-fous
15. Competences techniques et soft skills
16. Conclusion et questions

Pour 16 a 18 minutes :

- 30 a 45 secondes pour l'introduction ;
- 45 a 75 secondes par slide de contenu ;
- 2 a 3 minutes pour la demonstration ;
- 30 secondes pour conclure.

Toutes les slides doivent avoir des notes orateur. Le texte affiche doit rester
court et lisible.

---

## 19. Hierarchie des sources

En cas de contradiction, utiliser cet ordre :

1. ce fichier et les demandes les plus recentes de l'utilisateur ;
2. les consignes officielles CY Tech ;
3. `livrables/RAPPORT_STAGE_FINAL.md` ;
4. `livrables/PRESENTATION_SOUTENANCE_FINALE.md` ;
5. `docs/DELIVERABLES_FINAL_QA_2026-08-26.md` ;
6. `docs/PROJECT_COMPLETION_REPORT_2026-08-25.md` ;
7. `config/profil_entreprise.md` et `config/automation.json` ;
8. README, code et tests ;
9. `HISTORY.md` uniquement pour la chronologie historique.

`HISTORY.md` contient encore certains etats historiques devenus faux, par
exemple Telegram desactive ou watchdog present. Ne jamais l'utiliser pour le
statut final sans confirmation dans les sources prioritaires.

---

## 20. Fichiers a ignorer absolument

Ces quatre fichiers sont d'anciens brouillons non suivis par Git :

```text
docs/CURRENT_STATE_AUDIT_2026-08-25.md
docs/DELIVERABLES_BUILD_REPORT_2026-08-25.md
docs/_DRAFT_PRESENTATION_AGENT.md
livrables/PRESENTATION_SOUTENANCE_V1.md
```

Ils ne sont pas des sources canoniques. Ne pas les ajouter, ne pas les pousser
et ne pas reintroduire leur contenu.

---

## 21. Affirmations interdites

Ne jamais :

- parler d'Odoo, meme comme absence, limite ou perspective ;
- dire que Telegram est desactive ;
- dire que le profil OneTech est incomplet : parler du profil V1 valide ;
- dire qu'un watchdog fonctionne ;
- dire que le projet demarre automatiquement avec Windows ;
- utiliser l'ancien score 100/100 ;
- presenter Phi comme modele principal ;
- presenter l'IA comme decideur commercial autonome ;
- affirmer un acces ou contournement TUNEPS ;
- dire que le projet est en production ;
- inventer un ROI, gain de temps, taux de precision, adoption metier ou
  deploiement reel ;
- inventer les informations legales ou financieres de OneTech ;
- inventer le tuteur academique, la date de soutenance ou la fonction de Makram ;
- exposer un mot de passe ou token ;
- presenter les 62 tests hors Docker comme le resultat full-stack final ;
- ajouter des screenshots artificiels ;
- restaurer les passages retires par l'utilisateur.

---

## 22. Fichiers techniques utiles

### Configuration et infrastructure

- `README.md` ;
- `compose.yaml` ;
- `.env.example` ;
- `pyproject.toml` ;
- `config/profil_entreprise.md` ;
- `config/automation.json` ;
- `docs/OPERATIONS.md`.

### Code

- `src/onetech_ao/config.py` ;
- `src/onetech_ao/haicop.py` ;
- `src/onetech_ao/collector.py` ;
- `src/onetech_ao/database.py` ;
- `src/onetech_ao/documents.py` ;
- `src/onetech_ao/analysis.py` ;
- `src/onetech_ao/automation.py` ;
- `src/onetech_ao/telegram.py` ;
- `src/onetech_ao/worker.py` ;
- `src/onetech_ao/mcp_server.py` ;
- `src/onetech_ao/cli.py`.

### Workflows et skills

- `automation/n8n/workflows/daily-digest.json` ;
- `automation/n8n/workflows/telegram-mentions.json` ;
- `skills/collecte-haicop-ao/SKILL.md` ;
- `skills/analyse-ao/SKILL.md`.

### Base et preuves

- `database/README.md` ;
- `database/init/*.sql` ;
- `database/tests/*.sql` ;
- `tests/*.py` ;
- `docs/AUTOMATION_E2E_REPORT_2026-08-11.md` ;
- `docs/POSTGRES_ANALYSIS_E2E_REPORT_2026-08-10.md` ;
- `docs/PROJECT_COMPLETION_REPORT_2026-08-25.md` ;
- `docs/DELIVERABLES_FINAL_QA_2026-08-26.md`.

---

## 23. Generation des livrables

Scripts :

```text
scripts/build-deliverable-visuals.py
scripts/build-livrables.py
scripts/export-livrables-office.ps1
scripts/remove-blank-pdf-pages.py
livrables/_tools/generate_soutenance.py
```

Workflow courant :

```powershell
.\.venv\Scripts\python.exe .\scripts\build-livrables.py
.\scripts\export-livrables-office.ps1
```

Le script Python genere sources Office et visuels. Le script PowerShell exporte
le rapport HTML en PDF et le PowerPoint en PDF. Les fichiers finaux ne doivent
etre remplaces qu'apres une generation reussie.

Conserver l'encodage UTF-8. L'affichage mojibake dans certains terminaux
PowerShell ne signifie pas necessairement que les fichiers sont mal encodes ;
verifier dans Word, PowerPoint, un editeur UTF-8 et les exports PDF.

---

## 24. QA attendue

### Contenu

- faits et metriques coherents dans Markdown, Word, PowerPoint et PDF ;
- seulement du travail realise ;
- aucun placeholder administratif ;
- aucune affirmation interdite ;
- aucun secret.

### Rapport

- aucune page blanche ;
- table des matieres exploitable ;
- numeros de page ;
- titres et figures coherents ;
- aucune coupure ou superposition ;
- visuels lisibles en A4.

### Presentation

- 15 a 20 minutes ;
- notes sur chaque slide ;
- aucun texte trop petit ;
- aucune slide surchargee ;
- aucune superposition ;
- visuels nets ;
- demo faisable sans dependance externe fragile.

### Technique

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\scripts\test-database.ps1
git diff --check
git status --short
```

Le resultat de reference attendu dans l'environnement complet est :

- 67/67 tests Python ;
- 6/6 tests SQL.

Scanner aussi les fichiers modifies pour les formes de tokens, cles et secrets.
Verifier que `.env`, `pgadmin/pgpass`, `data`, `logs` et `backups` ne sont pas
suivis.

---

## 25. Git et push GitHub

Etat de reference avant cette passation :

- branche `main` ;
- remote `origin` vers le depot prive ;
- livrables actuels au commit `b5dc182` ;
- aucun changement suivi ou stage ;
- quatre anciens brouillons non suivis a preserver et ignorer.

Procedure :

```powershell
git status --short
git diff --check
git add <liste explicite des fichiers intentionnels>
git diff --cached --check
git commit -m "docs: improve internship report and defense presentation"
git push origin main
git status --short
git log -1 --oneline
```

Ne jamais utiliser `git add .`. Ne pas force-push. Ne pas ajouter les quatre
brouillons obsoletes. Verifier que le remote est prive avant de pousser.

---

## 26. Informations a demander plutot qu'inventer

- nom du tuteur academique ;
- date et heure exactes de soutenance ;
- format presentiel ou distanciel ;
- template de rapport officiel eventuel ;
- logos officiels fournis par l'ecole ou l'entreprise ;
- informations legales ou financieres de OneTech ;
- adresse exacte de l'entreprise ;
- fonction exacte de Makram Ben Hamed ;
- toute metrique ROI, temps gagne ou precision non mesuree.

Si l'information n'est pas obligatoire, l'omettre. Si elle est indispensable,
poser une question courte a l'utilisateur.

---

## 27. Paquet minimal si le depot GitHub n'est pas connecte

Televerser au modele :

1. ce fichier ;
2. `livrables/RAPPORT_STAGE_FINAL.md` ;
3. `livrables/PRESENTATION_SOUTENANCE_FINALE.md` ;
4. `livrables/_presentation_notes.json` ;
5. `docs/DELIVERABLES_FINAL_QA_2026-08-26.md` ;
6. `docs/PROJECT_COMPLETION_REPORT_2026-08-25.md` ;
7. les cinq PNG de `livrables/visuals/` ;
8. les DOCX/PPTX/PDF actuels si une critique visuelle est demandee.

Ce paquet suffit pour une refonte documentaire. Le code complet est necessaire
uniquement si le modele doit verifier l'implementation, regenerer les visuels
depuis les sources ou executer la QA technique.

---

## 28. Definition de termine

La mission documentaire est terminee seulement si :

- le rapport est plus clair, plus visuel et plus solide academiquement ;
- la presentation est convaincante, concise et presentable en 15 a 20 minutes ;
- chaque slide a des notes ;
- les formats editables et PDF sont regeneres ;
- toutes les pages/slides ont ete inspectees ;
- les metriques et affirmations sont verifiees ;
- aucun secret n'est expose ;
- les vieux brouillons ne sont pas ajoutes ;
- les tests et controles Git passent ;
- le commit est pousse sur `origin/main` ;
- le hash distant et l'URL GitHub sont fournis a l'utilisateur.
