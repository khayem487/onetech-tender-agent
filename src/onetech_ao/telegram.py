"""Small, defensive Telegram Bot API adapter for the OneTech AO project.

The adapter deliberately knows nothing about OpenClaw, PostgreSQL or business
logic.  It validates Telegram payloads, keeps the Bot API boundary narrow and
never includes a bot token in raised error messages.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import requests


MAX_TELEGRAM_MESSAGE_CHARS = 3900
GROUP_TYPES = frozenset({"group", "supergroup"})


class TelegramError(RuntimeError):
    """A safe, user-displayable failure at the Telegram API boundary."""


@dataclass(frozen=True, slots=True)
class TelegramBotIdentity:
    """Only the Bot API facts needed to filter incoming group messages."""

    bot_id: int
    username: str
    can_read_all_group_messages: bool


@dataclass(frozen=True, slots=True)
class TelegramInboundMessage:
    """Validated, privacy-minimised representation of a Telegram update."""

    update_id: int
    chat_id: str
    chat_type: str
    message_id: int
    sender_id: str | None
    text: str
    interaction_kind: str


def _api_description(payload: Any) -> str:
    """Return a concise Telegram error without echoing request URLs/tokens."""

    if isinstance(payload, dict):
        value = payload.get("description")
        if isinstance(value, str) and value.strip():
            return value.strip()[:300]
    return "Telegram API request failed"


class TelegramApi:
    """Minimal synchronous client used from the worker's bounded poll endpoint."""

    def __init__(self, token: str, *, session: requests.Session | None = None) -> None:
        cleaned = token.strip()
        if not cleaned:
            raise TelegramError("TELEGRAM_BOT_TOKEN absent")
        self._token = cleaned
        self._session = session or requests.Session()

    def _url(self, method: str) -> str:
        return f"https://api.telegram.org/bot{self._token}/{method}"

    def _request(self, method: str, *, json_body: dict[str, Any] | None = None,
                 params: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            if json_body is None:
                response = self._session.get(self._url(method), params=params, timeout=(5, 35))
            else:
                response = self._session.post(self._url(method), json=json_body, timeout=(5, 35))
        except requests.RequestException as exc:
            raise TelegramError("Telegram API inaccessible") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise TelegramError("Telegram API returned invalid JSON") from exc
        if not response.ok or not isinstance(payload, dict) or not payload.get("ok"):
            raise TelegramError(_api_description(payload))
        return payload

    def get_me(self) -> TelegramBotIdentity:
        result = self._request("getMe").get("result")
        if not isinstance(result, dict):
            raise TelegramError("Telegram bot identity is invalid")
        bot_id = result.get("id")
        username = result.get("username")
        if not isinstance(bot_id, int) or not isinstance(username, str) or not username.strip():
            raise TelegramError("Telegram bot identity is incomplete")
        return TelegramBotIdentity(
            bot_id=bot_id,
            username=username.strip(),
            can_read_all_group_messages=bool(result.get("can_read_all_group_messages")),
        )

    def get_chat(self, chat_id: str) -> dict[str, Any]:
        result = self._request("getChat", params={"chat_id": chat_id}).get("result")
        if not isinstance(result, dict):
            raise TelegramError("Telegram group details are invalid")
        return result

    def get_updates(self, *, offset: int, limit: int = 100) -> list[dict[str, Any]]:
        if offset < 0 or not 1 <= limit <= 100:
            raise TelegramError("Telegram polling parameters are invalid")
        result = self._request(
            "getUpdates",
            params={"offset": offset, "limit": limit, "allowed_updates": '["message"]'},
        ).get("result")
        if not isinstance(result, list):
            raise TelegramError("Telegram updates are invalid")
        return [item for item in result if isinstance(item, dict)]

    def send_message(
        self,
        *,
        chat_id: str,
        text: str,
        reply_to_message_id: int | None = None,
    ) -> int:
        content = text.strip()
        if not content:
            raise TelegramError("Telegram message is empty")
        if len(content) > MAX_TELEGRAM_MESSAGE_CHARS:
            raise TelegramError("Telegram message exceeds the safe single-message limit")
        body: dict[str, Any] = {
            "chat_id": chat_id,
            "text": content,
            "disable_web_page_preview": True,
        }
        if reply_to_message_id is not None:
            body["reply_parameters"] = {
                "message_id": reply_to_message_id,
                "allow_sending_without_reply": True,
            }
        result = self._request("sendMessage", json_body=body).get("result")
        if not isinstance(result, dict) or not isinstance(result.get("message_id"), int):
            raise TelegramError("Telegram did not return a sent message ID")
        return int(result["message_id"])


def split_telegram_text(text: str, *, max_chars: int = MAX_TELEGRAM_MESSAGE_CHARS) -> list[str]:
    """Split a long digest at newlines where possible, without losing content."""

    if max_chars < 100:
        raise ValueError("max_chars must be at least 100")
    remaining = text.strip()
    if not remaining:
        return []
    chunks: list[str] = []
    while len(remaining) > max_chars:
        boundary = remaining.rfind("\n", 0, max_chars + 1)
        if boundary < max_chars // 2:
            boundary = remaining.rfind(" ", 0, max_chars + 1)
        if boundary < max_chars // 2:
            boundary = max_chars
        chunk = remaining[:boundary].strip()
        if not chunk:
            boundary = max_chars
            chunk = remaining[:boundary]
        chunks.append(chunk)
        remaining = remaining[boundary:].lstrip()
    if remaining:
        chunks.append(remaining)
    return chunks


def parse_group_interaction(
    update: dict[str, Any],
    *,
    bot_id: int,
    bot_username: str,
) -> TelegramInboundMessage | None:
    """Accept only non-bot group mentions, replies to the bot, or bot commands."""

    update_id = update.get("update_id")
    message = update.get("message")
    if not isinstance(update_id, int) or not isinstance(message, dict):
        return None
    chat = message.get("chat")
    sender = message.get("from")
    text = message.get("text")
    message_id = message.get("message_id")
    if (
        not isinstance(chat, dict)
        or not isinstance(message_id, int)
        or not isinstance(text, str)
        or not text.strip()
        or not isinstance(sender, dict)
        or sender.get("is_bot") is True
    ):
        return None
    chat_id = chat.get("id")
    chat_type = chat.get("type")
    if chat_id is None or not isinstance(chat_type, str) or chat_type not in GROUP_TYPES:
        return None

    normalized_username = bot_username.lstrip("@").casefold()
    mention_pattern = re.compile(
        rf"(?<![A-Za-z0-9_])@{re.escape(normalized_username)}(?![A-Za-z0-9_])",
        re.IGNORECASE,
    )
    is_mention = bool(mention_pattern.search(text))

    reply = message.get("reply_to_message")
    reply_sender = reply.get("from") if isinstance(reply, dict) else None
    is_reply = isinstance(reply_sender, dict) and reply_sender.get("id") == bot_id

    command_pattern = re.compile(
        rf"^/[A-Za-z][A-Za-z0-9_]*(?:@{re.escape(normalized_username)})?(?:\s|$)",
        re.IGNORECASE,
    )
    is_command = bool(command_pattern.match(text.strip()))
    if not (is_mention or is_reply or is_command):
        return None

    kind = "mention" if is_mention else "reply" if is_reply else "command"
    sender_id = sender.get("id")
    return TelegramInboundMessage(
        update_id=update_id,
        chat_id=str(chat_id),
        chat_type=chat_type,
        message_id=message_id,
        sender_id=str(sender_id) if isinstance(sender_id, int) else None,
        text=text.strip(),
        interaction_kind=kind,
    )


def clean_interaction_text(text: str, *, bot_username: str) -> str:
    """Remove a leading bot command/mention before forwarding it to the agent."""

    username = bot_username.lstrip("@")
    cleaned = re.sub(rf"@{re.escape(username)}\b", "", text, flags=re.IGNORECASE)
    cleaned = re.sub(
        rf"^/[A-Za-z][A-Za-z0-9_]*(?:@{re.escape(username)})?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    return " ".join(cleaned.split()).strip() or "Aide-moi concernant les appels d'offres OneTech."
