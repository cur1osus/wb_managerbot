from aiogram import Router

from . import create_deep_link, reg_account, start

router = Router()
router.include_router(start.router)
router.include_router(reg_account.router)
router.include_router(create_deep_link.router)
