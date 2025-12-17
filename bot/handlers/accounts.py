from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from aiogram import F, Router
from sqlalchemy import select

from bot.db.models import Account, AccountFolder
from bot.keyboards.factories import FolderDeleteFactory, FolderFactory
from bot.keyboards.inline import (
    ik_available_accounts,
    ik_back,
    ik_folder_list,
)
from bot.states import FolderState
from bot.utils import fn

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery, Message
    from sqlalchemy.ext.asyncio import AsyncSession

    from bot.db.models import UserDB

router = Router()
logger = logging.getLogger(__name__)

FOLDER_BACK_PREFIX = "accounts_folder_"
LIST_BACK_TO = "folders"


async def _ensure_admin(
    query: CallbackQuery,
    user: UserDB | None,
) -> bool:
    if not user or not user.is_admin:
        await query.answer(text="Недостаточно прав", show_alert=True)
        return False
    return True


async def _show_accounts(
    query: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    user: UserDB,
    *,
    folder_id: int | None,
    title: str,
    empty_text: str,
    actions_back_to: str,
    add_to_folder_id: int | None = None,
) -> None:
    stmt = select(Account).where(Account.user_id == user.id)
    if folder_id == 0:
        stmt = stmt.where(Account.folder_id.is_(None))
    elif folder_id is not None:
        stmt = stmt.where(Account.folder_id == folder_id)

    accounts = (await session.scalars(stmt)).all()
    await state.update_data(accounts_back_to=actions_back_to)

    if not accounts:
        delete_folder_id = (
            folder_id if folder_id is not None and folder_id != 0 else None
        )
        await query.message.edit_text(
            text=empty_text,
            reply_markup=await ik_available_accounts(
                [],
                back_to=LIST_BACK_TO,
                add_to_folder_id=add_to_folder_id,
                delete_folder_id=delete_folder_id,
            ),
        )
        return

    for account in accounts:
        account.is_connected = await fn.Manager.bot_run(account.phone)
    await session.commit()

    await query.message.edit_text(
        title,
        reply_markup=await ik_available_accounts(
            list(accounts),
            back_to=LIST_BACK_TO,
            add_to_folder_id=add_to_folder_id,
        ),
    )


@router.callback_query(F.data == "accounts")
async def show_folders(
    query: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    user: UserDB | None,
) -> None:
    if not await _ensure_admin(query, user):
        return

    await fn.state_clear(state)
    folders = (
        await session.scalars(
            select(AccountFolder)
            .where(AccountFolder.user_id == user.id)
            .order_by(AccountFolder.name)
        )
    ).all()
    await query.message.edit_text(
        text="Папки",
        reply_markup=await ik_folder_list(list(folders)),
    )


@router.callback_query(F.data == "accounts_all")
async def show_all_accounts(
    query: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    user: UserDB | None,
) -> None:
    if not await _ensure_admin(query, user):
        return

    await _show_accounts(
        query,
        session,
        state,
        user,
        folder_id=None,
        title="Все аккаунты",
        empty_text="Аккаунтов еще нет",
        actions_back_to="accounts",
    )


@router.callback_query(F.data == "accounts_no_folder")
async def show_no_folder_accounts(
    query: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    user: UserDB | None,
) -> None:
    if not await _ensure_admin(query, user):
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


@router.callback_query(FolderFactory.filter())
async def show_folder_accounts(
    query: CallbackQuery,
    callback_data: FolderFactory,
    session: AsyncSession,
    state: FSMContext,
    user: UserDB | None,
) -> None:
    if not await _ensure_admin(query, user):
        return
    await show_folder_accounts_by_id(
        query,
        session,
        state,
        user,
        folder_id=callback_data.id,
    )


async def show_folder_accounts_by_id(
    query: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    user: UserDB,
    *,
    folder_id: int,
) -> None:
    folder = await session.scalar(
        select(AccountFolder).where(
            AccountFolder.id == folder_id,
            AccountFolder.user_id == user.id,
        )
    )
    if not folder:
        await query.answer(text="Папка не найдена", show_alert=True)
        return

    await _show_accounts(
        query,
        session,
        state,
        user,
        folder_id=folder.id,
        title=f"Папка: {folder.name}",
        empty_text="В папке пока нет аккаунтов",
        actions_back_to=f"{FOLDER_BACK_PREFIX}{folder.id}",
        add_to_folder_id=folder.id,
    )


@router.callback_query(FolderDeleteFactory.filter())
async def delete_folder(
    query: CallbackQuery,
    callback_data: FolderDeleteFactory,
    session: AsyncSession,
    state: FSMContext,
    user: UserDB | None,
) -> None:
    if not await _ensure_admin(query, user):
        return

    folder = await session.scalar(
        select(AccountFolder).where(
            AccountFolder.id == callback_data.id,
            AccountFolder.user_id == user.id,
        )
    )
    if not folder:
        await query.answer(text="Папка не найдена", show_alert=True)
        return

    has_accounts = await session.scalar(
        select(Account.id).where(Account.folder_id == folder.id).limit(1)
    )
    if has_accounts:
        await query.answer(text="В папке есть аккаунты", show_alert=True)
        return

    await session.delete(folder)
    await session.commit()
    await fn.state_clear(state)

    folders = (
        await session.scalars(
            select(AccountFolder)
            .where(AccountFolder.user_id == user.id)
            .order_by(AccountFolder.name)
        )
    ).all()
    await query.message.edit_text(
        text="Папка удалена",
        reply_markup=await ik_folder_list(list(folders)),
    )


@router.callback_query(F.data == "create_folder")
async def start_create_folder(
    query: CallbackQuery,
    state: FSMContext,
    user: UserDB | None,
) -> None:
    if not await _ensure_admin(query, user):
        return

    await state.set_state(FolderState.enter_name)
    await query.message.edit_text(
        text="Введите название папки",
        reply_markup=await ik_back(back_to=LIST_BACK_TO),
    )


@router.message(FolderState.enter_name)
async def create_folder(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: UserDB | None,
) -> None:
    if not user or not user.is_admin:
        return

    name = (message.text or "").strip()
    if not name:
        await message.answer("Название папки не может быть пустым")
        return
    if len(name) > 100:
        await message.answer("Название папки слишком длинное (максимум 100)")
        return

    existing = await session.scalar(
        select(AccountFolder).where(
            AccountFolder.user_id == user.id,
            AccountFolder.name == name,
        )
    )
    if existing:
        await message.answer("Папка с таким названием уже существует")
        return

    session.add(AccountFolder(name=name, user_id=user.id))
    await session.commit()
    await fn.state_clear(state)

    folders = (
        await session.scalars(
            select(AccountFolder)
            .where(AccountFolder.user_id == user.id)
            .order_by(AccountFolder.name)
        )
    ).all()
    await message.answer(
        text="Папка создана",
        reply_markup=await ik_folder_list(list(folders)),
    )
