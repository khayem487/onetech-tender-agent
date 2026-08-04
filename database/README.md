# PostgreSQL schema

The database layer separates official HAICOP facts from future AI-generated
analysis.

## Objects

- `collectes_haicop`: one audit row per collector execution.
- `appels_offres`: one row per HAICOP tender, keyed by `tender_id`.
- `documents_ao`: public documents, unique by tender and URL.
- `v_appels_offres_ouverts`: tenders that are not expired or have no known
  deadline.

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

## New Docker volumes

`database/init` is mounted into PostgreSQL's standard initialization directory.
Docker executes these files automatically only when it creates a new empty
database volume. Existing volumes must use `apply-database.ps1`.
