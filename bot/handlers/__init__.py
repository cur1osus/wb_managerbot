from aiogram import Router

from . import (
    account_actions,
    accounts,
    add_account,
    cmds,
    global_back,
)

router = Router()
router.include_router(cmds.router)

router.include_router(accounts.router)
router.include_router(add_account.router)
router.include_router(account_actions.router)
router.include_router(global_back.router)
