"""Orchestration quotidienne idempotente, digest et notifications."""

from __future__ import annotations

import hashlib
import json
import os
import re
import smtplib
import subprocess
import unicodedata
from datetime import datetime, timedelta
from email.message import EmailMessage
from pathlib import Path
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

import requests

from .analysis import build_analysis_context, context_fingerprint
from .collector import Collector, NEGATIVE_KEYWORDS, POSITIVE_KEYWORDS
from .config import Settings
from .database import Database
from .documents import DocumentProcessor
from .telegram import split_telegram_text


PARIS = ZoneInfo("Europe/Paris")
DEFAULT_DIGEST_EMAIL = "khayembg07@gmail.com"
EMAIL_RE = re.compile(r"^[^@\s,;]+@[^@\s,;]+\.[^@\s,;]+$")

# A bare mention of a "network" is not enough: HAICOP also contains gas,
# water, road, and training networks. These terms implement the validated
# OneTech profile rule that a pure equipment purchase without a digital
# component is out of scope for the automated shortlist.
DIGITAL_EVIDENCE_KEYWORDS = (
    "logiciel",
    "software",
    "informatique",
    "système d'information",
    "systeme d'information",
    "application web",
    "application mobile",
    "applications informatiques",
    "plateforme",
    "web",
    "data",
    "données",
    "donnees",
    "intelligence artificielle",
    "automatisation",
    "numérique",
    "numerique",
    "digital",
    "cloud",
    "cybersécurité",
    "cybersecurite",
    "réseau informatique",
    "reseau informatique",
    "réseaux informatiques",
    "reseaux informatiques",
)
PURE_EQUIPMENT_KEYWORDS = (
    "équipement",
    "equipement",
    "équipements",
    "equipements",
    "matériel",
    "materiel",
    "matériels",
    "materiels",
    "fourniture",
    "fournitures",
    "acquisition",
    "acquisitions",
)


class AutomationError(RuntimeError):
    """Erreur explicite du pipeline quotidien."""


def _fold(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(char for char in text if not unicodedata.combining(char)).casefold()


def _contains_term(haystack: str, keyword: object) -> bool:
    """Match a normalized word or phrase, never a substring of another word."""

    needle = _fold(keyword).strip()
    if not needle:
        return False
    return re.search(rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])", haystack) is not None


