"""Narrow HTTP bridge between n8n and the company OpenClaw gateway.

The worker deliberately exposes one business operation.  n8n never receives
the gateway bearer token and cannot invoke arbitrary OpenClaw prompts.
"""

from __future__ import annotations

import os
import secrets
import shlex
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROMPT_RELATIVE_PATH = Path("automation") / "prompts" / "daily_digest.md"
DEFAULT_TIMEZONE = "Europe/Paris"
DEFAULT_TIMEOUT_SECONDS = 1_800.0
MAX_RESPONSE_CHARS = 50_000
DEFAULT_DELIVERY_ARGS = "--mailpit"
ALLOWED_DELIVERY_ARGS = frozenset({"--mailpit", "--email", "--telegram"})


class DailyRunRequest(BaseModel):
    """Optional controls accepted from the trusted n8n workflow."""

    model_config = ConfigDict(extra="forbid")

    run_date: date | None = None
    max_candidates: int = Field(default=5, ge=1, le=5)


class DailyRunResponse(BaseModel):
    status: str
    run_date: date
    session_user: str
    agent_output: str
    output_truncated: bool = False


app = FastAPI(
    title="OneTech AO Automation Worker",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _timezone() -> ZoneInfo:
    name = os.getenv("AUTOMATION_TIMEZONE", DEFAULT_TIMEZONE).strip()
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError as exc:
        raise RuntimeError("AUTOMATION_TIMEZONE is invalid") from exc


def _timeout_seconds() -> float:
    raw = os.getenv("AUTOMATION_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS))
    try:
        value = float(raw)
    except ValueError as exc:
        raise RuntimeError("AUTOMATION_TIMEOUT_SECONDS must be numeric") from exc
    if not 30 <= value <= 3_600:
        raise RuntimeError("AUTOMATION_TIMEOUT_SECONDS must be between 30 and 3600")
    return value


def _chat_completions_url(base_url: str) -> str:
    """Accept a gateway root, /v1 root, or the complete endpoint URL."""

    parsed = urlsplit(base_url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RuntimeError("OPENCLAW_GATEWAY_URL must be an HTTP(S) URL")
    if parsed.query or parsed.fragment:
        raise RuntimeError("OPENCLAW_GATEWAY_URL must not contain query or fragment")

    path = parsed.path.rstrip("/")
    if path.endswith("/v1/chat/completions"):
        endpoint_path = path
    elif path.endswith("/v1"):
        endpoint_path = f"{path}/chat/completions"
    else:
        endpoint_path = f"{path}/v1/chat/completions"
    return urlunsplit((parsed.scheme, parsed.netloc, endpoint_path, "", ""))


def _load_prompt(run_date: date, max_candidates: int) -> str:
    prompt_path = _prompt_path()
    try:
        template = prompt_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError("Daily automation prompt is unavailable") from exc

    return (
        template.replace("{{RUN_DATE}}", run_date.isoformat())
        .replace("{{MAX_CANDIDATES}}", str(max_candidates))
        .replace("{{TIMEZONE}}", str(_timezone()))
        .replace("{{DELIVERY_ARGS}}", _delivery_args())
    )


def _delivery_args() -> str:
    """Return a deliberately narrow, locally configured delivery selection.

    The n8n workflow is allowed to ask the company agent to deliver a digest,
    but it must never turn an arbitrary environment value into a shell fragment.
    Mailpit is the safe default. Email and Telegram require an explicit local
    opt-in in ``.env`` after their recipients have been verified.
    """

    raw = os.getenv("AUTOMATION_DELIVERY_ARGS", DEFAULT_DELIVERY_ARGS).strip()
    try:
        values = shlex.split(raw)
    except ValueError as exc:
        raise RuntimeError("AUTOMATION_DELIVERY_ARGS is invalid") from exc
    if not values or len(values) != len(set(values)) or any(
        value not in ALLOWED_DELIVERY_ARGS for value in values
    ):
        raise RuntimeError(
            "AUTOMATION_DELIVERY_ARGS must only contain --mailpit, --email and --telegram"
        )
    return " ".join(values)


def _prompt_path() -> Path:
    configured = os.getenv("AUTOMATION_PROMPT_PATH", "").strip()
    if configured:
        return Path(configured)
    # Editable/local installs resolve through PROJECT_ROOT.  A wheel installed
    # in the worker image lives in site-packages, while Uvicorn starts in /app.
    for candidate in (PROJECT_ROOT / PROMPT_RELATIVE_PATH, Path.cwd() / PROMPT_RELATIVE_PATH):
        if candidate.is_file():
            return candidate
    return PROJECT_ROOT / PROMPT_RELATIVE_PATH


def _authenticate(
    supplied_token: str | None = Header(default=None, alias="X-Automation-Token"),
) -> None:
    try:
        expected_token = _required_env("AUTOMATION_TOKEN")
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Worker authentication is not configured",
        ) from exc

    if supplied_token is None or not secrets.compare_digest(supplied_token, expected_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid automation token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def _extract_agent_output(payload: Any) -> str:
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("OpenClaw returned an unexpected response") from exc

    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts).strip()
    raise RuntimeError("OpenClaw returned an unsupported response body")


def _redact_worker_secrets(text: str, values: tuple[str, ...]) -> str:
    for value in values:
        if value:
            text = text.replace(value, "[REDACTED]")
    return text


@app.get("/health")
async def health() -> dict[str, str]:
    """Readiness probe; it never calls the LLM or reveals configuration values."""

    try:
        _required_env("AUTOMATION_TOKEN")
        _required_env("OPENCLAW_GATEWAY_TOKEN")
        _chat_completions_url(_required_env("OPENCLAW_GATEWAY_URL"))
        _timeout_seconds()
        _timezone()
        _delivery_args()
        if not _prompt_path().is_file():
            raise RuntimeError("prompt missing")
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Worker configuration is incomplete",
        ) from exc
    return {"status": "ok"}


@app.post(
    "/runs/daily",
    response_model=DailyRunResponse,
    dependencies=[Depends(_authenticate)],
)
async def run_daily(request: DailyRunRequest) -> DailyRunResponse:
    """Ask the company agent to execute one idempotent daily AO run."""

    try:
        timezone = _timezone()
        run_date = request.run_date or datetime.now(timezone).date()
        gateway_token = _required_env("OPENCLAW_GATEWAY_TOKEN")
        automation_token = _required_env("AUTOMATION_TOKEN")
        endpoint = _chat_completions_url(_required_env("OPENCLAW_GATEWAY_URL"))
        timeout_seconds = _timeout_seconds()
        prompt = _load_prompt(run_date, request.max_candidates)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Worker configuration is incomplete",
        ) from exc

    session_user = f"onetech-ao-daily:{run_date.isoformat()}"
    body = {
        "model": os.getenv("OPENCLAW_AGENT_MODEL", "openclaw/default").strip()
        or "openclaw/default",
        "user": session_user,
        "stream": False,
        "messages": [{"role": "user", "content": prompt}],
    }
    headers = {
        "Authorization": f"Bearer {gateway_token}",
        "Content-Type": "application/json",
        "X-OpenClaw-Message-Channel": "automation",
    }

    try:
        timeout = httpx.Timeout(timeout_seconds, connect=min(timeout_seconds, 15.0))
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(endpoint, headers=headers, json=body)
            response.raise_for_status()
            output = _extract_agent_output(response.json())
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="OpenClaw daily run timed out",
        ) from exc
    except (httpx.HTTPError, ValueError, RuntimeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OpenClaw daily run failed",
        ) from exc

    output = _redact_worker_secrets(output, (gateway_token, automation_token))
    if not output:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OpenClaw daily run returned no summary",
        )
    truncated = len(output) > MAX_RESPONSE_CHARS
    if truncated:
        output = output[:MAX_RESPONSE_CHARS]

    return DailyRunResponse(
        status="ok",
        run_date=run_date,
        session_user=session_user,
        agent_output=output,
        output_truncated=truncated,
    )
