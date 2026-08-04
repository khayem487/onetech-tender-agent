# Docker/PostgreSQL setup

## What this runs

`compose.yaml` describes the `postgres` service.

- Docker downloads the PostgreSQL 16 image.
- The container runs the PostgreSQL server.
- Windows applications connect through `localhost:5432`.
- PostgreSQL stores its files in the named Docker volume
  `onetech_postgres_data`.
- `.env` supplies the initial database name, user, password, and host port.

The volume is separate from the container. Recreating the container therefore
does not erase the database.

## Commands

Run these from the company workspace:

```powershell
cd C:\Users\khaye\.openclaw-company\workspace
docker compose up -d
docker compose ps
```

`up -d` creates or starts the service in the background. `ps` shows its state
and health check.

Connect with PostgreSQL's client inside the container:

```powershell
docker compose exec postgres psql -U onetech -d onetech_ao
```

Useful read-only checks inside `psql`:

```sql
SELECT current_database(), current_user;
\dt
```

Exit `psql` with `\q`.

Stop the service while preserving all data:

```powershell
docker compose stop
```

Start it again:

```powershell
docker compose start
```

Remove the container and network while preserving the named volume:

```powershell
docker compose down
```

Do not run `docker compose down -v` unless the database is intentionally being
reset: `-v` deletes the persistent database volume.
