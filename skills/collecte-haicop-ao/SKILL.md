---
name: "collecte-haicop-ao"
description: "Collecte rapide AO via API publique HAICOP"
---

# Skill : Collecte HAICOP AO

## Quand utiliser

Utiliser cette skill dès que l'utilisateur demande :

- de chercher des appels d'offres publics en Tunisie ;
- de lister ou scorer des AO HAICOP / marchespublics.gov.tn ;
- de trouver les AO IT pertinents pour One Tech ;
- d'analyser un lien `https://www.marchespublics.gov.tn/fr/appels-doffres/...` ;
- de faire une veille des AO publiés récemment.

Après la collecte, utiliser `analyse-ao` pour produire la fiche d'analyse complète.

## Source publique principale

- Base : `https://www.marchespublics.gov.tn`
- Liste AO : `https://www.marchespublics.gov.tn/fr/appels-doffres`
- Détail AO : `https://www.marchespublics.gov.tn/fr/appels-doffres/Tender-XXXXX`
- Documents publics : souvent sous `https://www.marchespublics.gov.tn/storage/tender/...`

## Workflow rapide

### 1. Appeler la liste JSON DataTables

Le tableau public des appels d'offres est alimenté par un endpoint JSON de type DataTables sur la même URL `/fr/appels-doffres`. Ne pas explorer manuellement la page si l'objectif est de collecter vite.

Requête type :

```text
GET https://www.marchespublics.gov.tn/fr/appels-doffres?draw=1&start=0&length=50&order[0][column]=0&order[0][dir]=desc&search[value]=&search[regex]=false&columns[0][data]=id&columns[0][name]=&columns[0][searchable]=true&columns[0][orderable]=true&columns[0][search][value]=&columns[0][search][regex]=false&columns[1][data]=organization.name_fr&columns[1][name]=organization.name_fr&columns[1][searchable]=true&columns[1][orderable]=true&columns[1][search][value]=&columns[1][search][regex]=false&columns[2][data]=title_fr&columns[2][name]=title_fr&columns[2][searchable]=true&columns[2][orderable]=true&columns[2][search][value]=&columns[2][search][regex]=false&columns[3][data]=tenderPeriod_endDate&columns[3][name]=&columns[3][searchable]=true&columns[3][orderable]=true&columns[3][search][value]=&columns[3][search][regex]=false&columns[4][data]=publication_date&columns[4][name]=&columns[4][searchable]=true&columns[4][orderable]=true&columns[4][search][value]=&columns[4][search][regex]=false&columns[5][data]=reservedSME&columns[5][name]=&columns[5][searchable]=true&columns[5][orderable]=true&columns[5][search][value]=&columns[5][search][regex]=false
```

Headers utiles :

```text
User-Agent: Mozilla/5.0 TenderAgent/1.0
Referer: https://www.marchespublics.gov.tn/fr/appels-doffres
X-Requested-With: XMLHttpRequest
Accept: application/json, text/javascript, */*; q=0.01
```

### 2. Extraire les champs utiles

Depuis `data[]`, récupérer au minimum :

- `id` : identifiant AO, ex. `Tender-102830`
- `organization.name_fr` : acheteur / organisme
- `title_fr` : titre / objet
- `publication_date` : date de publication
- `tenderPeriod_endDate` : date limite
- `planID` : identifiant plan si présent
- `plan.reservedSME` ou `reservedSME` : réservé PME si présent

Construire ensuite l'URL détail :

```text
https://www.marchespublics.gov.tn/fr/appels-doffres/{id}
```

### 3. Enrichir avec la page détail

Pour chaque AO pertinent :

1. Télécharger la page détail publique.
2. Extraire les champs visibles, notamment les blocs de type `<strong>Libellé:</strong> valeur`.
3. Chercher les liens documents publics contenant `/storage/tender/`.
4. Conserver l'URL, le libellé du document et l'AO associé.

Regex utile pour les liens documents :

```regex
<a[^>]+href="(?P<url>https://www\.marchespublics\.gov\.tn/storage/tender/[^"]+)"[^>]*>(?P<label>.*?)</a>
```

### 4. Télécharger et préparer l'analyse

Télécharger seulement les documents utiles : avis, cahier des charges, annexes administratives, annexes techniques. Extraire le texte du PDF/DOCX quand possible, puis lancer `analyse-ao`.

Si aucun cahier des charges n'est public, produire une analyse partielle à partir de l'avis et signaler clairement que le cahier des charges doit être récupéré depuis TUNEPS.

## Limites connues

- Certains cahiers des charges sont uniquement disponibles sur TUNEPS avec session authentifiée.
- Des endpoints TUNEPS peuvent répondre `401 Unauthorized` sans session autorisée.
- Ne jamais contourner une authentification.
- Ne jamais inventer le contenu d'un cahier des charges non récupéré.

## Shortlist One Tech

Quand l'utilisateur demande les AO pertinents pour One Tech, scorer d'abord grossièrement sur titre + organisme.

Mots-clés positifs :

- informatique
- logiciel / software
- système / SI
- réseau / télécommunication
- data / données
- digital / numérique
- serveur
- cybersécurité
- maintenance informatique
- vidéosurveillance
- biométrique / pointage
- plateforme
- ERP / GED
- cloud
- IA

Mots-clés négatifs :

- travaux / construction / bâtiment / route
- alimentaire
- médical pur
- fournitures non IT
- nettoyage
- gardiennage
- mobilier

## Sortie attendue pour une recherche

Produire une shortlist concise :

```markdown
# Shortlist AO HAICOP - [date]

| AO | Organisme | Objet | Publication | Deadline | Pertinence | Documents publics | URL |
|---|---|---|---|---|---|---|---|
| Tender-XXXXX | ... | ... | ... | ... | GO / À discuter / Non prioritaire | Oui/Non | ... |

## Recommandation
1. Priorité 1 : ...
2. Priorité 2 : ...

## Limites
- Cahiers des charges TUNEPS non récupérés si authentification requise.
```

## Sortie attendue pour une analyse

Après collecte d'un AO précis :

1. Donner les sources récupérées.
2. Indiquer si l'analyse est complète ou partielle.
3. Appeler le workflow `analyse-ao` sur les documents/textes récupérés.
4. Sauvegarder la fiche en markdown si l'environnement le permet.
