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

## Milestone selected on 2026-07-20

Connect the HAICOP collector to PostgreSQL and prove idempotent upserts across
two real collection runs.

## 2026-08-08 - HAICOP to PostgreSQL integration

- Added the maintainable `onetech_ao` Python package and JSON CLI.
- Added verified TLS, HTTP timeouts/retries, DataTables pagination, Unicode and
  date normalization, DOM parsing for public detail pages, and strict public
  document URL validation.
- Connected collection-run journaling, tender UPSERTs, document UPSERTs and
  raw JSONB payload preservation to the existing PostgreSQL schema.
- Added unit tests and a self-cleaning PostgreSQL integration test.
- Ran two real identical collections with details: 20 tenders and 30 public
  document references remained unique after the second run.
- Updated the OpenClaw `collecte-haicop-ao` workflow to call the new CLI.

## 2026-08-10 - Automated document processing

- Added a resumable document-processing CLI and PostgreSQL migration.
- Restricted downloads to public HTTPS HAICOP document URLs, with redirect,
  size and archive-safety checks.
- Added local storage, SHA-256 hashes, PDF/DOCX text extraction, processing
  statuses and concise failure recording.
- Processed all 30 discovered documents: 25 extracted, 2 scanned PDFs without
  a text layer, 3 legacy DOC files retained as unsupported, and 0 failures.
- Proved idempotence by rerunning the processor with 0 pending documents.

## Milestone planned after the 2026-08-10 validation

Calibrate the One Tech company profile with Makram, then add OCR, legacy DOC
conversion and daily notifications. Odoo, MCP and Phi remain later exploration
items.

## 2026-08-10 - PostgreSQL-backed OpenClaw analysis

- Added a fingerprinted `analysis-context` export joining official tender facts,
  detail fields, document statuses and every extracted text from PostgreSQL.
- Preserved PDF page boundaries during extraction and reprocessed all five
  text-readable PDFs without re-downloading them.
- Added `analyses_ao` and `v_dernieres_analyses_ao` so generated reasoning stays
  separate from official HAICOP data.
- Added strict, idempotent `record-analysis`, plus `show-analysis` and `digest`.
- Added a tracked One Tech profile v0 with explicit unknown fields rather than
  invented company facts.
- Expanded SQL and Python tests for context export, partial-document reporting,
  fiche validation, score/decision consistency and analysis persistence.
- Proved the complete path on `Tender-103283`: OpenClaw read both extracted
  documents, generated a nine-section fiche, saved analysis ID 23 and verified
  it through `show-analysis` and `digest`.
- Replayed the identical fiche and context: PostgreSQL reused analysis ID 23
  instead of creating a duplicate.
- Recollected HAICOP data and confirmed the semantic context fingerprint stayed
  unchanged when only operational collection timestamps changed.

## 2026-08-11 to 2026-08-17 - Daily automation and real email

- Added the authenticated `ao-worker` bridge between n8n and the company
  OpenClaw gateway.
- Scheduled the end-to-end digest for weekdays at 08:00 Europe/Paris.
- Added Mailpit as a local proof channel and Gmail delivery through OAuth.
- Added a per-channel and per-recipient delivery ledger so retries do not send
  duplicate messages.
- Extended Gmail delivery to a comma-separated recipient list.

## 2026-08-18 to 2026-08-25 - Project completion hardening

- Added Tesseract OCR for scanned PDF/image documents and bounded LibreOffice
  conversion for legacy DOC files. All 152 stored documents now have a local
  file, SHA-256 and extracted text.
- Added a Telegram digest/reply implementation with database idempotence. Its
  workflow remains disabled until a dedicated OneTech bot and group ID are
  configured; the personal bot token is explicitly rejected.
- Registered `phi4-mini:latest` through Ollama in the company OpenClaw. The
  benchmark classifies the test tenders correctly but remains slow and is used
  only as an experimental second opinion.
- Added the `onetech-tender` MCP server with exactly five bounded tools:
  collection, open-tender listing, tender retrieval, analysis-context reading
  and digest generation.
- Added complete, checksummed backups and explicit component restoration.
  Restored a real backup into an isolated temporary PostgreSQL database and
  verified all table counts before deleting the drill database.
- Added Windows logon startup, a five-minute watchdog, health checks and
  persistent operational logs without touching the personal OpenClaw gateway.
- Final validation: 100 tenders, 152 extracted documents, no tender/document
  duplicates, 67 Python tests and 6 SQL tests passing.
- Odoo was intentionally excluded from the final scope.
