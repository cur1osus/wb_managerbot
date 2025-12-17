from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from aiogram import F, Router

from bot.keyboards.inline import (
    ik_action_with_account,
    ik_admin_panel,
)
from bot.states import AccountState, UserAdminState
from bot.utils import fn

from .common import account_back_to, account_from_state, alert_notifier

router = Router()
logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery
    from sqlalchemy.ext.asyncio import AsyncSession

    from bot.db.models import UserDB


@router.callback_query(AccountState.actions, F.data == "connect_account")
async def connect_account(
    query: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: UserDB,
) -> None:
    account = await account_from_state(state, session, alert_notifier(query), user)
    if not account:
        return

    await fn.Manager.start_bot(
        account.phone,
        account.path_session,
        account.api_id,
        account.api_hash,
    )
    await query.message.edit_text(
        "Пытаемся подключить Аккаунт с уже существующей сессией..."
    )

    await asyncio.sleep(2)
    if await fn.Manager.bot_run(account.phone):
        account.is_connected = True
        await session.commit()
        await query.message.edit_text(
            "Аккаунт успешно подключен!",
            reply_markup=await ik_action_with_account(
                back_to=await account_back_to(state)
            ),
        )
        return

    result = await fn.Telethon.send_code_via_telethon(
        account.phone,
        account.api_id,
        account.api_hash,
        account.path_session,
    )
    if result.success:
        await query.message.edit_text(
            "К сожалению, Аккаунт не смог подключиться по старой сессии, "
            "поэтому мы отправили код, как получите его отправьте мне",
        )
    else:
        await query.message.answer(f"Ошибка при отправке кода: {result.message}")
        return

    await state.update_data(
        api_id=account.api_id,
        api_hash=account.api_hash,
        phone=account.phone,
        phone_code_hash=result.message,
        path_session=account.path_session,
        save_account=False,
    )
    await state.set_state(UserAdminState.enter_code)


@router.callback_query(AccountState.actions, F.data == "disconnect_account")
async def disconnected_account(
    query: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: UserDB,
) -> None:
    account = await account_from_state(state, session, alert_notifier(query), user)
    if not account:
        return

    account.is_connected = False
    await session.commit()

    await fn.Manager.stop_bot(phone=account.phone)

    await fn.state_clear(state)
    await query.message.edit_text(
        "Аккаунт отключен", reply_markup=await ik_admin_panel()
    )


@router.callback_query(AccountState.actions, F.data == "delete_account")
async def delete_account(
    query: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: UserDB,
) -> None:
    account = await account_from_state(state, session, alert_notifier(query), user)
    if not account:
        return

    await fn.Manager.stop_bot(phone=account.phone, delete_session=True)

    await session.delete(account)
    await session.commit()

    await fn.state_clear(state)
    await query.message.edit_text("Бот удален", reply_markup=await ik_admin_panel())
