from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from aiogram import F, Router

from bot.db.models import Job
from bot.keyboards.inline import ik_action_with_account
from bot.states import AccountState

from .common import account_back_to, account_from_state, alert_notifier

router = Router()
logger = logging.getLogger(__name__)

JOB_GET_NAMES = "get_names_and_usernames"

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery
    from sqlalchemy.ext.asyncio import AsyncSession

    from bot.db.models import UserDB


@router.callback_query(AccountState.actions, F.data == "create_job_get_names")
async def create_job_get_names(
    query: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: UserDB,
) -> None:
    account = await account_from_state(state, session, alert_notifier(query), user)
    if not account:
        return

    session.add(Job(name=JOB_GET_NAMES, account_id=account.id))
    await session.commit()

    await query.answer(text="Задача создана", show_alert=True)
    await query.message.edit_text(
        text="Действия с аккаунтом",
        reply_markup=await ik_action_with_account(back_to=await account_back_to(state)),
    )
