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

## New Docker volumes

`database/init` is mounted into PostgreSQL's standard initialization directory.
Docker executes these files automatically only when it creates a new empty
database volume. Existing volumes must use `apply-database.ps1`.
