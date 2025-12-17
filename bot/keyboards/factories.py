from aiogram.filters.callback_data import CallbackData


class BackFactory(CallbackData, prefix="bk"):
    to: str


class AccountFactory(CallbackData, prefix="c"):
    id: int


class CancelFactory(CallbackData, prefix="cn"):
    to: str


class HistoryFactory(CallbackData, prefix="hst"):
    page: int


class BatchSizeFactory(CallbackData, prefix="bs"):
    value: int


class FolderFactory(CallbackData, prefix="fld"):
    id: int


class FolderMoveFactory(CallbackData, prefix="fmd"):
    id: int


class FolderAddFactory(CallbackData, prefix="fadd"):
    id: int


class AccountTextFactory(CallbackData, prefix="txt"):
    field: str
