from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from aiogram import F, Router

from bot.keyboards.inline import ik_action_with_account
from bot.states import AccountState

from .common import account_from_state, alert_notifier

router = Router()
logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery
    from sqlalchemy.ext.asyncio import AsyncSession

    from bot.db.models import UserDB


@router.callback_query(AccountState.actions, F.data == "start_account")
async def start_account(
    query: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: UserDB,
) -> None:
    account = await account_from_state(state, session, alert_notifier(query), user)
    if not account:
        return

    account.is_started = True
    await session.commit()

    await query.message.edit_text(
        f"Бот {account.name} [{account.phone}] запущен",
        reply_markup=await ik_action_with_account(),
    )


@router.callback_query(AccountState.actions, F.data == "stop_account")
async def stop_account(
    query: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: UserDB,
) -> None:
    account = await account_from_state(state, session, alert_notifier(query), user)
    if not account:
        return

    account.is_started = False
    await session.commit()

    await query.message.edit_text(
        f"Бот {account.name} [{account.phone}] остановлен",
        reply_markup=await ik_action_with_account(),
    )
