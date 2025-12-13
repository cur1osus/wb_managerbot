from aiogram import Router

from . import accounts, add_account, cmds, global_back
from .account_actions import router as account_actions_router

router = Router()
router.include_router(cmds.router)

router.include_router(accounts.router)
router.include_router(add_account.router)
router.include_router(account_actions_router)
router.include_router(global_back.router)
