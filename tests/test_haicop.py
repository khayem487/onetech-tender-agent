from datetime import datetime

import pytest

from onetech_ao.haicop import (
    NormalizationError,
    normalize_bool,
    normalize_tender,
    normalize_tender_id,
    normalize_text,
    parse_datetime,
    parse_detail_page,
)


def test_normalize_text_preserves_unicode_and_collapses_whitespace() -> None:
    assert normalize_text("  Équipement\n  شبكات &amp; sécurité ") == "Équipement شبكات & sécurité"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [(103300, "Tender-103300"), ("Tender-00103300", "Tender-103300")],
)
def test_normalize_tender_id(raw: object, expected: str) -> None:
    assert normalize_tender_id(raw) == expected


def test_normalize_tender_id_rejects_untrusted_shape() -> None:
    with pytest.raises(NormalizationError):
        normalize_tender_id("AO-103300")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [(True, True), ("oui", True), (0, False), ("Non", False), (None, None), ("?", None)],
)
def test_normalize_bool_is_three_state(raw: object, expected: bool | None) -> None:
    assert normalize_bool(raw) is expected


def test_parse_haicop_datetime_assigns_tunis_timezone() -> None:
    parsed = parse_datetime("2026-08-08 14:25:10")
    assert isinstance(parsed, datetime)
    assert parsed.isoformat() == "2026-08-08T14:25:10+01:00"


def test_normalize_realistic_haicop_row_preserves_raw_payload() -> None:
    row = {
        "id": 103300,
        "planID": "PLAN-88",
        "title_fr": "Acquisition de matériel informatique",
        "organization": {"id": 7, "name_fr": "Organisme public"},
        "plan": {"planID": "PLAN-88", "reservedSME": True},
        "publication_date": "2026-08-08 10:15:00",
        "tenderPeriod_endDate": "2026-09-01 12:00:00",
    }

    tender = normalize_tender(row, "https://www.marchespublics.gov.tn")

    assert tender.tender_id == "Tender-103300"
    assert tender.plan_id == "PLAN-88"
    assert tender.organization == "Organisme public"
    assert tender.reserved_sme is True
    assert tender.raw_payload == row
    assert tender.detail_url.endswith("/fr/appels-doffres/Tender-103300")


def test_parse_detail_page_extracts_only_unique_public_documents() -> None:
    source = """
    <html><body>
      <span><strong>Inscription</strong> navigation à ignorer</span>
      <p class="medium mb-0"><strong>Mode de passation :</strong> Appel d'offres ouvert</p>
      <p class="medium mb-0"><strong>Heure :</strong> 10:00</p>
      <p class="medium mb-0"><strong>Heure :</strong> 10:30</p>
      <a href="/storage/tender/2026/08/08/a.pdf"><span>Avis d'appel d'offres</span></a>
      <a href="https://www.marchespublics.gov.tn/storage/tender/2026/08/08/a.pdf#page=1">Doublon</a>
      <a href="http://www.marchespublics.gov.tn/storage/tender/insecure.pdf">HTTP refusé</a>
      <a href="https://tuneps.tn/storage/tender/private.pdf">Hôte refusé</a>
    </body></html>
    """

    details, documents = parse_detail_page(
        source,
        "https://www.marchespublics.gov.tn/fr/appels-doffres/Tender-103300",
        "Tender-103300",
    )

    assert details["Mode de passation"] == "Appel d'offres ouvert"
    assert "Inscription" not in details
    assert details["Heure"] == "10:00"
    assert details["Heure (2)"] == "10:30"
    assert len(documents) == 1
    assert documents[0].url == (
        "https://www.marchespublics.gov.tn/storage/tender/2026/08/08/a.pdf"
    )
    assert documents[0].document_type == "pdf"
