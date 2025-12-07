from aiogram.filters.callback_data import CallbackData


class BackFactory(CallbackData, prefix="bk"):
    to: str


class AccountFactory(CallbackData, prefix="c"):
    id: int


class CancelFactory(CallbackData, prefix="cn"):
    to: str
