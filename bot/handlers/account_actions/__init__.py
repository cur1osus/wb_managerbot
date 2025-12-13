from aiogram import Router

from .batch_size import router as batch_size_router
from .connection import router as connection_router
from .history import router as history_router
from .lifecycle import router as lifecycle_router
from .jobs import router as jobs_router
from .manage import router as manage_router
from .usernames import router as usernames_router

router = Router()
router.include_router(manage_router)
router.include_router(connection_router)
router.include_router(lifecycle_router)
router.include_router(batch_size_router)
router.include_router(history_router)
router.include_router(usernames_router)
router.include_router(jobs_router)
