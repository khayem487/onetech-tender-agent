# Exécution quotidienne OneTech AO

Date de suivi : `{{RUN_DATE}}`
Fuseau horaire : `{{TIMEZONE}}`
Maximum d'analyses : `{{MAX_CANDIDATES}}`

Exécute le workflow quotidien PostgreSQL de manière autonome, séquentielle et
idempotente. Utilise uniquement le workspace entreprise et ses skills actives.
N'affiche jamais de mot de passe, token, contenu de `.env` ou autre secret.

## 1. Démarrer et planifier le run

Depuis la racine du workspace entreprise, exécute exactement :

```powershell
docker compose exec -T ao-worker python -m onetech_ao.cli daily-start --trigger n8n --run-key daily:{{RUN_DATE}} --max-candidates {{MAX_CANDIDATES}}
```

Lis la réponse JSON. Conserve `execution.id` comme identifiant du run. La liste
bornée des AO à traiter se trouve dans `candidats[].tender_id`.

Si `daily-start` signale qu'un run du jour est déjà terminé ou qu'aucun candidat
n'est disponible, respecte cette décision idempotente et passe directement à
`daily-finish`. Ne sélectionne jamais toi-même des Tender-ID supplémentaires.

## 2. Analyser chaque candidat

Pour chaque `tender_id`, dans l'ordre retourné et sans parallélisme :

1. utilise obligatoirement la skill `analyse-ao` ;
2. lis le contexte et tous les textes documentaires disponibles depuis PostgreSQL ;
3. produis la fiche à neuf sections avec les quatre scores et une décision ;
4. enregistre et vérifie l'analyse dans PostgreSQL selon la procédure de la skill ;
5. si un document est scanné, ancien ou inaccessible, signale précisément la
   limite sans inventer son contenu ;
6. si une AO échoue, note l'erreur concise, continue avec la suivante et ne
   relance pas indéfiniment la même étape.

Le profil OneTech présent dans le workspace est la source de vérité validée. Ne
fabrique aucune capacité, certification, référence ou information financière.

## 3. Finaliser, produire et diffuser le digest

Après toutes les analyses, exécute en remplaçant `<ID>` par `execution.id` :

```powershell
.\.venv\Scripts\python.exe -m onetech_ao.cli daily-finish --run-id <ID> {{DELIVERY_ARGS}}
```

`daily-finish` doit être exécuté même si une analyse ou un canal a échoué. Il
doit conserver le digest local et le journal d'audit. Les canaux sont définis
par l'administrateur local dans `AUTOMATION_DELIVERY_ARGS`; Mailpit est le
mode de validation par défaut. Email et Telegram restent des tentatives
indépendantes : l'échec ou l'absence de configuration d'un canal ne doit pas
empêcher l'autre canal ni empêcher la clôture du run.

## 4. Réponse finale obligatoire

Réponds avec un résumé court et factuel indiquant :

- l'identifiant et le statut final du run ;
- les nombres de candidats, analyses réussies, ignorées et échouées ;
- le chemin du digest local ;
- pour email, Telegram et Mailpit : `envoyé`, `ignoré/non configuré` ou `échec` ;
- toute limite documentaire ou erreur restante.

Ne demande pas de confirmation humaine pendant ce run. Ne contourne jamais
TUNEPS, une authentification, un CAPTCHA ou une restriction d'accès.
