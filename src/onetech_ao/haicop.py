"""Client HTTP public HAICOP et fonctions de normalisation."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import urldefrag, urljoin, urlparse
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


TUNIS_TZ = ZoneInfo("Africa/Tunis")
TENDER_ID_RE = re.compile(r"^(?:Tender-)?(?P<number>\d+)$", re.IGNORECASE)
MICROSOFT_DATE_RE = re.compile(r"^/Date\((?P<milliseconds>\d+)(?:[+-]\d+)?\)/$")
ALLOWED_DOCUMENT_HOSTS = {"marchespublics.gov.tn", "www.marchespublics.gov.tn"}


class HaicopError(RuntimeError):
    """Erreur concise liée à une source publique HAICOP."""


class NormalizationError(ValueError):
    """Ligne HAICOP inutilisable sans inventer de donnée."""


@dataclass(slots=True)
class DocumentRecord:
    tender_id: str
    label: str | None
    document_type: str | None
    url: str
    raw_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TenderRecord:
    tender_id: str
    plan_id: str | None
    organization: str | None
    title: str | None
    publication_date: datetime | None
    deadline: datetime | None
    reserved_sme: bool | None
    detail_url: str
    raw_payload: dict[str, Any]
    detail_fields: dict[str, Any] = field(default_factory=dict)
    documents: list[DocumentRecord] = field(default_factory=list)


@dataclass(slots=True)
class FetchResult:
    tenders: list[TenderRecord]
    errors: list[str]


def normalize_text(value: object) -> str | None:
    if value is None:
        return None
    text = html.unescape(str(value))
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def normalize_tender_id(value: object) -> str:
    text = normalize_text(value)
    if not text:
        raise NormalizationError("identifiant AO absent")
    match = TENDER_ID_RE.fullmatch(text)
    if not match:
        raise NormalizationError("identifiant AO public invalide")
    return f"Tender-{int(match.group('number'))}"


def normalize_bool(value: object) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = normalize_text(value)
    if text is None:
        return None
    lowered = text.casefold()
    if lowered in {"1", "true", "yes", "oui", "y", "o"}:
        return True
    if lowered in {"0", "false", "no", "non", "n"}:
        return False
    return None


def parse_datetime(value: object) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, (int, float)):
        timestamp = float(value)
        if timestamp > 10_000_000_000:
            timestamp /= 1000
        parsed = datetime.fromtimestamp(timestamp, tz=TUNIS_TZ)
    else:
        text = normalize_text(value)
        if not text:
            return None
        ms_match = MICROSOFT_DATE_RE.fullmatch(text)
        if ms_match:
            return datetime.fromtimestamp(
                int(ms_match.group("milliseconds")) / 1000,
                tz=TUNIS_TZ,
            )

        iso_candidate = text.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(iso_candidate)
        except ValueError:
            parsed = None
            for date_format in (
                "%d/%m/%Y %H:%M:%S",
                "%d/%m/%Y %H:%M",
                "%d/%m/%Y",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M",
            ):
                try:
                    parsed = datetime.strptime(text, date_format)
                    break
                except ValueError:
                    continue
            if parsed is None:
                return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=TUNIS_TZ)
    return parsed


def _nested(mapping: dict[str, Any], *keys: str) -> Any:
    current: Any = mapping
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def normalize_tender(row: dict[str, Any], base_url: str) -> TenderRecord:
    tender_id = normalize_tender_id(row.get("id", row.get("tender_id")))
    plan = row.get("plan") if isinstance(row.get("plan"), dict) else {}
    reserve_value = row.get("reservedSME")
    if reserve_value is None:
        reserve_value = plan.get("reservedSME")

    organization = _nested(row, "organization", "name_fr")
    if organization is None:
        organization = row.get("organization_name_fr") or row.get("organisme")

    plan_id = row.get("planID") or plan.get("id") or row.get("plan_id")
    detail_url = urljoin(base_url.rstrip("/") + "/", f"fr/appels-doffres/{tender_id}")

    return TenderRecord(
        tender_id=tender_id,
        plan_id=normalize_text(plan_id),
        organization=normalize_text(organization),
        title=normalize_text(row.get("title_fr") or row.get("title_ar") or row.get("title")),
        publication_date=parse_datetime(row.get("publication_date")),
        deadline=parse_datetime(row.get("tenderPeriod_endDate") or row.get("date_limite")),
        reserved_sme=normalize_bool(reserve_value),
        detail_url=detail_url,
        raw_payload=dict(row),
    )


def _document_type(url: str, label: str | None) -> str | None:
    suffix = PurePosixPath(urlparse(url).path).suffix.lower().lstrip(".")
    if suffix:
        return suffix[:30]
    text = (label or "").casefold()
    for candidate in ("pdf", "docx", "doc", "xlsx", "xls", "zip", "rar"):
        if candidate in text:
            return candidate
    return None


def parse_detail_page(
    html_text: str,
    detail_url: str,
    tender_id: str,
) -> tuple[dict[str, str], list[DocumentRecord]]:
    soup = BeautifulSoup(html_text, "html.parser")
    fields: dict[str, str] = {}

    strong_nodes = list(soup.find_all("strong"))
    detail_nodes = [
        strong
        for strong in strong_nodes
        if strong.parent is not None
        and strong.parent.name == "p"
        and "medium" in (strong.parent.get("class") or [])
    ]
    if detail_nodes:
        strong_nodes = detail_nodes

    for strong in strong_nodes:
        label = normalize_text(strong.get_text(" ", strip=True))
        parent = strong.parent
        if not label or parent is None:
            continue
        whole = normalize_text(parent.get_text(" ", strip=True))
        if not whole:
            continue
        value = whole
        if value.startswith(label):
            value = value[len(label) :].lstrip(" :–-")
        key = label.rstrip(" :")
        if key and value and value != key:
            unique_key = key
            suffix = 2
            while unique_key in fields:
                unique_key = f"{key} ({suffix})"
                suffix += 1
            fields[unique_key] = value

    documents: list[DocumentRecord] = []
    seen_urls: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        raw_href = str(anchor.get("href", "")).strip()
        absolute_url = urldefrag(urljoin(detail_url, raw_href))[0]
        parsed = urlparse(absolute_url)
        if parsed.scheme != "https":
            continue
        if parsed.hostname not in ALLOWED_DOCUMENT_HOSTS:
            continue
        if not parsed.path.startswith("/storage/tender/"):
            continue
        if absolute_url in seen_urls:
            continue
        seen_urls.add(absolute_url)
        label = normalize_text(anchor.get_text(" ", strip=True))
        documents.append(
            DocumentRecord(
                tender_id=tender_id,
                label=label,
                document_type=_document_type(absolute_url, label),
                url=absolute_url,
                raw_metadata={"href_source": raw_href},
            )
        )

    return fields, documents


class HaicopClient:
    """Client limité aux pages et endpoints publics documentés."""

    def __init__(
        self,
        base_url: str,
        timeout: tuple[float, float],
        user_agent: str,
        session: requests.Session | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.list_url = f"{self.base_url}/fr/appels-doffres"
        self.timeout = timeout
        self.session = session or requests.Session()

        retry = Retry(
            total=3,
            connect=3,
            read=3,
            status=3,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET"}),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.headers.update(
            {
                "User-Agent": user_agent,
                "Referer": self.list_url,
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json, text/javascript, */*; q=0.01",
            }
        )

    @staticmethod
    def _datatable_params(start: int, length: int) -> dict[str, str | int]:
        columns = [
            ("id", ""),
            ("organization.name_fr", "organization.name_fr"),
            ("title_fr", ""),
            ("tenderPeriod_endDate", ""),
            ("publication_date", ""),
            ("reservedSME", ""),
        ]
        params: dict[str, str | int] = {
            "draw": 1,
            "start": start,
            "length": length,
            "order[0][column]": 0,
            "order[0][dir]": "desc",
            "search[value]": "",
            "search[regex]": "false",
        }
        for index, (data, name) in enumerate(columns):
            prefix = f"columns[{index}]"
            params[f"{prefix}[data]"] = data
            params[f"{prefix}[name]"] = name
            params[f"{prefix}[searchable]"] = "true"
            params[f"{prefix}[orderable]"] = "true"
            params[f"{prefix}[search][value]"] = ""
            params[f"{prefix}[search][regex]"] = "false"
        return params

    def fetch_tenders(self, limit: int, since_days: int | None = None) -> FetchResult:
        if limit < 1:
            raise ValueError("limit doit être supérieur à zéro")
        if since_days is not None and since_days < 0:
            raise ValueError("since_days ne peut pas être négatif")

        cutoff = None
        if since_days is not None:
            cutoff = datetime.now(TUNIS_TZ) - timedelta(days=since_days)

        tenders: list[TenderRecord] = []
        errors: list[str] = []
        seen_ids: set[str] = set()
        start = 0
        page_size = min(100, max(limit, 20))

        while len(tenders) < limit:
            params = self._datatable_params(start, page_size)
            try:
                response = self.session.get(self.list_url, params=params, timeout=self.timeout)
                response.raise_for_status()
                payload = response.json()
            except (requests.RequestException, ValueError) as exc:
                raise HaicopError(f"liste HAICOP inaccessible: {type(exc).__name__}") from exc

            rows = payload.get("data") if isinstance(payload, dict) else None
            if not isinstance(rows, list):
                raise HaicopError("réponse HAICOP inattendue: champ data absent")
            if not rows:
                break

            for row_index, row in enumerate(rows, start=start):
                if not isinstance(row, dict):
                    errors.append(f"ligne {row_index}: format non objet")
                    continue
                try:
                    tender = normalize_tender(row, self.base_url)
                except NormalizationError as exc:
                    errors.append(f"ligne {row_index}: {exc}")
                    continue
                if tender.tender_id in seen_ids:
                    continue
                seen_ids.add(tender.tender_id)
                if cutoff is not None:
                    if tender.publication_date is None or tender.publication_date < cutoff:
                        continue
                tenders.append(tender)
                if len(tenders) >= limit:
                    break

            start += len(rows)
            total = payload.get("recordsFiltered") if isinstance(payload, dict) else None
            if isinstance(total, int) and start >= total:
                break
            if len(rows) < page_size:
                break
            if start >= 10_000:
                errors.append("pagination interrompue après 10 000 lignes")
                break

        return FetchResult(tenders=tenders, errors=errors)

    def fetch_detail(self, tender: TenderRecord) -> tuple[dict[str, str], list[DocumentRecord]]:
        headers = {"Accept": "text/html,application/xhtml+xml"}
        try:
            response = self.session.get(tender.detail_url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise HaicopError(
                f"détail {tender.tender_id} inaccessible: {type(exc).__name__}"
            ) from exc
        return parse_detail_page(response.text, tender.detail_url, tender.tender_id)

    def close(self) -> None:
        self.session.close()
