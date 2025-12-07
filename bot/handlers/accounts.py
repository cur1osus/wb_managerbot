from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from aiogram import F, Router
from sqlalchemy import select

from bot.db.models import Account
from bot.keyboards.inline import (
    ik_available_accounts,
    ik_back,
)
from bot.utils import fn

if TYPE_CHECKING:
    from aiogram.types import CallbackQuery
    from sqlalchemy.ext.asyncio import AsyncSession

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "accounts")
async def show_bots(
    query: CallbackQuery,
    session: AsyncSession,
) -> None:
    accounts = (await session.scalars(select(Account))).all()
    if not accounts:
        await query.message.edit_text(
            text="Аккаунтов еще нет", reply_markup=await ik_back()
        )
        return
    for account in accounts:
        account.is_connected = await fn.Manager.bot_run(account.phone)
    await session.commit()
    await query.message.edit_text(
        "Аккаунты",
        reply_markup=await ik_available_accounts(list(accounts)),
    )
