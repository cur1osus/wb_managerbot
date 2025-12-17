from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from aiogram import F, Router
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.accounts import (
    show_all_accounts,
    show_folders,
    show_folder_accounts_by_id,
    show_no_folder_accounts,
)
from bot.keyboards.factories import BackFactory
from bot.keyboards.inline import ik_admin_panel
from bot.states import AccountState
from bot.utils import fn

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery

    from bot.db.models import UserDB

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(BackFactory.filter(F.to == "default"))
async def back_default(
    query: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    user: UserDB,
) -> None:
    await fn.state_clear(state)
    await query.message.edit_text(
        text="Главный экран",
        reply_markup=await ik_admin_panel(),
    )


@router.callback_query(AccountState.actions, BackFactory.filter(F.to == "accounts"))
async def back_accounts(
    query: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    user: UserDB,
) -> None:
    await show_all_accounts(query, session, state, user)


@router.callback_query(BackFactory.filter(F.to == "folders"))
async def back_folders(
    query: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    user: UserDB,
) -> None:
    await show_folders(query, session, state, user)


@router.callback_query(
    AccountState.actions, BackFactory.filter(F.to == "accounts_no_folder")
)
async def back_accounts_no_folder(
    query: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    user: UserDB,
) -> None:
    await show_no_folder_accounts(query, session, state, user)


@router.callback_query(
    AccountState.actions,
    BackFactory.filter(F.to.startswith("accounts_folder_")),
)
async def back_accounts_folder(
    query: CallbackQuery,
    callback_data: BackFactory,
    session: AsyncSession,
    state: FSMContext,
    user: UserDB,
) -> None:
    folder_id_str = callback_data.to.replace("accounts_folder_", "", 1)
    if not folder_id_str.isdigit():
        await query.answer(text="Некорректный идентификатор папки", show_alert=True)
        return
    await show_folder_accounts_by_id(
        query,
        session,
        state,
        user,
        folder_id=int(folder_id_str),
    )
