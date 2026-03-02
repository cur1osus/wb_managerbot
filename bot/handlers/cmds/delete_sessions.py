from __future__ import annotations

import logging
import shutil
from typing import TYPE_CHECKING

from aiogram import F, Router
from aiogram.filters.command import Command
from aiogram.types import CallbackQuery
from aiogram.utils.markdown import hbold

from bot.keyboards.inline import ik_confirm_delete_sessions
from bot.settings import se
from bot.utils import fn

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import Message
    from bot.db.models import UserDB

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command(commands=["delete_sessions"]))
async def delete_sessions_cmd(message: Message, user: UserDB | None) -> None:
    if not user or not user.is_admin:
        await message.answer("У вас нет прав для выполнения этой команды")
        return

    folder_path = se.path_to_folder

    await message.answer(
        f"{hbold('Внимание!')}\n\n"
        f"Вы собираетесь удалить папку с сессиями:\n"
        f"{hbold(folder_path)}\n\n"
        f"Это действие нельзя отменить. Все сессии будут удалены.\n\n"
        f"Вы уверены?",
        reply_markup=await ik_confirm_delete_sessions(),
    )


@router.callback_query(F.data == "confirm_delete_sessions")
async def confirm_delete_sessions(
    callback: CallbackQuery, state: FSMContext, user: UserDB | None
) -> None:
    if not user or not user.is_admin:
        await callback.answer(
            "У вас нет прав для выполнения этой команды", show_alert=True
        )
        return

    folder_path = se.path_to_folder

    try:
        if shutil.os.path.exists(folder_path):
            shutil.rmtree(folder_path)
            logger.info(
                f"Папка {folder_path} успешно удалена пользователем {user.user_id}"
            )
            await callback.message.edit_text(
                f"{hbold('Успешно!')}\n\nПапка {hbold(folder_path)} удалена."
            )
        else:
            await callback.message.edit_text(
                f"{hbold('Информация')}\n\nПапка {hbold(folder_path)} не существует."
            )
    except Exception as e:
        logger.error(f"Ошибка при удалении папки {folder_path}: {e}")
        await callback.message.edit_text(
            f"{hbold('Ошибка!')}\n\nНе удалось удалить папку: {e}"
        )

    await fn.state_clear(state)
    await callback.answer()


@router.callback_query(F.data == "cancel_delete_sessions")
async def cancel_delete_sessions(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text(
        f"{hbold('Отменено')}\n\nУдаление папки с сессиями отменено."
    )
    await fn.state_clear(state)
    await callback.answer()
