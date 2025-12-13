from typing import Final

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.db.models import Account
from bot.keyboards.factories import (
    AccountFactory,
    BackFactory,
    BatchSizeFactory,
    CancelFactory,
    HistoryFactory,
)

LIMIT_BUTTONS: Final[int] = 100
BACK_BUTTON_TEXT = "🔙"


async def ik_admin_panel() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="👥 Аккаунты", callback_data="accounts")
    builder.button(text="❇️ Добавить Аккаунт", callback_data="add_new_account")
    builder.adjust(1)
    return builder.as_markup()


async def ik_available_accounts(
    accounts: list[Account],
    back_to: str = "default",
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for account in accounts:
        builder.button(
            text=f"{'❇️' if account.is_connected else '⛔️'}{'🟢' if account.is_started else '🔴'} {account.phone} ({account.name or '?'})",
            callback_data=AccountFactory(id=account.id),
        )
    builder.button(text=BACK_BUTTON_TEXT, callback_data=BackFactory(to=back_to))
    builder.adjust(1)
    return builder.as_markup()


async def ik_back(back_to: str = "default") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=BACK_BUTTON_TEXT, callback_data=BackFactory(to=back_to))
    builder.adjust(1)
    return builder.as_markup()


async def ik_action_with_account(back_to: str = "accounts") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="⛓️‍💥 Отключить", callback_data="disconnect_account")
    builder.button(text="🟢 Старт", callback_data="start_account")
    builder.button(text="🔴 Стоп", callback_data="stop_account")
    builder.button(
        text="⚙️ Пропускная способность",
        callback_data="change_batch_size",
    )
    builder.button(text="🚮 Сбросить ники", callback_data="reset_nicks_account")
    builder.button(text="🌀 Загрузить ники", callback_data="load_nicks_account")
    builder.button(
        text="📥 Получить имена/юзернеймы",
        callback_data="create_job_get_names",
    )
    builder.button(
        text="📜 История отправок",
        callback_data=HistoryFactory(page=1),
    )
    builder.button(text=BACK_BUTTON_TEXT, callback_data=BackFactory(to=back_to))
    builder.adjust(1, 2, 1, 1, 1, 1, 1, 1)
    return builder.as_markup()


async def ik_connect_account(back_to: str = "default") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🗑 Удалить", callback_data="delete_account")
    builder.button(text="❇️ Подключить", callback_data="connect_account")
    builder.button(text=BACK_BUTTON_TEXT, callback_data=BackFactory(to=back_to))
    builder.adjust(1)
    return builder.as_markup()


async def ik_cancel_action(back_to: str = "default") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🚫 Отмена", callback_data=CancelFactory(to=back_to))
    builder.adjust(1)
    return builder.as_markup()


async def ik_choose_batch_size(current: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for value in range(1, 31):
        label = f"{'✅ ' if value == current else ''}{value}"
        builder.button(
            text=label,
            callback_data=BatchSizeFactory(value=value),
        )
    builder.button(text=BACK_BUTTON_TEXT, callback_data="batch_size_back")
    builder.adjust(5, 5, 5, 5, 5, 5, 1)
    return builder.as_markup()
