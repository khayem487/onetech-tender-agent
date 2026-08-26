# Soutenance de stage — OneTech Tender Agent

**Durée cible : 15 à 20 minutes, démonstration comprise.**

**Source de génération :** `_tools/generate_soutenance.py`
**Livrable :** `PRESENTATION_SOUTENANCE_KHAYEM_BEN_GHORBEL.pptx`

La présentation suit exactement le plan transmis par CY Tech : entreprise,
mission, outils, solutions/tâches réalisées, compétences techniques et soft
skills. Elle présente uniquement les réalisations validées du stage.

## 1 — Titre et promesse livrée

- OneTech Tender Agent
- Système IA agentique pour collecter, analyser et diffuser les AO publics
- 100 AO · 152 documents · 67/67 tests Python

## 2 — Entreprise d’accueil

- One Tech Business Solutions
- Développement logiciel, intégration SI, Data/IA et automatisation
- Contexte métier : structurer la veille sur les marchés publics

## 3 — Problème métier

- Information dispersée entre listes, pages détail et pièces jointes
- Formats hétérogènes
- Risque opérationnel sur les échéances et critères
- Besoin d’un dossier unique et explicable

## 4 — Mission réalisée

Six capacités reliées dans un même MVP : collecte, stockage, extraction,
analyse, automatisation et interopérabilité.

## 5 — Architecture agentique

OpenClaw orchestre ; le modèle interprète ; Python/SQL/OCR exécutent les tâches
déterministes ; les skills bornent la procédure.

## 6 — Architecture de bout en bout

HAICOP → acquisition → PostgreSQL → intelligence → n8n/Gmail/Telegram.

## 7 — Traçabilité PostgreSQL

Séparation des faits officiels, preuves documentaires et analyses. Hashes,
contraintes uniques, UPSERT et historique rendent le système rejouable.

## 8 — Pipeline documentaire

Téléchargement contrôlé, type réel, SHA-256, extraction native, OCR Tesseract,
conversion LibreOffice et persistance. Résultat : 152/152.

## 9 — Analyse Go/No-Go

Contexte hashé, fiche en neuf sections, quatre critères sur 25, décision liée
aux sources et replay sans doublon.

## 10 — Automatisation multicanale

n8n déclenche le worker et OpenClaw ; PostgreSQL conserve le registre ; Mailpit,
Gmail et Telegram assurent la diffusion sans double envoi.

## 11 — Interopérabilité MCP

Cinq outils bornés réutilisent la même logique métier et la même base :
collecte, liste, détail, analyse et digest.

## 12 — Résultats validés

- 100 AO centralisées
- 152/152 documents traités
- 0 doublon détecté
- 67/67 tests Python et 6/6 scripts SQL
- 5/5 outils MCP

## 13 — Démonstration

Quatre preuves : données PostgreSQL, fiche Go/No-Go, replay idempotent et
diffusion n8n/Gmail/Telegram.

## 14 — Garde-fous livrés

SHA-256, idempotence, outils bornés, séparation faits/raisonnement, tests,
sauvegarde/restauration et validation humaine.

## 15 — Compétences développées

### Techniques

Python, API, PostgreSQL, JSONB, Docker, n8n, OpenClaw, MCP, OCR, tests et sécurité.

### Soft skills

Autonomie, communication, organisation, esprit critique, persévérance et
responsabilité.

## 16 — Conclusion

Une chaîne de décision explicable, testée et réutilisable. Les faits sont
centralisés, les analyses sont traçables et la diffusion est idempotente.

**Fin : Merci — Questions.**
