import os
from functools import lru_cache

from loguru import logger

DIR_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "")


class PromptManager:
    @classmethod
    @lru_cache(maxsize=24)
    def _get_prompt_sync(cls, file_name: str) -> str | None:
        if not file_name.endswith((".txt", ".md")):
            file_name += ".md"

        file_path = os.path.join(DIR_PATH, file_name)

        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()

        logger.error(f"导入提示词文件错误：文件路径不存在:{file_path}")
        return None

    @classmethod
    async def get_prompt(cls, file_name: str) -> str | None:
        return cls._get_prompt_sync(file_name)

    @classmethod
    async def get_soul(cls, soul_name: str = "soul") -> str | None:
        return await cls.get_prompt(soul_name)
