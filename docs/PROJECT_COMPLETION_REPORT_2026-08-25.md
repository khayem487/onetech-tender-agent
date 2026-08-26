# OneTech Tender Agent — rapport de finalisation

Date de validation technique : 25 août 2026
Dernière mise à jour documentaire : 26 août 2026

## Résultat livré

OneTech Tender Agent automatise la veille sur les appels d’offres publics depuis
la collecte HAICOP jusqu’à la diffusion d’un digest actionnable. La chaîne
réunit Python, PostgreSQL, OpenClaw, n8n, OCR, Gmail, Telegram et MCP dans une
architecture traçable et reproductible.

## Capacités opérationnelles

- collecte publique HAICOP avec pagination, normalisation et pages détaillées ;
- PostgreSQL 16 avec journal de collecte, UPSERT et contraintes anti-doublon ;
- téléchargement borné, stockage local et empreintes SHA-256 ;
- extraction PDF/DOCX, OCR des scans et conversion contrôlée des anciens DOC ;
- contextes d’analyse persistés et fiches Go/No-Go reliées à leurs sources ;
- orchestration n8n du digest les jours ouvrés à 08:00, heure de Paris ;
- diffusion Mailpit, Gmail et Telegram avec registre anti-doublon ;
- réponses du bot OneTech aux mentions dans le groupe Telegram dédié ;
- serveur MCP onetech-tender avec cinq outils bornés ;
- Ollama/Phi-4 Mini évalué comme second avis local ;
- sauvegarde complète et restauration vérifiée dans une base isolée ;
- démarrage et contrôle manuels avec scripts PowerShell dédiés.

## Snapshot validé

| Indicateur | Résultat |
|---|---:|
| Appels d’offres centralisés | 100 |
| Documents présents, hashés et extraits | 152 / 152 |
| Doublons détectés | 0 |
| Tests Python réussis | 67 / 67 |
| Scripts SQL validés | 6 / 6 |
| Outils MCP opérationnels | 5 / 5 |

Les 152 documents comprennent 41 PDF, 74 DOCX, 35 anciens DOC et 2 images.
L’extraction choisit automatiquement la méthode native, la conversion
LibreOffice ou l’OCR Tesseract en français, arabe et anglais.

## Exploitation

Le projet est lancé à la demande :

~~~powershell
.\scripts\start-onetech-stack.ps1 -StartGateway -StartOllama
.\scripts\healthcheck-onetech-stack.ps1 -RequireGateway -RequireOllama -RequireWorkflows -RequireMcp
~~~

Aucune tâche Windows récurrente n’est requise. Les secrets restent dans
le fichier .env ou dans les configurations OpenClaw locales et ne sont pas
versionnés.

## Livrables

- rapport de stage en Markdown, Word, HTML et PDF ;
- présentation de soutenance en Markdown, PowerPoint et PDF ;
- 16 diapositives avec notes orateur pour un exposé de 15 à 20 minutes ;
- cinq visuels éditables en HTML et exportés en PNG ;
- annexe d’évaluation CY Tech à faire compléter et signer ;
- README et documentation d’exploitation.

Le contrôle final détaillé est consigné dans
[DELIVERABLES_FINAL_QA_2026-08-26.md](DELIVERABLES_FINAL_QA_2026-08-26.md).
