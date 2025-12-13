from __future__ import annotations

import logging
from functools import partial
from typing import TYPE_CHECKING, Awaitable, Callable

from bot.db.models import Account

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery
    from sqlalchemy.ext.asyncio import AsyncSession

    from bot.db.models import UserDB

logger = logging.getLogger(__name__)
Notifier = Callable[[str], Awaitable[None]]


def alert_notifier(query: CallbackQuery) -> Notifier:
    return partial(query.answer, show_alert=True)


async def account_from_state(
    state: FSMContext,
    session: AsyncSession,
    notify: Notifier,
    user: UserDB | None,
) -> Account | None:
    data = await state.get_data()
    account_id: int | None = data.get("account_id")
    if not account_id:
        await notify("Ошибка: account_id пустой в state")
        return None

    account = await session.get(Account, account_id)
    if not account:
        await notify("Ошибка: account не найден в базе данных")
        return None
    if user and account.user_id and account.user_id != user.id:
        await notify("Аккаунт не найден для текущего пользователя")
        return None

    return account
