from __future__ import annotations

import logging
from typing import Final, Iterable

import msgpack
from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from bot.db.models import Account, Job, UserDB

logger = logging.getLogger(__name__)
minute: Final[int] = 60


def key_build(key: str) -> str:
    return f"post_manager:func:send_posts:{key}"


key_last_post_id = key_build("last_post_id")


def _format_username(value: str | None) -> str:
    if not value:
        return ""
    return value if value.startswith("@") else f"@{value}"


def _format_payload_item(item: object) -> str:
    if isinstance(item, dict):
        name = item.get("name") if isinstance(item.get("name"), str) else None
        username = (
            item.get("username") if isinstance(item.get("username"), str) else None
        )
        uname = _format_username(username)
        if name or uname:
            return " ".join(part for part in (name, uname) if part)
        return "\n".join(f"{k}: {v}" for k, v in item.items())
    return str(item)


def _payload_to_text(payload: object) -> str:
    if isinstance(payload, list):
        lines: Iterable[str] = (_format_payload_item(item) for item in payload)
        text = "\n".join(lines).strip()
        return text or "Ответ задачи пуст"
    if isinstance(payload, dict):
        return "\n".join(f"{k}: {v}" for k, v in payload.items())
    return str(payload)


async def send_job_answers(
    sessionmaker: async_sessionmaker,
    bot: Bot,
) -> None:
    async with sessionmaker() as session:
        stmt = (
            select(Job, Account, UserDB)
            .join(Account, Job.account_id == Account.id)
            .join(UserDB, Account.user_id == UserDB.id)
            .where(Job.answer.is_not(None))
        )
        rows = (await session.execute(stmt)).all()

        for job, account, user in rows:
            try:
                payload = msgpack.unpackb(job.answer, raw=False)
            except Exception as exc:  # pragma: no cover - guardrail
                logger.exception(
                    "Не удалось декодировать ответ задачи %s: %s", job.id, exc
                )
                payload = f"Не удалось декодировать ответ: {exc}"

            # header = f"Результат задачи {job.name} для {account.name or account.phone}"
            text = _payload_to_text(payload)

            try:
                await bot.send_message(chat_id=user.user_id, text=text)
            except Exception as exc:  # pragma: no cover - network related
                logger.exception(
                    "Не удалось отправить результат задачи %s пользователю %s: %s",
                    job.id,
                    user.id,
                    exc,
                )

            await session.delete(job)

        if rows:
            await session.commit()
