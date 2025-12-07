from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from aiogram import F, Router
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.accounts import show_bots
from bot.keyboards.factories import BackFactory
from bot.states import AccountState

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery

    from bot.db.models import UserDB

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(AccountState.actions, BackFactory.filter(F.to == "accounts"))
async def back_default(
    query: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    user: UserDB,
) -> None:
    await show_bots(query, session)
