# OneTech Tender Agent

Personal development repository for the internship project:

> Developpement d'un systeme IA agentique pour la gestion des appels d'offres publics

The target pipeline is a reproducible proof of concept that collects public
HAICOP tenders, stores them in PostgreSQL, analyses their relevance, and
produces a useful digest for OneTech.

## Current state

- HAICOP collection workflow documented as an OpenClaw skill.
- Three tender analysis records preserved as Markdown.
- PostgreSQL 16 and pgAdmin run locally through Docker Compose.
- The PostgreSQL business schema and collector integration are the next work.

## Planned pipeline

```text
HAICOP public source
        -> collector
        -> PostgreSQL
        -> analysis and scoring
        -> local digest
        -> later: scheduling and notifications
```

This repository is maintained by Khayem for personal progress tracking. See
[`HISTORY.md`](HISTORY.md) for the reconstructed work timeline.
