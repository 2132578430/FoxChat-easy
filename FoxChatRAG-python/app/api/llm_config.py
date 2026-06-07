"""
LLM 配置 API 路由

端点:
- POST /llm/testConnection: 测试 LLM 连接（被 Java Feign 调用）

注意：
  LLM 配置的 CRUD（增删改查）由 Java 端 LlmConfigController + LlmConfigServiceImpl 直接操作 MySQL，
  Python 端不再暴露重复的 CRUD 端点。
  仅保留 testConnection，因为只有 Python 安装了 litellm 可以真正发起 API 连通性测试。
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.mysql_client import get_db
from app.schemas.M import M
from loguru import logger

llm_config_router = APIRouter(prefix="/llm", tags=["llm-config"])


@llm_config_router.post("/testConnection")
async def test_connection(config_data: dict, db: AsyncSession = Depends(get_db)):
    """
    测试 LLM 连接（被 Java Feign ChatClient.testConnection 调用）

    Args:
        config_data: 配置数据 (model_name, api_key, base_url)
        db: 数据库会话

    Returns:
        测试结果 (成功/失败, 错误消息)
    """
    from app.service.llm_config_service import test_llm_connection

    logger.info(f"【API】测试连接: model={config_data.get('model_name')}")

    result = await test_llm_connection(
        model_name=config_data["model_name"],
        api_key=config_data["api_key"],
        base_url=config_data["base_url"]
    )

    return M.get_msg(result)