"""Interface en ligne de commande du collecteur OneTech AO."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Sequence

from .analysis import (
    AnalysisContextError,
    build_analysis_context,
    export_analysis_context,
    normalize_tender_id,
    record_analysis,
)
from .collector import Collector
from .config import ConfigurationError, Settings
from .database import Database
from .documents import DocumentProcessor


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
    collect_parser.add_argument("--process-documents", action="store_true")
    collect_parser.add_argument("--document-limit", type=int, default=50)

    documents_parser = subparsers.add_parser(
        "process-documents",
        help="télécharger et extraire les documents HAICOP en attente",
    )
    documents_parser.add_argument("--limit", type=int, default=50)
    documents_parser.add_argument("--retry-errors", action="store_true")
    documents_parser.add_argument("--reprocess-extracted", action="store_true")
    documents_parser.add_argument(
        "--tender-id",
        help="traiter uniquement les documents d'un Tender-ID précis",
    )

    status_parser = subparsers.add_parser("status", help="vérifier PostgreSQL et le journal")
    status_parser.add_argument("--history-limit", type=int, default=5)

    list_parser = subparsers.add_parser("list-open", help="lister les AO encore ouverts")
    list_parser.add_argument("--limit", type=int, default=20)

    context_parser = subparsers.add_parser(
        "analysis-context",
        help="exporter depuis PostgreSQL le contexte complet d'un AO pour analyse",
    )
    context_parser.add_argument("tender_id", help="Tender-123 ou URL HAICOP publique")
    context_parser.add_argument("--output", type=Path)
    context_parser.add_argument(
        "--stdout",
        action="store_true",
        help="émettre le contexte complet en JSON au lieu d'un manifeste court",
    )

    record_parser = subparsers.add_parser(
        "record-analysis",
        help="valider et enregistrer une fiche produite par analyse-ao",
    )
    record_parser.add_argument("tender_id")
    record_parser.add_argument("--fiche", type=Path, required=True)
    record_parser.add_argument(
        "--status",
        choices=("complete", "partielle"),
        required=True,
    )
    record_parser.add_argument("--score-adequation", type=int, required=True)
    record_parser.add_argument("--score-delai", type=int, required=True)
    record_parser.add_argument("--score-administratif", type=int, required=True)
    record_parser.add_argument("--score-risque", type=int, required=True)
    record_parser.add_argument(
        "--context-sha256",
        required=True,
        help="empreinte renvoyée par analysis-context; protège contre un contexte obsolète",
    )
    record_parser.add_argument(
        "--decision",
        choices=("GO", "A_DISCUTER", "NO_GO"),
        required=True,
    )
    record_parser.add_argument("--engine", default="openclaw")
    record_parser.add_argument("--model")

    show_parser = subparsers.add_parser(
        "show-analysis",
        help="afficher les métadonnées de la dernière analyse d'un AO",
    )
    show_parser.add_argument("tender_id")

    digest_parser = subparsers.add_parser(
        "digest",
        help="lister les dernières analyses classées pour OneTech",
    )
    digest_parser.add_argument("--limit", type=int, default=10)
    digest_parser.add_argument("--include-expired", action="store_true")

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
        collection = collector.collect(
            limit=args.limit,
            with_details=args.with_details,
            since_days=args.since_days,
            dry_run=args.dry_run,
        ).to_dict()
        if args.process_documents:
            if args.dry_run:
                raise ValueError("--process-documents est incompatible avec --dry-run")
            _validate_positive(args.document_limit, "--document-limit")
            collection["traitement_documents"] = DocumentProcessor(
                settings=settings,
                database=database,
            ).process(limit=args.document_limit).to_dict()
        return collection

    if args.command == "process-documents":
        _validate_positive(args.limit, "--limit")
        tender_id = normalize_tender_id(args.tender_id) if args.tender_id else None
        return DocumentProcessor(settings=settings, database=database).process(
            limit=args.limit,
            retry_errors=args.retry_errors,
            reprocess_extracted=args.reprocess_extracted,
            tender_id=tender_id,
        ).to_dict()

    if args.command == "status":
        _validate_positive(args.history_limit, "--history-limit")
        return {
            "statut": "ok",
            "postgresql": database.check_connection(),
            "compteurs": database.counts(),
            "integrite": database.integrity_report(),
            "traitement_documents": database.document_processing_counts(),
            "dernieres_collectes": database.recent_collections(args.history_limit),
        }

    if args.command == "list-open":
        _validate_positive(args.limit, "--limit")
        database.check_connection()
        rows = database.list_open(args.limit)
        return {"statut": "ok", "nb_resultats": len(rows), "appels_offres": rows}

    if args.command == "analysis-context":
        database.check_connection()
        if args.stdout:
            return build_analysis_context(settings, database, args.tender_id)
        result, _ = export_analysis_context(
            settings,
            database,
            args.tender_id,
            output=args.output,
        )
        return result.to_dict()

    if args.command == "record-analysis":
        database.check_connection()
        return record_analysis(
            settings,
            database,
            reference=args.tender_id,
            fiche=args.fiche,
            status=args.status,
            adequation=args.score_adequation,
            deadline=args.score_delai,
            administrative=args.score_administratif,
            risk=args.score_risque,
            decision=args.decision,
            context_sha256=args.context_sha256,
            engine=args.engine,
            model=args.model,
        )

    if args.command == "show-analysis":
        database.check_connection()
        tender_id = normalize_tender_id(args.tender_id)
        analysis = database.latest_analysis(tender_id)
        if analysis is None:
            raise AnalysisContextError(f"Aucune analyse enregistrée pour {tender_id}")
        return {"statut": "ok", "analyse": analysis}

    if args.command == "digest":
        _validate_positive(args.limit, "--limit")
        database.check_connection()
        analyses = database.analysis_digest(args.limit, args.include_expired)
        return {
            "statut": "ok",
            "nb_resultats": len(analyses),
            "analyses": analyses,
            "avertissement": (
                None
                if analyses
                else "Aucune fiche enregistrée: lancer analyse-ao sur les AO retenus."
            ),
        }

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
    except (AnalysisContextError, ConfigurationError, ValueError) as exc:
        emit({"statut": "echec", "erreur": str(exc)}, stream=sys.stderr)
        return 2
    except Exception as exc:
        message = settings.redact(exc) if settings is not None else type(exc).__name__
        emit({"statut": "echec", "erreur": message}, stream=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
