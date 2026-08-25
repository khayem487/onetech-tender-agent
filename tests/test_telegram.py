from __future__ import annotations

import asyncio

from onetech_ao.telegram import (
    TelegramBotIdentity,
    clean_interaction_text,
    parse_group_interaction,
    split_telegram_text,
)
from onetech_ao.worker import TelegramPollRequest, poll_telegram


BOT_ID = 8509493240
BOT_USERNAME = "belbelkhabelbelyembelbel487_bot"


def _update(*, text: str, chat_type: str = "supergroup", reply_to_bot: bool = False) -> dict[str, object]:
    message: dict[str, object] = {
        "message_id": 18,
        "from": {"id": 42, "is_bot": False},
        "chat": {"id": -1001234567890, "type": chat_type, "title": "OneTech AO"},
        "text": text,
    }
    if reply_to_bot:
        message["reply_to_message"] = {"message_id": 10, "from": {"id": BOT_ID, "is_bot": True}}
    return {"update_id": 99, "message": message}


def test_group_mention_is_accepted() -> None:
    interaction = parse_group_interaction(
        _update(text=f"@{BOT_USERNAME} quels sont les délais ?"),
        bot_id=BOT_ID,
        bot_username=BOT_USERNAME,
    )

    assert interaction is not None
    assert interaction.chat_id == "-1001234567890"
    assert interaction.interaction_kind == "mention"


def test_reply_to_bot_is_accepted_without_a_mention() -> None:
    interaction = parse_group_interaction(
        _update(text="Peux-tu expliquer cette AO ?", reply_to_bot=True),
        bot_id=BOT_ID,
        bot_username=BOT_USERNAME,
    )

    assert interaction is not None
    assert interaction.interaction_kind == "reply"


def test_plain_group_message_and_private_message_are_ignored() -> None:
    assert parse_group_interaction(
        _update(text="Bonjour tout le monde"), bot_id=BOT_ID, bot_username=BOT_USERNAME
    ) is None
    assert parse_group_interaction(
        _update(text=f"@{BOT_USERNAME} bonjour", chat_type="private"),
        bot_id=BOT_ID,
        bot_username=BOT_USERNAME,
    ) is None


def test_command_and_clean_text_are_supported() -> None:
    interaction = parse_group_interaction(
        _update(text=f"/status@{BOT_USERNAME} Tender-103283"),
        bot_id=BOT_ID,
        bot_username=BOT_USERNAME,
    )

    assert interaction is not None
    assert interaction.interaction_kind == "command"
    assert clean_interaction_text(interaction.text, bot_username=BOT_USERNAME) == "Tender-103283"


def test_long_telegram_text_is_split_without_losing_words() -> None:
    source = "Premier bloc\n" + ("mot " * 200) + "\nDernier bloc"
    chunks = split_telegram_text(source, max_chars=180)

    assert len(chunks) > 1
    assert all(len(chunk) <= 180 for chunk in chunks)
    assert " ".join(chunks).replace("\n", " ").split() == source.replace("\n", " ").split()


def test_poll_acknowledges_ignored_updates(monkeypatch) -> None:
    """Plain group chatter must not clog the durable Telegram offset."""

    class FakeApi:
        def __init__(self, token: str) -> None:
            assert token == "test-token"

        def get_me(self) -> TelegramBotIdentity:
            return TelegramBotIdentity(BOT_ID, BOT_USERNAME, False)

        def get_chat(self, chat_id: str) -> dict[str, object]:
            return {"id": int(chat_id), "type": "supergroup", "title": "OneTech AO"}

        def get_updates(self, *, offset: int, limit: int = 100) -> list[dict[str, object]]:
            assert offset == 0
            assert limit == 50
            return [_update(text="Bonjour sans mention")]

    class FakeDatabase:
        def __init__(self) -> None:
            self.offsets: list[int] = []

        def telegram_poll_offset(self, consumer: str) -> int:
            return 0

        def advance_telegram_poll_offset(self, value: int, consumer: str) -> int:
            self.offsets.append(value)
            return value

    database = FakeDatabase()
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "-1001234567890")
    monkeypatch.setattr("onetech_ao.worker.TelegramApi", FakeApi)
    monkeypatch.setattr("onetech_ao.worker._worker_database", lambda: database)

    response = asyncio.run(poll_telegram(TelegramPollRequest(max_updates=50)))

    assert response.status == "ok"
    assert response.updates == 1
    assert response.eligible == 0
    assert database.offsets == [100]
