# Project history

This timeline was reconstructed on 2026-08-04 from preserved local files,
session notes, and verified project artifacts. Git commits created during the
reconstruction are import checkpoints; the dates below record when the work
itself happened.

## 2026-06-26 - Project direction

- The official internship subject was confirmed: "Developpement d'un systeme
  IA agentique pour la gestion des appels d'offres publics".
- The learning objective included understanding agentic AI, the distinction
  between an agent and its model, and OpenClaw's operation.
- Tunisian public procurement data from `marchespublics.gov.tn` was selected as
  the initial public source.

## 2026-07-07 - First HAICOP proof of concept

- A HAICOP collection workflow was documented.
- Public tender data and documents were collected without bypassing
  authentication boundaries.
- Three tender analysis records and their source material were preserved.
- An initial Python/SQLite experiment also existed, but it is superseded and
  remains outside the active project tree.

## 2026-07-08 - Supervisor feedback

- The first PoC received positive feedback.
- Follow-up exploration areas included PostgreSQL, daily tender delivery,
  Telegram/Discord, n8n, Odoo, MCP, and a small Microsoft Phi benchmark.
- These were separate exploration areas, not completed deliverables.

## 2026-07-20 - End-to-end slice selected

- The next implementation slice was chosen as:
  `HAICOP collector -> PostgreSQL -> local digest preview`.
- Idempotent upserts and a two-run duplicate-prevention test were identified as
  acceptance checks.

## 2026-08-04 - Local database infrastructure

- PostgreSQL 16 was configured with Docker Compose and persistent storage.
- pgAdmin was added as a browser-based administration interface.
- Database connectivity was verified for `onetech_ao` using the `onetech`
  database role.

## Database schema milestone

- Added versioned SQL initialization under `database/init`.
- Separated collection runs, official tender facts, and public documents.
- Added duplicate-prevention constraints, indexes, update timestamps, and an
  open-tenders view.
- Added a transactional smoke test that proves tender and document upserts do
  not create duplicates.

## Next milestone

Connect the HAICOP collector to PostgreSQL and prove idempotent upserts across
two real collection runs.
