from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from aiogram import F, Router

from bot.keyboards.factories import BatchSizeFactory
from bot.keyboards.inline import ik_action_with_account, ik_choose_batch_size
from bot.states import AccountState

from .common import account_from_state, alert_notifier

router = Router()
logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery
    from sqlalchemy.ext.asyncio import AsyncSession

    from bot.db.models import UserDB


@router.callback_query(AccountState.actions, F.data == "change_batch_size")
async def change_batch_size(
    query: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: UserDB,
) -> None:
    account = await account_from_state(state, session, alert_notifier(query), user)
    if not account:
        return

    await query.message.edit_text(
        text=(
            "Выберите новую пропускную способность для аккаунта.\n"
            f"Текущее значение: {account.batch_size}"
        ),
        reply_markup=await ik_choose_batch_size(account.batch_size),
    )


@router.callback_query(AccountState.actions, BatchSizeFactory.filter())
async def set_batch_size(
    query: CallbackQuery,
    callback_data: BatchSizeFactory,
    state: FSMContext,
    session: AsyncSession,
    user: UserDB,
) -> None:
    account = await account_from_state(state, session, alert_notifier(query), user)
    if not account:
        return

    new_size = callback_data.value
    if not 1 <= new_size <= 30:
        await query.answer(text="Недопустимое значение", show_alert=True)
        return

    account.batch_size = new_size
    await session.commit()

    await query.message.edit_text(
        text=f"Пропускная способность установлена на {new_size}",
        reply_markup=await ik_action_with_account(),
    )


@router.callback_query(AccountState.actions, F.data == "batch_size_back")
async def batch_size_back(
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
        reply_markup=await ik_action_with_account(),
    )
