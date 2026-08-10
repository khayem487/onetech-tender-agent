# PostgreSQL schema

The database layer separates official HAICOP facts from future AI-generated
analysis.

## Objects

- `collectes_haicop`: one audit row per collector execution.
- `appels_offres`: one row per HAICOP tender, keyed by `tender_id`.
- `documents_ao`: public documents, unique by tender and URL, with local path,
  SHA-256, processing status and extracted text.
- `analyses_ao`: generated fiches and four-part scores, kept separate from
  official HAICOP facts and idempotent by source/fiche fingerprints.
- `v_appels_offres_ouverts`: tenders that are not expired or have no known
  deadline.
- `v_dernieres_analyses_ao`: latest saved analysis for each tender.

Raw source payloads are kept in JSONB columns so fields that are not modelled
yet remain available for audits and future migrations.

## Apply migrations

From PowerShell:

```powershell
cd C:\Users\khaye\.openclaw-company\workspace
.\scripts\apply-database.ps1
```

The script applies every `database/init/*.sql` file in filename order. The SQL
is idempotent, so running it again does not duplicate tables or indexes.

## Run smoke tests

```powershell
.\scripts\test-database.ps1
```

The test inserts and upserts the same tender and document twice, asserts that
only one row exists, then rolls the transaction back. It leaves no test tender
in the database.

## Python collector integration

The `onetech_ao` package reads the database connection from the ignored root
`.env` file. Check the connection and integrity without exposing credentials:

```powershell
.\.venv\Scripts\python.exe -m onetech_ao.cli status
```

Run the real collector twice with the same arguments to verify idempotence:

```powershell
.\.venv\Scripts\python.exe -m onetech_ao.cli collect --limit 20 --with-details
.\.venv\Scripts\python.exe -m onetech_ao.cli collect --limit 20 --with-details
```

On an unchanged HAICOP result set, the first run reports inserts and the
second reports updates. The row counts in `appels_offres` and `documents_ao`
must remain unchanged, and `status` must report no duplicates.

The Python integration test creates a uniquely named tender and document,
checks both UPSERT paths and their JSONB payloads, then deletes all test rows:

```powershell
.\.venv\Scripts\python.exe -m pytest -m integration
```

## Document processing

Migration `002_document_processing.sql` adds observable processing metadata:

- `statut_traitement`: `a_traiter`, `extrait`, `sans_texte`, `non_supporte` or
  `echec`;
- `mime_type` and `taille_octets`;
- `traite_le` and `erreur_traitement`;
- existing `chemin_local`, `empreinte_sha256` and `texte_extrait` fields.

Process pending public documents with:

```powershell
.\.venv\Scripts\python.exe -m onetech_ao.cli process-documents --limit 50
```

Only HTTPS files under the public HAICOP `/storage/tender/` path are accepted.
Files are size-limited, hashed, stored under ignored `data/documents/`, and
PDF/DOCX text is written to PostgreSQL. Re-running the command leaves completed
documents untouched.

PDF extraction preserves `--- PAGE N ---` markers for source traceability. To
re-extract already completed local files after a parser improvement:

```powershell
.\.venv\Scripts\python.exe -m onetech_ao.cli process-documents --limit 50 --reprocess-extracted
```

## Analysis bridge

Migration `003_analysis.sql` stores model-generated output outside the official
tender tables. The bridge exports a complete, fingerprinted context to an
ignored local JSON file:

```powershell
.\.venv\Scripts\python.exe -m onetech_ao.cli analysis-context Tender-103283
```

After `analyse-ao` writes the mandatory nine-section fiche, use
`record-analysis` to validate and store it. `show-analysis` reads the latest
record and `digest` ranks the latest non-expired analyses by decision and
score.

The manifest hash returned by `analysis-context` must be passed as
`--context-sha256`. This prevents a fiche from being saved against facts that
changed while the model was reading them. Operational collection timestamps,
database IDs and local paths are deliberately excluded from the semantic hash;
official fields, document content, profile, rubric and evaluation date remain
included.

Migration `004_analysis_audit.sql` stores the exact context snapshot, rubric
version and evaluation date. Re-recording a fiche for the same semantic context
updates the existing row instead of creating a duplicate.

## New Docker volumes

`database/init` is mounted into PostgreSQL's standard initialization directory.
Docker executes these files automatically only when it creates a new empty
database volume. Existing volumes must use `apply-database.ps1`.
