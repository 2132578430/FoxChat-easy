"""
LLM 配置 API 路由

端点:
- POST /llm/config/batch: 批量保存配置 (5 个场景)
- GET /llm/config/{llm_id}: 获取所有配置
- DELETE /llm/config/{llm_id}/{scenario}: 删除配置
- POST /llm/testConnection: 测试连接
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.mysql_client import get_db
from app.service.llm_config_service import (
    get_llm_configs_batch,
    save_llm_configs_batch,
    delete_llm_config,
    validate_config_count,
    get_missing_scenarios,
)
from app.schemas.M import M
from loguru import logger

llm_config_router = APIRouter(prefix="/llm", tags=["llm-config"])


@llm_config_router.post("/config/batch")
async def save_configs_batch(
    llm_id: str,
    configs: list[dict],
    db: AsyncSession = Depends(get_db)
):
    """
    批量保存 5 个场景配置

    Args:
        llm_id: AI 朋友 ID
        configs: 配置列表 (每个包含 scenario 字段)
        db: 数据库会话

    Returns:
        成功消息
    """
    logger.info(f"【API】批量保存配置: llm_id={llm_id}, count={len(configs)}")

    config_ids = await save_llm_configs_batch(llm_id, configs, db)

    return M.get_msg({"config_ids": config_ids, "message": "配置保存成功"})


@llm_config_router.get("/config/{llm_id}")
async def get_configs(llm_id: str, db: AsyncSession = Depends(get_db)):
    """
    获取所有配置

    Args:
        llm_id: AI 朋友 ID
        db: 数据库会话

    Returns:
        配置字典
    """
    logger.info(f"【API】获取配置: llm_id={llm_id}")

    config_map = await get_llm_configs_batch(llm_id, db)

    return M.get_msg({"configs": config_map})


@llm_config_router.delete("/config/{llm_id}/{scenario}")
async def delete_config(
    llm_id: str,
    scenario: str,
    db: AsyncSession = Depends(get_db)
):
    """
    删除配置

    Args:
        llm_id: AI 朋友 ID
        scenario: 场景名称
        db: 数据库会话

    Returns:
        成功消息
    """
    logger.info(f"【API】删除配置: llm_id={llm_id}, scenario={scenario}")

    success = await delete_llm_config(llm_id, scenario, db)

    if success:
        return M.get_msg({"message": "配置删除成功"})
    else:
        return M.get_msg({"message": "配置不存在"})


@llm_config_router.get("/validate/{llm_id}")
async def validate_configs(llm_id: str, db: AsyncSession = Depends(get_db)):
    """
    验证配置完整性

    Args:
        llm_id: AI 朋友 ID
        db: 数据库会话

    Returns:
        验证结果 (是否完整, 缺失场景列表)
    """
    logger.info(f"【API】验证配置: llm_id={llm_id}")

    is_valid = await validate_config_count(llm_id, db)
    missing_scenarios = await get_missing_scenarios(llm_id, db)

    return M.get_msg({
        "is_valid": is_valid,
        "missing_scenarios": missing_scenarios
    })


@llm_config_router.post("/testConnection")
async def test_connection(config_data: dict, db: AsyncSession = Depends(get_db)):
    """
    测试连接 (调用 LiteLLM 验证配置)

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