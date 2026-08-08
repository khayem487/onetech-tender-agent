"""Interface en ligne de commande du collecteur OneTech AO."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta
from typing import Any, Sequence

from .collector import Collector
from .config import ConfigurationError, Settings
from .database import Database


def configure_stdio() -> None:
    """Force une sortie Unicode stable sous Windows/PowerShell 5.1."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="backslashreplace")


def _json_default(value: object) -> str:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, timedelta):
        return str(value)
    return str(value)


def emit(payload: Any, stream: Any = sys.stdout) -> None:
    json.dump(payload, stream, ensure_ascii=False, indent=2, default=_json_default)
    stream.write("\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="onetech-ao",
        description="Collecteur public HAICOP vers PostgreSQL",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect_parser = subparsers.add_parser("collect", help="collecter et stocker les AO")
    collect_parser.add_argument("--limit", type=int, default=50)
    collect_parser.add_argument("--with-details", action="store_true")
    collect_parser.add_argument("--dry-run", action="store_true")
    collect_parser.add_argument("--since-days", type=int)

    status_parser = subparsers.add_parser("status", help="vérifier PostgreSQL et le journal")
    status_parser.add_argument("--history-limit", type=int, default=5)

    list_parser = subparsers.add_parser("list-open", help="lister les AO encore ouverts")
    list_parser.add_argument("--limit", type=int, default=20)

    return parser


def _validate_positive(value: int, label: str) -> None:
    if value < 1:
        raise ValueError(f"{label} doit être supérieur à zéro")


def run(args: argparse.Namespace, settings: Settings) -> dict[str, Any]:
    database = Database(settings)
    if args.command == "collect":
        _validate_positive(args.limit, "--limit")
        if args.since_days is not None and args.since_days < 0:
            raise ValueError("--since-days ne peut pas être négatif")
        collector = Collector(settings=settings, database=database)
        return collector.collect(
            limit=args.limit,
            with_details=args.with_details,
            since_days=args.since_days,
            dry_run=args.dry_run,
        ).to_dict()

    if args.command == "status":
        _validate_positive(args.history_limit, "--history-limit")
        return {
            "statut": "ok",
            "postgresql": database.check_connection(),
            "compteurs": database.counts(),
            "integrite": database.integrity_report(),
            "dernieres_collectes": database.recent_collections(args.history_limit),
        }

    if args.command == "list-open":
        _validate_positive(args.limit, "--limit")
        database.check_connection()
        rows = database.list_open(args.limit)
        return {"statut": "ok", "nb_resultats": len(rows), "appels_offres": rows}

    raise ValueError("commande inconnue")


def main(argv: Sequence[str] | None = None) -> int:
    configure_stdio()
    parser = build_parser()
    args = parser.parse_args(argv)
    settings: Settings | None = None
    try:
        settings = Settings.load()
        emit(run(args, settings))
        return 0
    except (ConfigurationError, ValueError) as exc:
        emit({"statut": "echec", "erreur": str(exc)}, stream=sys.stderr)
        return 2
    except Exception as exc:
        message = settings.redact(exc) if settings is not None else type(exc).__name__
        emit({"statut": "echec", "erreur": message}, stream=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