def _relative(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _email_recipients() -> list[str]:
    """Return a validated, ordered and deduplicated digest recipient list."""

    raw = os.getenv("DIGEST_EMAIL_TO", DEFAULT_DIGEST_EMAIL)
    recipients: list[str] = []
    seen: set[str] = set()
    for item in re.split(r"[,;\n]", raw):
        recipient = item.strip()
        if not recipient:
            continue
        normalized = recipient.casefold()
        if not EMAIL_RE.fullmatch(recipient):
            raise AutomationError(f"Adresse DIGEST_EMAIL_TO invalide: {recipient}")
        if normalized not in seen:
            recipients.append(recipient)
            seen.add(normalized)
    if not recipients:
        raise AutomationError("DIGEST_EMAIL_TO ne contient aucun destinataire")
    return recipients


def _automation_config(settings: Settings) -> dict[str, Any]:
    path = settings.project_root / "config" / "automation.json"
    defaults: dict[str, Any] = {
        "positive_keywords": list(POSITIVE_KEYWORDS),
        "negative_keywords": list(NEGATIVE_KEYWORDS),
        "max_candidates": 5,
        "minimum_relevance_score": 6,
        "since_days": 7,
        "collection_limit": 50,
        "document_limit": 200,
    }
    if not path.is_file():
        return defaults
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise AutomationError("config/automation.json doit contenir un objet JSON")
    return {**defaults, **loaded}


def relevance(row: dict[str, Any], config: dict[str, Any]) -> tuple[int, list[str]]:
    """Score lexical explicable, utilisé seulement pour choisir quoi analyser."""
    title_haystack = _fold(str(row.get("titre") or ""))
    offer_haystack = _fold(
        " ".join(
            [
                str(row.get("organisme") or ""),
                str(row.get("titre") or ""),
                json.dumps(row.get("champs_details") or {}, ensure_ascii=False),
            ]
        )
    )
    haystack = f"{offer_haystack} {_fold(str(row.get('extrait_documents') or '')[:30000])}"
    positives = sorted(
        {
            keyword
            for keyword in config.get("positive_keywords", [])
            if _contains_term(haystack, keyword)
        }
    )
    negatives = sorted(
        {
            keyword
            for keyword in config.get("negative_keywords", [])
            if _contains_term(haystack, keyword)
        }
    )
    score = len(positives) * 3 - len(negatives) * 4
    reasons = [f"+ {word}" for word in positives] + [f"- {word}" for word in negatives]
    has_digital_evidence = any(
        _contains_term(title_haystack, keyword) for keyword in DIGITAL_EVIDENCE_KEYWORDS
    )
    has_equipment_signal = any(
        _contains_term(title_haystack, keyword) for keyword in PURE_EQUIPMENT_KEYWORDS
    )
    if has_equipment_signal and not has_digital_evidence:
        score -= 10
        reasons.append("- fourniture/matériel sans composante numérique explicite")
    return score, reasons


class DailyAutomation:
    def __init__(self, settings: Settings, database: Database | None = None) -> None:
        self.settings = settings
        self.database = database or Database(settings)
        self.config = _automation_config(settings)

    def start(
        self,
        *,
        trigger: str = "manuel",
        run_key: str | None = None,
        force: bool = False,
        max_candidates: int | None = None,
        since_days: int | None = None,
        collection_limit: int | None = None,
        document_limit: int | None = None,
    ) -> dict[str, Any]:
        self.database.check_connection()
        today = datetime.now(PARIS).date()
        base_key = run_key or f"daily:{today.isoformat()}"
        effective_key = (
            f"{base_key}:force:{datetime.now(PARIS).strftime('%H%M%S')}:{uuid4().hex[:8]}"
            if force
            else base_key
        )
        maximum = int(max_candidates or self.config["max_candidates"])
        minimum_relevance = int(self.config["minimum_relevance_score"])
        days = int(since_days if since_days is not None else self.config["since_days"])
        collect_limit = int(collection_limit or self.config["collection_limit"])
        docs_limit = int(document_limit or self.config["document_limit"])
        if min(maximum, minimum_relevance, collect_limit, docs_limit) < 1 or days < 0:
            raise AutomationError("Les limites doivent être positives et since-days non négatif")

        parameters = {
            "date": today.isoformat(),
            "max_candidates": maximum,
            "minimum_relevance_score": minimum_relevance,
            "since_days": days,
            "collection_limit": collect_limit,
            "document_limit": docs_limit,
        }
        run = self.database.start_daily_run(
            run_key=effective_key,
            trigger=trigger,
            parameters=parameters,
        )
        run_id = int(run["id"])
        if not bool(run["creee"]):
            existing_candidates = self.database.daily_candidates(run_id)
            return {
                "statut": "reutilisee",
                "execution": run,
                "candidats": existing_candidates,
                "instruction": (
                    "Reprendre les candidats a_analyser, puis appeler daily-finish."
                    if run["statut"] in {"en_cours", "analyse"}
                    else "Cette exécution quotidienne est déjà terminale."
                ),
            }

        try:
            collection = Collector(settings=self.settings, database=self.database).collect(
                limit=collect_limit,
                with_details=True,
                since_days=days,
                dry_run=False,
            )
            processing = DocumentProcessor(
                settings=self.settings,
                database=self.database,
            ).process(limit=docs_limit)

            cutoff = today - timedelta(days=days)
            ranked: list[tuple[int, dict[str, Any], list[str]]] = []
            for row in self.database.open_tenders_for_automation(limit=max(collect_limit * 4, 200)):
                publication = row.get("date_publication")
                publication_date = publication.date() if hasattr(publication, "date") else publication
                if publication_date and publication_date < cutoff:
                    continue
                score, reasons = relevance(row, self.config)
                if score >= minimum_relevance:
                    ranked.append((score, row, reasons))

            # PostgreSQL can return either `date` or `datetime` values
            # depending on the HAICOP field. An ISO value is stable for both
            # and avoids comparing naive and aware datetimes.
            ranked.sort(
                key=lambda item: (item[0], str(item[1].get("date_publication") or "")),
                reverse=True,
            )

            candidates: list[dict[str, Any]] = []
            skipped_unchanged: list[str] = []
            for score, row, reasons in ranked:
                context = build_analysis_context(
                    self.settings,
                    self.database,
                    row["tender_id"],
                )
                fingerprint = context_fingerprint(context)
                if row.get("dernier_contexte_sha256") == fingerprint:
                    skipped_unchanged.append(row["tender_id"])
                    continue
                candidate = self.database.upsert_daily_candidate(
                    run_id=run_id,
                    tender_id=row["tender_id"],
                    context_sha256=fingerprint,
                    relevance_score=score,
                    reasons=reasons,
                )
                candidates.append(
                    {
                        **candidate,
                        "organisme": row.get("organisme"),
                        "titre": row.get("titre"),
                        "date_limite": row.get("date_limite"),
                        "url": row.get("url_detail"),
                    }
                )
                if len(candidates) >= maximum:
                    break

            updated = self.database.update_daily_run(
                run_id,
                status="analyse",
                collection_id=collection.collecte_id,
                candidate_count=len(candidates),
                error=(" | ".join(collection.erreurs)[:500] if collection.erreurs else None),
            )
            return {
                "statut": "analyse",
                "execution": updated,
                "collecte": collection.to_dict(),
                "traitement_documents": processing.to_dict(),
                "candidats": candidates,
                "ignores_contexte_inchange": skipped_unchanged,
                "prochaine_action": (
                    "Analyser chaque tender_id avec la skill analyse-ao, puis lancer daily-finish."
                    if candidates
                    else "Aucun nouveau contexte pertinent; lancer directement daily-finish."
                ),
            }
        except Exception as exc:
            self.database.update_daily_run(
                run_id,
                status="echec",
                error=self.settings.redact(exc),
                terminal=True,
            )
            raise

    def finish(
        self,
        run_id: int,
        *,
        email: bool = False,
        telegram: bool = False,
        mailpit: bool = False,
    ) -> dict[str, Any]:
        run = self.database.get_daily_run(run_id)
        if run is None:
            raise AutomationError(f"Exécution {run_id} introuvable")
        candidates = self.database.reconcile_daily_candidates(run_id)
        successful = [item for item in candidates if item["statut"] == "termine"]
        failed = [item for item in candidates if item["statut"] == "echec"]
        # Freeze the terminal timestamp *before* rendering. The timestamp is
        # part of the digest body and therefore its SHA-256. Rendering first
        # and terminalizing afterwards would make the first retry look like a
        # different digest and could bypass the delivery ledger.
        pre_delivery_status = "terminee" if not failed else "partielle"
        pre_delivery_errors = [item.get("erreur") for item in failed if item.get("erreur")]
        run = self.database.update_daily_run(
            run_id,
            status=pre_delivery_status,
            candidate_count=len(candidates),
            analysis_count=len(successful),
            error=(" | ".join(pre_delivery_errors)[:500] if pre_delivery_errors else None),
            terminal=True,
        )

        markdown = render_digest(run, successful, failed)
        digest_dir = self.settings.project_root / "data" / "digests"
        digest_dir.mkdir(parents=True, exist_ok=True)
        digest_path = digest_dir / f"{datetime.now(PARIS).date().isoformat()}_run-{run_id}.md"
        digest_path.write_text(markdown, encoding="utf-8")
        digest_hash = hashlib.sha256(markdown.encode("utf-8")).hexdigest()

        deliveries: list[dict[str, Any]] = []
        if mailpit:
            for recipient in _email_recipients():
                deliveries.append(
                    self._deliver_mailpit(
                        run_id, digest_hash, digest_path, markdown, recipient
                    )
                )
        if email:
            for recipient in _email_recipients():
                deliveries.append(
                    self._deliver_gmail(run_id, digest_hash, digest_path, recipient)
                )
        if telegram:
            deliveries.append(self._deliver_telegram(run_id, digest_hash, markdown))

        delivery_failures = [item for item in deliveries if item.get("statut") == "echec"]
        status = "terminee" if not failed and not delivery_failures else "partielle"
        error_parts = [item.get("erreur") for item in failed + delivery_failures if item.get("erreur")]
        updated = self.database.update_daily_run(
            run_id,
            status=status,
            candidate_count=len(candidates),
            analysis_count=len(successful),
            digest_path=_relative(digest_path, self.settings.project_root),
            digest_sha256=digest_hash,
            error=(" | ".join(error_parts)[:500] if error_parts else None),
            terminal=True,
        )
        return {
            "statut": status,
            "execution": updated,
            "candidats": candidates,
            "digest": {
                "chemin": _relative(digest_path, self.settings.project_root),
                "sha256": digest_hash,
            },
            "diffusions": deliveries,
        }

    def _reserve(self, run_id: int, channel: str, recipient: str, digest: str) -> dict[str, Any]:
        recipient_hash = hashlib.sha256(recipient.encode("utf-8")).hexdigest()
        return self.database.reserve_delivery(
            run_id=run_id,
            channel=channel,
            recipient_hash=recipient_hash,
            digest_sha256=digest,
        )

    def _deliver_mailpit(
        self,
        run_id: int,
        digest_hash: str,
        digest_path: Path,
        markdown: str,
        recipient: str,
    ) -> dict[str, Any]:
        delivery = self._reserve(run_id, "mailpit", recipient, digest_hash)
        if not delivery.get("claimed", False):
            state = "deja_envoyee" if delivery["statut"] == "envoyee" else "en_cours"
            return {"canal": "mailpit", "statut": state, "id": delivery["id"]}
        try:
            message = EmailMessage()
            message["From"] = os.getenv("MAILPIT_EMAIL_FROM", "onetech-ao@localhost")
            message["To"] = recipient
            message["Subject"] = f"[OneTech AO] Digest quotidien — run {run_id}"
            message.set_content(markdown)
            with smtplib.SMTP(
                os.getenv("MAILPIT_SMTP_HOST", "127.0.0.1"),
                int(os.getenv("MAILPIT_SMTP_PORT", "1025")),
                timeout=10,
            ) as client:
                client.send_message(message)
            saved = self.database.finish_delivery(
                int(delivery["id"]), status="envoyee", external_id=digest_path.name
            )
            return {"canal": "mailpit", "statut": "envoyee", "id": saved["id"]}
        except Exception as exc:
            error = self.settings.redact(exc)
            saved = self.database.finish_delivery(
                int(delivery["id"]), status="echec", error=error
            )
            return {"canal": "mailpit", "statut": "echec", "id": saved["id"], "erreur": error}

    def _deliver_gmail(
        self,
        run_id: int,
        digest_hash: str,
        digest_path: Path,
        recipient: str,
    ) -> dict[str, Any]:
        account = os.getenv("GOG_ACCOUNT", _email_recipients()[0])
        delivery = self._reserve(run_id, "email", recipient, digest_hash)
        if not delivery.get("claimed", False):
            state = "deja_envoyee" if delivery["statut"] == "envoyee" else "en_cours"
            return {"canal": "email", "statut": state, "id": delivery["id"]}
        command = [
            "gog",
            "gmail",
            "send",
            "--to",
            recipient,
            "--subject",
            f"[OneTech AO] Digest quotidien — run {run_id}",
            "--body-file",
            str(digest_path),
            "--account",
            account,
            "--json",
            "--no-input",
        ]
        try:
            completed = subprocess.run(
                command,
                cwd=self.settings.project_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=60,
                check=True,
            )
            payload = json.loads(completed.stdout or "{}")
            external_id = str(payload.get("id") or payload.get("messageId") or "gmail")
            saved = self.database.finish_delivery(
                int(delivery["id"]), status="envoyee", external_id=external_id
            )
            return {"canal": "email", "statut": "envoyee", "id": saved["id"]}
        except Exception as exc:
            stderr = getattr(exc, "stderr", None)
            error = self.settings.redact(stderr or exc)
            saved = self.database.finish_delivery(
                int(delivery["id"]), status="echec", error=error
            )
            return {"canal": "email", "statut": "echec", "id": saved["id"], "erreur": error}

    def _deliver_telegram(self, run_id: int, digest_hash: str, markdown: str) -> dict[str, Any]:
        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
        if not token or not chat_id:
            return {
                "canal": "telegram",
                "statut": "echec",
                "erreur": "TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID absent",
            }
        chunks = split_telegram_text(markdown)
        if not chunks:
            return {"canal": "telegram", "statut": "echec", "erreur": "Digest Telegram vide"}

        sent_ids: list[str] = []
        delivery_ids: list[int] = []
        pending = False
        for index, chunk in enumerate(chunks, start=1):
            # Each chunk has its own ledger reservation.  A failure after a
            # previous chunk cannot make a retry duplicate that first message.
            chunk_recipient = f"{chat_id}:chunk:{index}"
            delivery = self._reserve(run_id, "telegram", chunk_recipient, digest_hash)
            delivery_ids.append(int(delivery["id"]))
            if not delivery.get("claimed", False):
                if delivery["statut"] == "envoyee":
                    continue
                pending = True
                continue
            try:
                response = requests.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={"chat_id": chat_id, "text": chunk, "disable_web_page_preview": True},
                    timeout=(5, 20),
                )
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict) or not payload.get("ok"):
                    raise AutomationError("Telegram a refuse le message")
                external_id = str(payload.get("result", {}).get("message_id") or "telegram")
                saved = self.database.finish_delivery(
                    int(delivery["id"]), status="envoyee", external_id=external_id
                )
                sent_ids.append(str(saved.get("identifiant_externe") or external_id))
            except Exception as exc:
                error = self.settings.redact(exc)
                saved = self.database.finish_delivery(
                    int(delivery["id"]), status="echec", error=error
                )
                return {
                    "canal": "telegram",
                    "statut": "echec",
                    "id": saved["id"],
                    "erreur": error,
                }

        if pending:
            return {"canal": "telegram", "statut": "en_cours", "ids": delivery_ids}
        return {
            "canal": "telegram",
            "statut": "envoyee",
            "ids": delivery_ids,
            "messages": sent_ids,
        }


