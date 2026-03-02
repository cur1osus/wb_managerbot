from typing import Final

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.db.models import Account, AccountFolder
from bot.keyboards.factories import (
    AccountFactory,
    AccountTextFactory,
    BackFactory,
    BatchSizeFactory,
    CancelFactory,
    FolderAddFactory,
    FolderDeleteFactory,
    FolderFactory,
    FolderMoveFactory,
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
    add_to_folder_id: int | None = None,
    delete_folder_id: int | None = None,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if add_to_folder_id is not None:
        builder.button(
            text="➕ Добавить аккаунт",
            callback_data=FolderAddFactory(id=add_to_folder_id),
        )
    if delete_folder_id is not None:
        builder.button(
            text="🗑 Удалить папку",
            callback_data=FolderDeleteFactory(id=delete_folder_id),
        )
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
        text="⚙️ Пропускная",
        callback_data="change_batch_size",
    )
    builder.button(text="🌀 Загрузить ники", callback_data="load_nicks_account")
    builder.button(text="🚮 Сбросить ники", callback_data="reset_nicks_account")
    builder.button(text="📁 Переместить", callback_data="move_account_folder")
    builder.button(text="📝 Тексты", callback_data="edit_account_texts")
    builder.button(
        text="📜 История",
        callback_data=HistoryFactory(page=1),
    )
    builder.button(
        text="📥 Получить имена/юзернеймы",
        callback_data="create_job_get_names",
    )
    builder.button(text=BACK_BUTTON_TEXT, callback_data=BackFactory(to=back_to))
    builder.adjust(1, 2, 2, 2, 2, 1)
    return builder.as_markup()


async def ik_connect_account(back_to: str = "default") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🗑 Удалить", callback_data="delete_account")
    builder.button(text="❇️ Подключить", callback_data="connect_account")
    builder.button(text="📁 Переместить в папку", callback_data="move_account_folder")
    # builder.button(text="📝 Тексты", callback_data="edit_account_texts")
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


async def ik_folder_list(
    folders: list[AccountFolder],
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Создать папку", callback_data="create_folder")
    builder.button(text="📦 Все аккаунты", callback_data="accounts_all")
    # builder.button(text="📂 Без папки", callback_data="accounts_no_folder")
    for folder in folders:
        builder.button(
            text=f"📁 {folder.name}",
            callback_data=FolderFactory(id=folder.id),
        )
    # builder.button(text=BACK_BUTTON_TEXT, callback_data=BackFactory(to="default"))
    builder.adjust(1)
    return builder.as_markup()


async def ik_move_account_folder(
    folders: list[AccountFolder],
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="📂 Без папки",
        callback_data=FolderMoveFactory(id=0),
    )
    for folder in folders:
        builder.button(
            text=f"📁 {folder.name}",
            callback_data=FolderMoveFactory(id=folder.id),
        )
    builder.button(
        text=BACK_BUTTON_TEXT, callback_data=BackFactory(to="account_actions")
    )
    builder.adjust(1)
    return builder.as_markup()


async def ik_account_texts_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Приветствия утром",
        callback_data=AccountTextFactory(field="greetings_morning"),
    )
    builder.button(
        text="П. днем",
        callback_data=AccountTextFactory(field="greetings_day"),
    )
    builder.button(
        text="П. вечером",
        callback_data=AccountTextFactory(field="greetings_evening"),
    )
    builder.button(
        text="П. ночью",
        callback_data=AccountTextFactory(field="greetings_night"),
    )
    builder.button(
        text="П. в любое время",
        callback_data=AccountTextFactory(field="greetings_anytime"),
    )
    builder.button(
        text="Вводные",
        callback_data=AccountTextFactory(field="lead_in_texts"),
    )
    builder.button(
        text="Уточняющие",
        callback_data=AccountTextFactory(field="clarifying_texts"),
    )
    builder.button(
        text="Раз. диалог",
        callback_data=AccountTextFactory(field="follow_up_texts"),
    )
    builder.button(
        text="Закрывающие",
        callback_data=AccountTextFactory(field="closing_texts"),
    )
    builder.button(text="🧪 Тест текстов", callback_data="test_account_texts")
    builder.button(
        text=BACK_BUTTON_TEXT, callback_data=BackFactory(to="account_actions")
    )
    builder.adjust(1, 2, 2, 2, 2, 1, 1)
    return builder.as_markup()


async def ik_account_texts_category_actions() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить", callback_data="account_texts_add")
    builder.button(text="🗑 Удалить", callback_data="account_texts_delete")
    builder.button(
        text=BACK_BUTTON_TEXT, callback_data=BackFactory(to="account_texts_menu")
    )
    builder.adjust(1)
    return builder.as_markup()


async def ik_confirm_delete_sessions() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, удалить", callback_data="confirm_delete_sessions")
    builder.button(text="❌ Отмена", callback_data="cancel_delete_sessions")
    builder.adjust(1)
    return builder.as_markup()
