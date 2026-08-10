---
name: "collecte-haicop-ao"
description: "Collecte HAICOP vers PostgreSQL et shortlist OneTech"
---

# Collecte HAICOP AO

Utiliser pour rechercher, lister ou surveiller les appels d'offres tunisiens publiés sur HAICOP/marchespublics.gov.tn, puis pour présélectionner les AO pertinents pour OneTech.

Après la collecte d'un AO précis et de ses documents publics, utiliser `analyse-ao` pour l'analyse complète.

## Source de vérité

Workspace entreprise :

```text
C:\Users\khaye\.openclaw-company\workspace
```

Le package `onetech_ao` encapsule l'endpoint DataTables public, la normalisation, le parsing des pages détail et les UPSERT PostgreSQL. L'utiliser au lieu de redécouvrir ou reconstruire manuellement la requête HAICOP.

Ne jamais lire à voix haute, afficher ou journaliser les valeurs de `.env`.

## Workflow

1. Se placer dans le workspace entreprise.
2. Vérifier PostgreSQL et l'intégrité :

```powershell
.\.venv\Scripts\python.exe -m onetech_ao.cli status
```

3. Collecter les AO récents :

```powershell
.\.venv\Scripts\python.exe -m onetech_ao.cli collect --limit 50
```

Ajouter `--with-details` pour enrichir les pages détail et enregistrer les liens documentaires publics. Utiliser `--since-days N` si l'utilisateur fixe une période. Utiliser `--dry-run` seulement si l'utilisateur demande explicitement une simulation sans stockage.

Pour une collecte complète avec téléchargement, hash et extraction PDF/DOCX :

```powershell
.\.venv\Scripts\python.exe -m onetech_ao.cli collect --limit 50 --with-details --process-documents
```

Pour reprendre uniquement les documents déjà découverts :

```powershell
.\.venv\Scripts\python.exe -m onetech_ao.cli process-documents --limit 50
```

Ajouter `--retry-errors` à `process-documents` uniquement après avoir vérifié la cause des erreurs précédentes.

4. Vérifier après collecte :

```powershell
.\.venv\Scripts\python.exe -m onetech_ao.cli status
```

Confirmer que PostgreSQL répond, que les compteurs du dernier run correspondent à la sortie de collecte, et que `doublons_appels_offres`, `doublons_documents` et `payloads_bruts_vides` valent zéro.
Vérifier aussi `traitement_documents` : `a_traiter` et `echecs` doivent être explicitement signalés. `sans_texte` indique un PDF probablement scanné ; `non_supporte` indique actuellement un ancien format DOC.

5. Pour relire les AO ouverts déjà stockés :

```powershell
.\.venv\Scripts\python.exe -m onetech_ao.cli list-open --limit 20
```

## Réponse attendue

Retourner :

- statut de la collecte ;
- identifiant de collecte ;
- nombre reçu, inséré et mis à jour ;
- nombre de documents insérés et mis à jour ;
- nombre de documents extraits, sans texte, non supportés et en échec ;
- erreurs ou avertissements concis ;
- shortlist OneTech issue de la sortie JSON ;
- limite explicite si un cahier des charges exige TUNEPS.

Ne jamais transformer la shortlist lexicale en décision Go/No-Go définitive. Pour cela, lancer `analyse-ao` sur les documents disponibles.

## Sécurité et limites

- Utiliser uniquement l'API et les pages publiques HAICOP gérées par le package.
- Ne jamais désactiver la vérification TLS.
- Ne jamais contourner TUNEPS, une session ou une authentification.
- Ne jamais inventer un document non public.
- Ne jamais afficher les secrets PostgreSQL.
- Ne télécharger que les URLs HTTPS publiques HAICOP autorisées par le package.
- Ne jamais présenter `sans_texte` ou `non_supporte` comme un document analysé.
- Si Docker/PostgreSQL est arrêté, démarrer uniquement les services du workspace avec `docker compose up -d`, puis réappliquer les migrations idempotentes avec `.\scripts\apply-database.ps1`.
- Si l'environnement virtuel manque, suivre la section installation de `README.md`.
- En cas d'échec, rapporter l'erreur concise de la CLI et vérifier la dernière ligne de `collectes_haicop`; ne pas appeler directement un endpoint privé en contournement.
