from datetime import datetime
from zoneinfo import ZoneInfo

from onetech_ao.collector import shortlist
from onetech_ao.haicop import TenderRecord


def _tender(tender_id: str, title: str) -> TenderRecord:
    return TenderRecord(
        tender_id=tender_id,
        plan_id=None,
        organization="Organisme public",
        title=title,
        publication_date=datetime(2026, 8, 8, tzinfo=ZoneInfo("Africa/Tunis")),
        deadline=None,
        reserved_sme=None,
        detail_url=f"https://www.marchespublics.gov.tn/fr/appels-doffres/{tender_id}",
        raw_payload={"id": tender_id},
    )


def test_shortlist_keeps_only_positive_onetech_candidates() -> None:
    candidates = shortlist(
        [
            _tender("Tender-1", "Acquisition de serveurs et matériel informatique"),
            _tender("Tender-2", "Travaux de construction d'une route"),
            _tender("Tender-3", "Sélection d'un cabinet juridique"),
        ]
    )

    assert [item["tender_id"] for item in candidates] == ["Tender-1"]
    assert candidates[0]["pertinence"] == "Priorité à analyser"
