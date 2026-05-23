"""清理 role_current_state 键中的错误数据"""

import json
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger

from app.core.db.redis_client import redis_client
from app.common.constant.LLMChatConstant import build_memory_key, LLMChatConstant
from app.service.chat.state_manager import _create_default_state_dict, _json_set

# 配置日志
logger.remove()
logger.add(sys.stderr, level="INFO")


def cleanup_malformed_current_state(user_id: str, llm_id: str) -> dict:
    """
    清理 role_current_state 键中的错误数据

    Args:
        user_id: 用户 ID
        llm_id: 模型 ID

    Returns:
        清理结果信息
    """
    key = build_memory_key(LLMChatConstant.ROLE_CURRENT_STATE, user_id, llm_id)

    result = {
        "key": key,
        "action": None,
        "old_data_type": None,
        "old_data_sample": None,
        "new_data": None,
    }

    # 1. 检查现有数据
    try:
        json_client = redis_client.json()
        existing_data = json_client.get(key)

        if not existing_data:
            result["action"] = "no_data"
            result["message"] = "键不存在，无需清理"
            logger.info(f"键不存在: {key}")
            return result

        # 2. 判断数据类型
        if isinstance(existing_data, list):
            result["old_data_type"] = "list"
            result["old_data_sample"] = existing_data[:2] if len(existing_data) > 0 else []
            result["action"] = "deleted_and_reinitialized"

            logger.warning(
                f"发现错误数据格式: {key}\n"
                f"  类型: list (应为 dict)\n"
                f"  样本: {existing_data[:2]}"
            )

            # 3. 删除错误数据
            redis_client.delete(key)
            logger.info(f"已删除错误数据: {key}")

            # 4. 初始化正确的 CurrentState dict
            default_state = _create_default_state_dict()
            _json_set(key, '$', default_state)
            result["new_data"] = default_state

            logger.info(
                f"已初始化正确数据: {key}\n"
                f"  emotion: {default_state['emotion']['value']}\n"
                f"  relation_state: {default_state['relation_state']['value']}"
            )

        elif isinstance(existing_data, dict):
            # 检查是否为 CurrentState 格式
            expected_fields = {"emotion", "relation_state", "current_focus", "unfinished_items", "interaction_mode"}
            actual_fields = set(existing_data.keys())

            if expected_fields.issubset(actual_fields):
                result["old_data_type"] = "dict (correct)"
                result["action"] = "no_change_needed"
                result["message"] = "数据格式正确，无需清理"
                logger.info(f"数据格式正确: {key}")
            else:
                # dict 但字段不对，可能是 MemoryEvent dict
                result["old_data_type"] = "dict (wrong fields)"
                result["old_data_sample"] = existing_data
                result["action"] = "deleted_and_reinitialized"

                logger.warning(
                    f"发现错误 dict 格式: {key}\n"
                    f"  缺失字段: {expected_fields - actual_fields}\n"
                    f"  数据样本: {existing_data}"
                )

                redis_client.delete(key)
                default_state = _create_default_state_dict()
                _json_set(key, '$', default_state)
                result["new_data"] = default_state
                logger.info(f"已重新初始化: {key}")

        else:
            result["old_data_type"] = str(type(existing_data))
            result["action"] = "deleted_and_reinitialized"
            logger.warning(f"未知数据类型: {type(existing_data)}")
            redis_client.delete(key)
            default_state = _create_default_state_dict()
            _json_set(key, '$', default_state)
            result["new_data"] = default_state

    except Exception as e:
        result["action"] = "error"
        result["error"] = str(e)
        logger.error(f"清理失败: {key}, error: {e}")

    return result


def batch_cleanup_all_users() -> list:
    """
    批量清理所有用户的 role_current_state 键

    Returns:
        清理结果列表
    """
    logger.info("开始批量清理所有 role_current_state 键...")

    # 扫描所有 role_current_state 键
    pattern = "chat:memory:*:*:role_current_state"
    keys = redis_client.keys(pattern)

    logger.info(f"发现 {len(keys)} 个 role_current_state 键")

    results = []
    cleaned_count = 0

    for key in keys:
        # 从 key 中提取 user_id 和 llm_id
        # key format: chat:memory:{user_id}:{llm_id}:role_current_state
        parts = key.split(":")
        if len(parts) >= 4:
            user_id = parts[2]
            llm_id = parts[3]

            result = cleanup_malformed_current_state(user_id, llm_id)
            results.append(result)

            if result["action"] == "deleted_and_reinitialized":
                cleaned_count += 1

    logger.info(f"批量清理完成: {cleaned_count}/{len(keys)} 个键已修复")
    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="清理 role_current_state 错误数据")
    parser.add_argument("--user-id", help="指定用户 ID")
    parser.add_argument("--llm-id", help="指定模型 ID", default="default")
    parser.add_argument("--batch", action="store_true", help="批量清理所有用户")

    args = parser.parse_args()

    if args.batch:
        results = batch_cleanup_all_users()
        print(json.dumps(results, ensure_ascii=False, indent=2))
    elif args.user_id:
        result = cleanup_malformed_current_state(args.user_id, args.llm_id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        parser.print_help()
        print("\n示例:")
        print("  # 清理特定用户")
        print("  python scripts/cleanup_malformed_current_state.py --user-id test_user --llm-id default")
        print("\n  # 批量清理所有用户")
        print("  python scripts/cleanup_malformed_current_state.py --batch")