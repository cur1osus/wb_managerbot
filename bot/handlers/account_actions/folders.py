from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from aiogram import F, Router
from sqlalchemy import select

from bot.db.models import AccountFolder
from bot.keyboards.factories import BackFactory, FolderMoveFactory
from bot.keyboards.inline import ik_action_with_account, ik_move_account_folder
from bot.states import AccountState

from ..accounts import _show_accounts
from .common import account_back_to, account_from_state, alert_notifier

router = Router()
logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery
    from sqlalchemy.ext.asyncio import AsyncSession

    from bot.db.models import UserDB


@router.callback_query(AccountState.actions, F.data == "move_account_folder")
async def move_account_folder(
    query: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: UserDB,
) -> None:
    account = await account_from_state(state, session, alert_notifier(query), user)
    if not account:
        return

    folders = (
        await session.scalars(
            select(AccountFolder)
            .where(AccountFolder.user_id == user.id)
            .order_by(AccountFolder.id)
        )
    ).all()

    await query.message.edit_text(
        text="Выберите папку для аккаунта",
        reply_markup=await ik_move_account_folder(list(folders)),
    )


@router.callback_query(
    AccountState.actions, BackFactory.filter(F.to == "account_actions")
)
async def move_account_folder_back(
    query: CallbackQuery,
    state: FSMContext,
) -> None:
    await query.message.edit_text(
        text="Действия с аккаунтом",
        reply_markup=await ik_action_with_account(back_to=await account_back_to(state)),
    )


@router.callback_query(AccountState.actions, FolderMoveFactory.filter())
async def set_account_folder(
    query: CallbackQuery,
    callback_data: FolderMoveFactory,
    state: FSMContext,
    session: AsyncSession,
    user: UserDB,
) -> None:
    account = await account_from_state(state, session, alert_notifier(query), user)
    if not account:
        return

    old_folder = await account.awaitable_attrs.folder

    async def _show_old_folder() -> None:
        if old_folder:
            await _show_accounts(
                query,
                session,
                state,
                user,
                folder_id=old_folder.id,
                title=old_folder.name,
                empty_text="Аккаунтов еще нет",
                actions_back_to=f"accounts_folder_{old_folder.id}",
            )
            return
        await _show_accounts(
            query,
            session,
            state,
            user,
            folder_id=0,
            title="Аккаунты без папки",
            empty_text="Аккаунтов без папки еще нет",
            actions_back_to="accounts_no_folder",
        )

    folder_id = callback_data.id
    if folder_id == 0:
        account.folder_id = None
        await session.commit()
        await query.answer(text="Аккаунт перемещен", show_alert=True)
        await _show_old_folder()
        return

    folder = await session.scalar(
        select(AccountFolder).where(
            AccountFolder.id == folder_id,
            AccountFolder.user_id == user.id,
        )
    )
    if not folder:
        await query.answer(text="Папка не найдена", show_alert=True)
        return

    account.folder_id = folder.id
    await session.commit()
    await query.answer(text="Аккаунт перемещен", show_alert=True)
    await _show_old_folder()
