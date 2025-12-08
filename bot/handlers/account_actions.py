from __future__ import annotations

import asyncio
import logging
from functools import partial
from typing import TYPE_CHECKING, Awaitable, Callable, Final

from aiogram import F, Router
from aiogram.types import InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import and_, delete, func, select

from bot.db.models import Account, Username
from bot.keyboards.factories import AccountFactory, CancelFactory, HistoryFactory
from bot.keyboards.inline import (
    ik_action_with_account,
    ik_admin_panel,
    ik_cancel_action,
    ik_connect_account,
)
from bot.states import AccountState, UserAdminState
from bot.utils import fn

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery
    from sqlalchemy.ext.asyncio import AsyncSession

router = Router()
logger = logging.getLogger(__name__)
Notifier = Callable[[str], Awaitable[None]]
HISTORY_PAGE_SIZE: Final[int] = 10
MAX_TG_MESSAGE_LENGTH: Final[int] = 4096


def _alert(query: CallbackQuery) -> Notifier:
    return partial(query.answer, show_alert=True)


async def _account_from_state(
    state: FSMContext,
    session: AsyncSession,
    notify: Notifier,
) -> Account | None:
    data = await state.get_data()
    account_id: int | None = data.get("account_id")
    if not account_id:
        await notify("Ошибка: account_id пустой в state")
        return None

    account = await session.get(Account, account_id)
    if not account:
        await notify("Ошибка: account не найден в базе данных")
        return None

    return account


def _format_username_item(username: Username) -> str:
    mention = username.username
    if mention and not mention.startswith("@"):
        mention = f"@{mention}"

    status = "✅" if username.sended else "⏳"
    item = f" — {username.item_name}" if username.item_name else ""
    return f"{mention}{item} ({status})"


def _history_text(
    account: Account,
    usernames: list[Username],
    page: int,
    total_pages: int,
    total: int,
) -> str:
    header = account.name or account.phone
    rows = [
        f"История отправок для {header}",
        f"Всего получателей: {total}",
        f"Страница {page}/{total_pages}",
        "",
    ]
    start_index = 1 + (page - 1) * HISTORY_PAGE_SIZE
    for index, username in enumerate(usernames, start=start_index):
        rows.append(f"{index}. {_format_username_item(username)}")

    if not usernames:
        rows.append("Пока нет ни одной отправки или очереди.")

    text = "\n".join(rows)
    if len(text) > MAX_TG_MESSAGE_LENGTH:
        text = text[: MAX_TG_MESSAGE_LENGTH - 3] + "..."
    return text


def _history_keyboard(page: int, total_pages: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    adjust = []
    if total_pages > 1 and page > 1:
        builder.button(text="⬅️", callback_data=HistoryFactory(page=page - 1))
        adjust.append(1)
    if total_pages > 1 and page < total_pages:
        builder.button(text="➡️", callback_data=HistoryFactory(page=page + 1))
        if adjust:
            adjust[0] += 1
        else:
            adjust.append(1)
    builder.button(text="🔙 К действиям", callback_data="history_back")
    adjust.append(1)
    builder.adjust(*adjust)
    return builder.as_markup()


@router.callback_query(AccountFactory.filter())
async def manage_account(
    query: CallbackQuery,
    callback_data: AccountFactory,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    account_id = callback_data.id
    account = await session.get(Account, account_id)
    if not account:
        await query.answer(text="Аккаунт не найден", show_alert=True)
        return

    markup = (
        await ik_action_with_account()
        if account.is_connected
        else await ik_connect_account()
    )
    await query.message.edit_text("Выберите действие", reply_markup=markup)
    await state.set_state(AccountState.actions)
    await state.update_data(account_id=account_id)


@router.callback_query(AccountState.actions, F.data == "connect_account")
async def connect_account(
    query: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    account = await _account_from_state(state, session, _alert(query))
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
            reply_markup=await ik_action_with_account(),
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
) -> None:
    account = await _account_from_state(state, session, _alert(query))
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
) -> None:
    account = await _account_from_state(state, session, _alert(query))
    if not account:
        return

    await fn.Manager.stop_bot(phone=account.phone, delete_session=True)

    await session.delete(account)
    await session.commit()

    await fn.state_clear(state)
    await query.message.edit_text("Бот удален", reply_markup=await ik_admin_panel())


@router.callback_query(AccountState.actions, F.data == "start_account")
async def start_account(
    query: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    account = await _account_from_state(state, session, _alert(query))
    if not account:
        return

    account.is_started = True
    await session.commit()

    await query.message.edit_text(
        f"Бот {account.name} [{account.phone}] запущен",
        reply_markup=await ik_action_with_account(),
    )


@router.callback_query(AccountState.actions, F.data == "stop_account")
async def stop_account(
    query: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    account = await _account_from_state(state, session, _alert(query))
    if not account:
        return

    account.is_started = False
    await session.commit()

    await query.message.edit_text(
        f"Бот {account.name} [{account.phone}] остановлен",
        reply_markup=await ik_action_with_account(),
    )


@router.callback_query(AccountState.actions, HistoryFactory.filter())
async def history_usernames(
    query: CallbackQuery,
    callback_data: HistoryFactory,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    account = await _account_from_state(state, session, _alert(query))
    if not account:
        return

    total_stmt = (
        select(func.count())
        .select_from(Username)
        .where(Username.account_id == account.id)
    )
    total = (await session.execute(total_stmt)).scalar_one()
    total_pages = max(1, (total + HISTORY_PAGE_SIZE - 1) // HISTORY_PAGE_SIZE)
    page = max(1, min(callback_data.page, total_pages))

    stmt = (
        select(Username)
        .where(Username.account_id == account.id)
        .order_by(Username.id.desc())
        .offset((page - 1) * HISTORY_PAGE_SIZE)
        .limit(HISTORY_PAGE_SIZE)
    )
    usernames = (await session.execute(stmt)).scalars().all()

    text = _history_text(account, usernames, page, total_pages, total)
    await query.message.edit_text(
        text=text,
        reply_markup=_history_keyboard(page, total_pages),
    )


@router.callback_query(AccountState.actions, F.data == "history_back")
async def history_back_to_actions(
    query: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    account = await _account_from_state(state, session, _alert(query))
    if not account:
        return

    await query.message.edit_text(
        text="Действия с аккаунтом",
        reply_markup=await ik_action_with_account(),
    )


@router.callback_query(AccountState.actions, F.data == "load_nicks_account")
async def load_nicks_account(
    query: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    account = await _account_from_state(state, session, _alert(query))
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
) -> None:
    account = await _account_from_state(state, session, partial(message.answer))
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
) -> None:
    account = await _account_from_state(state, session, _alert(query))
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
