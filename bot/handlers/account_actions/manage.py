from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from aiogram import Router
from sqlalchemy import select

from bot.db.models import Account
from bot.keyboards.factories import AccountFactory
from bot.keyboards.inline import ik_action_with_account, ik_connect_account
from bot.states import AccountState

from .common import account_back_to
from .texts import ensure_texts

router = Router()
logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery
    from sqlalchemy.ext.asyncio import AsyncSession

    from bot.db.models import UserDB


@router.callback_query(AccountFactory.filter())
async def manage_account(
    query: CallbackQuery,
    callback_data: AccountFactory,
    state: FSMContext,
    session: AsyncSession,
    user: UserDB,
) -> None:
    if not user.is_admin:
        await query.answer(text="Недостаточно прав", show_alert=True)
        return

    account_id = callback_data.id
    account = await session.scalar(
        select(Account).where(
            Account.id == account_id,
            Account.user_id == user.id,
        )
    )
    if not account:
        await query.answer(text="Аккаунт не найден", show_alert=True)
        return

    _, created_texts = await ensure_texts(session, account.id)
    if created_texts:
        await session.commit()

    back_to = await account_back_to(state)
    markup = (
        await ik_action_with_account(back_to=back_to)
        if account.is_connected
        else await ik_connect_account(back_to=back_to)
    )
    await query.message.edit_text("Выберите действие", reply_markup=markup)
    await state.set_state(AccountState.actions)
    await state.update_data(account_id=account_id, accounts_back_to=back_to)