def render_digest(
    run: dict[str, Any],
    successful: list[dict[str, Any]],
    failed: list[dict[str, Any]],
) -> str:
    lines = [
        "# Digest quotidien OneTech — appels d'offres HAICOP",
        "",
        f"- Exécution : `{run['cle_execution']}` (ID {run['id']})",
        # A digest must remain byte-for-byte stable across retry attempts so
        # that the delivery ledger can prevent duplicate notifications.
        f"- Généré le : {(run.get('terminee_le') or run.get('demarree_le') or datetime.now(PARIS)).isoformat(timespec='seconds')}",
        f"- Analyses disponibles : {len(successful)}",
        f"- Analyses manquantes/échouées : {len(failed)}",
        "",
    ]
    if not successful:
        lines.extend(["Aucune nouvelle opportunité analysée aujourd'hui.", ""])
    for index, item in enumerate(successful, start=1):
        lines.extend(
            [
                f"## {index}. {item['tender_id']} — {item.get('titre') or 'Sans titre'}",
                "",
                f"- Organisme : {item.get('organisme') or 'Non trouvé'}",
                f"- Décision : **{item.get('decision')}** — {item.get('score_total')}/100",
                f"- Date limite : {item.get('date_limite') or 'Non trouvée'}",
                f"- Fiche : `{item.get('fiche_chemin')}`",
                f"- Source : {item.get('url_detail') or 'Non trouvée'}",
                "",
            ]
        )
    if failed:
        lines.extend(["## Limites techniques", ""])
        for item in failed:
            lines.append(f"- {item['tender_id']} : {item.get('erreur') or 'analyse absente'}")
        lines.append("")
    lines.extend(
        [
            "---",
            "Ce digest est une présélection automatisée. Les décisions finales restent à valider humainement.",
            "",
        ]
    )
    return "\n".join(lines)
