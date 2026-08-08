"""Orchestration HAICOP -> PostgreSQL et shortlist locale."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .config import Settings
from .database import Database
from .haicop import HaicopClient, TenderRecord


POSITIVE_KEYWORDS = (
    "informatique",
    "logiciel",
    "software",
    "système d'information",
    "systeme d'information",
    "réseau",
    "reseau",
    "télécommunication",
    "telecommunication",
    "data",
    "données",
    "donnees",
    "digital",
    "numérique",
    "numerique",
    "serveur",
    "cybersécurité",
    "cybersecurite",
    "vidéosurveillance",
    "videosurveillance",
    "biométrique",
    "biometrique",
    "plateforme",
    "cloud",
    "erp",
    "ged",
    "intelligence artificielle",
)

NEGATIVE_KEYWORDS = (
    "construction",
    "bâtiment",
    "batiment",
    "route",
    "alimentaire",
    "nettoyage",
    "gardiennage",
    "mobilier",
)


@dataclass(slots=True)
class CollectionResult:
    statut: str
    collecte_id: int | None
    nb_recus: int
    nb_inseres: int
    nb_mis_a_jour: int
    nb_documents_inseres: int
    nb_documents_mis_a_jour: int
    erreurs: list[str] = field(default_factory=list)
    shortlist: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def shortlist(tenders: list[TenderRecord], limit: int = 5) -> list[dict[str, Any]]:
    ranked: list[tuple[int, TenderRecord, list[str]]] = []
    for tender in tenders:
        haystack = f"{tender.organization or ''} {tender.title or ''}".casefold()
        positive = sorted({word for word in POSITIVE_KEYWORDS if word in haystack})
        negative = sorted({word for word in NEGATIVE_KEYWORDS if word in haystack})
        score = len(positive) * 2 - len(negative) * 2
        if score > 0:
            ranked.append((score, tender, positive))

    ranked.sort(
        key=lambda item: (
            item[0],
            item[1].publication_date.isoformat() if item[1].publication_date else "",
        ),
        reverse=True,
    )

    output: list[dict[str, Any]] = []
    for score, tender, matches in ranked[:limit]:
        output.append(
            {
                "tender_id": tender.tender_id,
                "organisme": tender.organization,
                "objet": tender.title,
                "publication": tender.publication_date,
                "date_limite": tender.deadline,
                "pertinence": "Priorité à analyser",
                "mots_cles": matches,
                "documents_publics": len(tender.documents),
                "url": tender.detail_url,
            }
        )
    return output


class Collector:
    def __init__(
        self,
        settings: Settings,
        database: Database | None = None,
        client: HaicopClient | None = None,
    ) -> None:
        self.settings = settings
        self.database = database or Database(settings)
        self.client = client or HaicopClient(
            base_url=settings.haicop_base_url,
            timeout=settings.http_timeout,
            user_agent=settings.user_agent,
        )

    def collect(
        self,
        limit: int = 50,
        with_details: bool = False,
        since_days: int | None = None,
        dry_run: bool = False,
    ) -> CollectionResult:
        self.database.check_connection()
        parameters = {
            "limit": limit,
            "with_details": with_details,
            "since_days": since_days,
            "dry_run": dry_run,
        }
        collection_id = None if dry_run else self.database.start_collection(parameters)

        try:
            fetched = self.client.fetch_tenders(limit=limit, since_days=since_days)
            errors = list(fetched.errors)

            if with_details:
                for tender in fetched.tenders:
                    try:
                        detail_fields, documents = self.client.fetch_detail(tender)
                        tender.detail_fields = detail_fields
                        tender.documents = documents
                    except Exception as exc:  # une page détail ne doit pas annuler le lot
                        errors.append(self.settings.redact(exc, max_length=240))

            result = CollectionResult(
                statut="simulation" if dry_run else "terminee",
                collecte_id=collection_id,
                nb_recus=len(fetched.tenders),
                nb_inseres=0,
                nb_mis_a_jour=0,
                nb_documents_inseres=0,
                nb_documents_mis_a_jour=0,
                erreurs=errors,
                shortlist=shortlist(fetched.tenders),
            )

            if dry_run:
                return result

            assert collection_id is not None
            with self.database.connect() as connection:
                for tender in fetched.tenders:
                    if self.database.upsert_tender(connection, tender, collection_id):
                        result.nb_inseres += 1
                    else:
                        result.nb_mis_a_jour += 1
                    for document in tender.documents:
                        if self.database.upsert_document(connection, document):
                            result.nb_documents_inseres += 1
                        else:
                            result.nb_documents_mis_a_jour += 1

            warning = None
            if errors:
                warning = self.settings.redact(" | ".join(errors), max_length=500)
            self.database.finish_collection(
                collection_id=collection_id,
                received=result.nb_recus,
                inserted=result.nb_inseres,
                updated=result.nb_mis_a_jour,
                warning=warning,
            )
            return result
        except Exception as exc:
            if collection_id is not None:
                error = self.settings.redact(exc)
                try:
                    self.database.fail_collection(collection_id, error)
                except Exception:
                    pass
            raise
        finally:
            self.client.close()
