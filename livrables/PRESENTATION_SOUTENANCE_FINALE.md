# Présentation de soutenance — version finale

Les versions de référence sont :

- [PRESENTATION_SOUTENANCE_KHAYEM_BEN_GHORBEL.pptx](./PRESENTATION_SOUTENANCE_KHAYEM_BEN_GHORBEL.pptx) — présentation PowerPoint éditable avec notes orateur sur chaque diapositive ;
- [PRESENTATION_SOUTENANCE_KHAYEM_BEN_GHORBEL.pdf](./PRESENTATION_SOUTENANCE_KHAYEM_BEN_GHORBEL.pdf) — version PDF de secours ;
- [version Canva éditable](https://www.canva.com/d/a00BY55ehhel_wn) — import de la présentation finale.

## Fil narratif des 16 diapositives

1. **Titre** — mission, étudiant, entreprise et période.
2. **Contexte et mission** — problème métier, objectif et contraintes de confiance.
3. **Problématique** — transformer des sources hétérogènes en décision traçable.
4. **Chronologie** — progression par couches de risque.
5. **Cas d’utilisation** — décideur AO, automate n8n et source HAICOP.
6. **Architecture** — collecte, PostgreSQL, documents, agent et canaux.
7. **Traçabilité** — faits, documents, contexte, analyse et diffusion.
8. **Pipeline documentaire** — téléchargement sûr, signature, extraction native et OCR.
9. **Go / No-Go** — quatre critères, seuils et garde-fous de cohérence.
10. **Séquence quotidienne** — collecte, sélection, analyse et diffusion idempotente.
11. **Séquence Telegram** — filtrage, reprise et absence de persistance du texte utilisateur.
12. **MCP** — cinq outils bornés et séparation agent / domaine.
13. **Résultats** — corpus, couverture documentaire et tests.
14. **Sécurité et qualité** — contrôles aux différentes frontières.
15. **Démonstration** — deux décisions `NO_GO` et rejeu sans doublon.
16. **Conclusion** — résultat, compétences et message final.

## Messages à défendre

- Le système produit une recommandation explicable ; il ne remplace pas la décision humaine.
- L’empreinte du contexte relie les faits sources, les pièces et l’analyse.
- L’idempotence permet de relancer les workflows sans multiplier leurs effets.
- Les entrées externes sont bornées : URL, signatures de fichiers, archives, délais et secrets.
- L’état présenté correspond à un MVP opérationnel, validé et démontrable.

Les notes orateur intégrées au fichier PowerPoint reprennent le discours conseillé et les sources techniques de chaque diapositive.
