# Docker/PostgreSQL setup

## What this runs

`compose.yaml` describes five local services: `postgres`, `pgadmin`, `mailpit`,
`ao-worker` and `n8n`.

- Docker downloads the PostgreSQL 16 image.
- The container runs the PostgreSQL server.
- Windows applications connect through `localhost:5432`.
- PostgreSQL stores its files in the named Docker volume
  `onetech_postgres_data`.
- `.env` supplies the initial database name, user, password, and host port.
- pgAdmin provides a browser interface at `http://localhost:5050`.
- Mailpit captures test emails locally at `http://localhost:8025`; it does not
  deliver them to the Internet.
- `ao-worker` is an internal, authenticated bridge from n8n to the company
  OpenClaw gateway.
- n8n schedules the daily digest at `http://localhost:5678`.

The volumes are separate from their containers. Recreating a container therefore
does not erase the database, n8n workflow state, or Mailpit test inbox.

The `database/init` directory is mounted read-only into PostgreSQL's standard
initialization directory. It is applied automatically for a new empty volume.
For the existing database, apply migrations explicitly:

```powershell
.\scripts\apply-database.ps1
.\scripts\test-database.ps1
```

## Daily automation topology

```text
n8n -> ao-worker -> OpenClaw company gateway -> HAICOP/PostgreSQL/analysis
                                                 -> digest -> Mailpit by default
```

`ao-worker` can only call the narrow daily-digest endpoint and requires an
automation token. It reaches the separately started company gateway through
`host.docker.internal:18790`; Docker cannot start that gateway itself. Start it
before a manual or scheduled run:

```powershell
C:\Users\khaye\.openclaw-company\start-company-gateway.cmd
```

The named volumes are:

```text
onetech_postgres_data
onetech_pgadmin_data
onetech_n8n_data
onetech_mailpit_data
```

## n8n activation and safe test

The versioned workflow definition lives in:

```text
automation/n8n/workflows/daily-digest.json
```

Mounting this file does not import it into n8n. Run the helper once from the
workspace root; it imports only when missing, activates the existing workflow,
and restarts n8n so the scheduler is loaded:

```powershell
.\scripts\activate-daily-automation.ps1
```

The schedule is weekdays at 08:00 Europe/Paris. For a safe verification, open
`http://localhost:5678`, create the local n8n owner account if prompted, run
the Manual Trigger once, then inspect the email at `http://localhost:8025`.
The default delivery is Mailpit only. Gmail/Telegram remain opt-in through the
ignored `.env` file and must be tested independently.

## pgAdmin

Open `http://localhost:5050` and sign in with the pgAdmin email/password from
`.env`. These credentials protect the pgAdmin interface; they are separate
from the PostgreSQL credentials.

The server is already registered under `Servers > OneTech PostgreSQL` with:

```text
Name: OneTech PostgreSQL
Host: postgres
Port: 5432
Maintenance database: onetech_ao
Username: onetech
Password: the POSTGRES_PASSWORD value from .env
```

The host is `postgres`, not `localhost`, because pgAdmin reaches PostgreSQL
through the internal Compose network.

The shareable server definition is stored in `pgadmin/servers.json`. The
database password is stored separately in the ignored `pgadmin/pgpass` file
and copied into pgAdmin's persistent volume with permissions limited to the
pgAdmin process.

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

Check the database through the collector package:

```powershell
.\.venv\Scripts\python.exe -m onetech_ao.cli status
```

This command reads the Windows-side connection (`127.0.0.1` and the port from
`.env`) and never prints the PostgreSQL password.

Remove the container and network while preserving the named volume:

```powershell
docker compose down
```

Do not run `docker compose down -v` unless all local state is intentionally
reset: `-v` deletes the persistent PostgreSQL, pgAdmin, n8n, and Mailpit
volumes.
