import logging
from typing import Final

logger = logging.getLogger(__name__)
minute: Final[int] = 60


def key_build(key: str) -> str:
    return f"post_manager:func:send_posts:{key}"


key_last_post_id = key_build("last_post_id")
