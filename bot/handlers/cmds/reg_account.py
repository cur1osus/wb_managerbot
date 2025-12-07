from __future__ import annotations

import asyncio
import logging
import os
from typing import TYPE_CHECKING

from aiogram import F, Router
from aiogram.filters.command import Command
from aiogram.fsm.state import any_state
from aiogram.types.reply_keyboard_remove import ReplyKeyboardRemove
from sqlalchemy import select

from bot.db.models import UserDB
from bot.keyboards.reply import rk_cancel
from bot.settings import se
from bot.states import UserAdminState
from bot.utils import fn

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import Message
    from sqlalchemy.ext.asyncio import AsyncSession

router = Router()
logger = logging.getLogger(__name__)


@router.message(any_state, F.text == "Отмена")
async def cancel_reg(
    message: Message,
    state: FSMContext,
) -> None:
    await fn.state_clear(state)
    msg = await message.answer(
        "Добавление бота отменено",
        reply_markup=ReplyKeyboardRemove(),
    )
    await fn.set_general_message(state, msg)


@router.message(Command(commands=["add_account"]))
async def add_new_bot(message: Message, state: FSMContext, user: UserDB) -> None:
    if not user.is_admin:
        await message.answer("Вы не администратор")
        return
    await message.answer("Введите api_id", reply_markup=await rk_cancel())
    await state.set_state(UserAdminState.enter_api_id)


@router.message(UserAdminState.enter_api_id)
async def enter_api_id(message: Message, state: FSMContext) -> None:
    await state.update_data(api_id=message.text)
    await message.answer("Введите api_hash", reply_markup=None)
    await state.set_state(UserAdminState.enter_api_hash)


@router.message(UserAdminState.enter_api_hash)
async def enter_api_hash(message: Message, state: FSMContext) -> None:
    await state.update_data(api_hash=message.text)
    await message.answer("Введите phone", reply_markup=None)
    await state.set_state(UserAdminState.enter_phone)


@router.message(UserAdminState.enter_phone)
async def enter_phone(message: Message, state: FSMContext) -> None:
    if not message.text:
        return

    os.makedirs(se.path_to_folder, exist_ok=True)

    await state.update_data(phone=message.text)

    data = await state.get_data()
    api_id = data.get("api_id")
    api_hash = data.get("api_hash")

    if not api_id or not api_hash:
        await message.answer(
            "Произошла ошибка, не обнаружено API ID или API HASH, нажмите 'Отмена' и попробуйте снова"
        )
        return

    relative_path = f"{se.path_to_folder}/{message.text}"
    path_session = os.path.abspath(f"{relative_path}.session")

    result = await fn.Telethon.send_code_via_telethon(
        message.text,
        int(api_id),
        api_hash,
        path_session,
    )

    if not result.success:
        t = str(result.message)
        await message.answer(t, reply_markup=None)
        return

    phone_code_hash = result.message
    await state.update_data(
        phone_code_hash=phone_code_hash,
        path_session=path_session,
    )
    await message.answer("Введите code", reply_markup=None)
    await state.set_state(UserAdminState.enter_code)


@router.message(UserAdminState.enter_code)
async def enter_code(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if not message.text:
        return

    data = await state.get_data()

    is_password = data.get("is_password", False)
    code = data.get("code") if is_password else message.text
    password = message.text if is_password else None

    api_id = data["api_id"]
    api_hash = data["api_hash"]
    phone = data["phone"]
    phone_code_hash = data["phone_code_hash"]
    path_session = data["path_session"]

    r = await fn.Telethon.create_telethon_session(
        phone,
        code,  # pyright: ignore
        int(api_id),
        api_hash,
        phone_code_hash,
        password,
        path_session,
    )
    if r.message == "password_required":
        await message.answer("Введите пароль", reply_markup=None)
        await state.update_data(code=code, is_password=True)
        return
    if not r.success:
        t = str(r.message)
        await message.answer(t, reply_markup=None)
        return

    account_exist = await session.scalar(
        select(Account).where(Account.api_hash == api_hash)
    )
    if account_exist:
        await message.answer(
            "Бот уже зарегистрирован",
            reply_markup=ReplyKeyboardRemove(),
        )
        await fn.state_clear(state)
        return

    a = Account(
        api_id=int(api_id),
        api_hash=api_hash,
        phone=phone,
        path_session=path_session,
        is_connected=True,
    )
    session.add(a)
    await session.commit()

    asyncio.create_task(fn.Manager.start_bot(phone, path_session, api_id, api_hash))

    await fn.state_clear(state)

    await message.answer("Бот подключен и запущен", reply_markup=ReplyKeyboardRemove())
