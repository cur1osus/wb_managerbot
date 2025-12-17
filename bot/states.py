from aiogram.fsm.state import State, StatesGroup


class UserAdminState(StatesGroup):
    enter_api_id = State()
    enter_api_hash = State()
    enter_phone = State()
    enter_code = State()
    enter_password = State()


class AccountState(StatesGroup):
    actions = State()
    load_nicks = State()


class FolderState(StatesGroup):
    enter_name = State()


class AccountTextsState(StatesGroup):
    choose_category = State()
    enter_text = State()
    enter_item_name = State()
    delete_text = State()
