from __future__ import annotations

import logging
from functools import partial
from typing import TYPE_CHECKING

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy import and_, delete

from bot.db.models import Username
from bot.keyboards.factories import CancelFactory
from bot.keyboards.inline import ik_action_with_account, ik_cancel_action
from bot.states import AccountState
from bot.utils import fn

from .common import account_from_state, alert_notifier

router = Router()
logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery
    from sqlalchemy.ext.asyncio import AsyncSession

    from bot.db.models import UserDB


@router.callback_query(AccountState.actions, F.data == "load_nicks_account")
async def load_nicks_account(
    query: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: UserDB,
) -> None:
    account = await account_from_state(state, session, alert_notifier(query), user)
    if not account:
        return

    await query.message.edit_text(
        text="Отправьте никнеймы",
        reply_markup=await ik_cancel_action(back_to="cancel_load_nicks"),
    )
    await state.set_state(AccountState.load_nicks)


@router.callback_query(
    AccountState.load_nicks,
    CancelFactory.filter(F.to == "cancel_load_nicks"),
)
async def cancel_load_nicks(
    query: CallbackQuery,
    state: FSMContext,
    user: UserDB,
) -> None:
    await query.message.edit_text(
        text="Загрузка никнеймов отменена",
        reply_markup=await ik_action_with_account(),
    )
    await state.set_state(AccountState.actions)


@router.message(AccountState.load_nicks)
async def catch_load_nicks(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: UserDB,
) -> None:
    account = await account_from_state(
        state,
        session,
        partial(message.answer),
        user,
    )
    if not account:
        return

    usernames, line_not_handled = await fn.parse_users_from_text(
        message.text if message.text else ""
    )
    if not usernames:
        await message.answer(text="Текст не корректный")
        return

    for n in usernames:
        session.add(
            Username(
                username=n.username,
                item_name=n.item_name,
                account_id=account.id,
            )
        )

    await session.commit()
    await message.answer(text=f"{len(usernames)} ч. успешно добавлены в очередь")
    if line_not_handled:
        await message.answer(
            text=f"Не были распознаны эти строки:\n\n{'\n'.join(line_not_handled)}"
        )
    await state.set_state(AccountState.actions)
    await message.answer(
        text="Действия с аккаунтом",
        reply_markup=await ik_action_with_account(),
    )


@router.callback_query(AccountState.actions, F.data == "reset_nicks_account")
async def reset_nicks_account(
    query: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: UserDB,
) -> None:
    account = await account_from_state(state, session, alert_notifier(query), user)
    if not account:
        return

    await session.execute(
        delete(Username).where(
            and_(
                Username.account_id == account.id,
                Username.sended.is_(False),
            )
        )
    )
    await session.commit()
    await query.answer(text="Очередь успешно отчищена!", show_alert=True)
