from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Final

from aiogram import F, Router
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import func, select

from bot.db.models import Account, Username
from bot.keyboards.factories import HistoryFactory
from bot.keyboards.inline import ik_action_with_account
from bot.states import AccountState

from .common import account_back_to, account_from_state, alert_notifier

router = Router()
logger = logging.getLogger(__name__)
HISTORY_PAGE_SIZE: Final[int] = 10
MAX_TG_MESSAGE_LENGTH: Final[int] = 4096

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery
    from sqlalchemy.ext.asyncio import AsyncSession

    from bot.db.models import UserDB


def _format_username_item(username: Username) -> str:
    mention = username.username
    if mention and not mention.startswith("@"):
        mention = f"@{mention}"

    status = "✅" if username.sended else "⏳"
    item = f" — {username.item_name}" if username.item_name else ""
    return f"{mention}{item} ({status})"


def _history_text(
    account: Account,
    usernames: list[Username],
    page: int,
    total_pages: int,
    total: int,
) -> str:
    header = account.name or account.phone
    rows = [
        f"История отправок для {header}",
        f"Всего получателей: {total}",
        f"Страница {page}/{total_pages}",
        "",
    ]
    start_index = 1 + (page - 1) * HISTORY_PAGE_SIZE
    for index, username in enumerate(usernames, start=start_index):
        rows.append(f"{index}. {_format_username_item(username)}")

    if not usernames:
        rows.append("Пока нет ни одной отправки или очереди.")

    text = "\n".join(rows)
    if len(text) > MAX_TG_MESSAGE_LENGTH:
        text = text[: MAX_TG_MESSAGE_LENGTH - 3] + "..."
    return text


def _history_keyboard(page: int, total_pages: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    adjust = []
    if total_pages > 1 and page > 1:
        builder.button(text="⬅️", callback_data=HistoryFactory(page=page - 1))
        adjust.append(1)
    if total_pages > 1 and page < total_pages:
        builder.button(text="➡️", callback_data=HistoryFactory(page=page + 1))
        if adjust:
            adjust[0] += 1
        else:
            adjust.append(1)
    builder.button(text="🔙 К действиям", callback_data="history_back")
    adjust.append(1)
    builder.adjust(*adjust)
    return builder.as_markup()


@router.callback_query(AccountState.actions, HistoryFactory.filter())
async def history_usernames(
    query: CallbackQuery,
    callback_data: HistoryFactory,
    state: FSMContext,
    session: AsyncSession,
    user: UserDB,
) -> None:
    account = await account_from_state(state, session, alert_notifier(query), user)
    if not account:
        return

    total_stmt = (
        select(func.count())
        .select_from(Username)
        .where(Username.account_id == account.id)
    )
    total = (await session.execute(total_stmt)).scalar_one()
    total_pages = max(1, (total + HISTORY_PAGE_SIZE - 1) // HISTORY_PAGE_SIZE)
    page = max(1, min(callback_data.page, total_pages))

    stmt = (
        select(Username)
        .where(Username.account_id == account.id)
        .order_by(Username.id.desc())
        .offset((page - 1) * HISTORY_PAGE_SIZE)
        .limit(HISTORY_PAGE_SIZE)
    )
    usernames = (await session.execute(stmt)).scalars().all()

    text = _history_text(account, usernames, page, total_pages, total)
    await query.message.edit_text(
        text=text,
        reply_markup=_history_keyboard(page, total_pages),
    )


@router.callback_query(AccountState.actions, F.data == "history_back")
async def history_back_to_actions(
    query: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: UserDB,
) -> None:
    account = await account_from_state(state, session, alert_notifier(query), user)
    if not account:
        return

    await query.message.edit_text(
        text="Действия с аккаунтом",
        reply_markup=await ik_action_with_account(back_to=await account_back_to(state)),
    )
