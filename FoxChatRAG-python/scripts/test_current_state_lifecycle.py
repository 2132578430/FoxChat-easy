"""
当前状态生命周期测试脚本

测试场景：
1. 默认状态初始化
2. 状态字段更新与覆盖规则
3. 状态过期机制
4. 摘要注入格式验证

运行方式：
    cd FoxChatRAG-python
    python scripts/test_current_state_lifecycle.py
"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime, timedelta
from loguru import logger

from app.core.db.redis_client import redis_client
from app.common.constant.LLMChatConstant import LLMChatConstant, build_memory_key
from app.service.chat.state_manager import (
    get_current_state,
    update_current_state,
    update_unfinished_items,
    check_and_expire_fields,
    increment_round_counter,
)
from app.schemas.current_state import CurrentState, StateField, UnfinishedItem, ItemStatus, UpdateSource


TEST_USER_ID = "test_current_state_user"
TEST_LLM_ID = "test_current_state_llm"


def cleanup_test_data():
    """清理测试数据"""
    keys_to_delete = [
        build_memory_key(LLMChatConstant.ROLE_CURRENT_STATE, TEST_USER_ID, TEST_LLM_ID),
        build_memory_key(LLMChatConstant.ROLE_EMOTION_STATE, TEST_USER_ID, TEST_LLM_ID),
        f"chat:memory:{TEST_USER_ID}:{TEST_LLM_ID}:round_counter",
    ]

    for key in keys_to_delete:
        redis_client.delete(key)

    logger.info(f"测试数据清理完成")


def test_1_default_state():
    """测试1: 默认状态初始化"""
    logger.info("=" * 50)
    logger.info("测试1: 默认状态初始化")

    # 清理现有数据
    cleanup_test_data()

    # 获取状态（应该返回默认）
    state = get_current_state(TEST_USER_ID, TEST_LLM_ID)

    assert state.emotion.value == "neutral"
    assert state.relation_state.value == "中性"
    assert state.current_focus.value == ""
    assert len(state.unfinished_items) == 0
    assert state.interaction_mode.value == "闲聊"

    logger.info(f"✓ 默认状态: emotion={state.emotion.value}, relation={state.relation_state.value}")


def test_2_emotion_update():
    """测试2: 情绪更新"""
    logger.info("=" * 50)
    logger.info("测试2: 情绪更新")

    # 更新情绪
    update_current_state(
        user_id=TEST_USER_ID,
        llm_id=TEST_LLM_ID,
        field_name="emotion",
        new_value="开心",
        confidence=0.9,
        source=UpdateSource.RUNTIME,
        reason="用户表达开心情绪",
    )

    # 验证更新
    state = get_current_state(TEST_USER_ID, TEST_LLM_ID)
    assert state.emotion.value == "开心"
    assert state.emotion.confidence == 0.9

    logger.info(f"✓ 情绪更新: emotion={state.emotion.value}, confidence={state.emotion.confidence}")


def test_3_focus_update():
    """测试3: 焦点更新"""
    logger.info("=" * 50)
    logger.info("测试3: 焦点更新")

    # 更新焦点
    update_current_state(
        user_id=TEST_USER_ID,
        llm_id=TEST_LLM_ID,
        field_name="current_focus",
        new_value="考试压力",
        confidence=0.7,
        source=UpdateSource.RUNTIME,
        expire_rounds=2,
        reason="从用户输入提取",
    )

    # 验证更新
    state = get_current_state(TEST_USER_ID, TEST_LLM_ID)
    assert state.current_focus.value == "考试压力"

    logger.info(f"✓ 焦点更新: focus={state.current_focus.value}")


def test_4_unfinished_items():
    """测试4: 未完成事项"""
    logger.info("=" * 50)
    logger.info("测试4: 未完成事项")

    # 添加事项
    items = [
        UnfinishedItem(
            content="明天继续聊考试结果",
            status=ItemStatus.PENDING,
            confidence=0.85,
            expire_rounds=6,
        )
    ]
    update_unfinished_items(TEST_USER_ID, TEST_LLM_ID, items)

    # 验证
    state = get_current_state(TEST_USER_ID, TEST_LLM_ID)
    assert len(state.unfinished_items) == 1
    assert state.unfinished_items[0].content == "明天继续聊考试结果"

    logger.info(f"✓ 未完成事项: {len(state.unfinished_items)} 条")


def test_5_overwrite_rules():
    """测试5: 覆盖规则"""
    logger.info("=" * 50)
    logger.info("测试5: 覆盖规则")

    # 尝试低置信度更新（应该不覆盖）
    update_current_state(
        user_id=TEST_USER_ID,
        llm_id=TEST_LLM_ID,
        field_name="emotion",
        new_value="悲伤",
        confidence=0.5,  # 低置信度，差值 < 0.15
        source=UpdateSource.RUNTIME,
        reason="尝试低置信度更新",
    )

    state = get_current_state(TEST_USER_ID, TEST_LLM_ID)
    assert state.emotion.value == "开心"  # 保持原值
    logger.info(f"✓ 低置信度不覆盖: emotion 保持 {state.emotion.value}")

    # 尝试高置信度更新（应该覆盖）
    update_current_state(
        user_id=TEST_USER_ID,
        llm_id=TEST_LLM_ID,
        field_name="emotion",
        new_value="悲伤",
        confidence=0.95,  # 高置信度，差值 >= 0.15
        source=UpdateSource.RUNTIME,
        reason="高置信度更新",
    )

    state = get_current_state(TEST_USER_ID, TEST_LLM_ID)
    assert state.emotion.value == "悲伤"
    logger.info(f"✓ 高置信度覆盖: emotion 更新为 {state.emotion.value}")


def test_6_expiry():
    """测试6: 过期机制"""
    logger.info("=" * 50)
    logger.info("测试6: 过期机制")

    # 模拟轮次推进
    for i in range(3):
        increment_round_counter(TEST_USER_ID, TEST_LLM_ID)

    rounds_passed = increment_round_counter(TEST_USER_ID, TEST_LLM_ID)

    # 检查过期（焦点 expire_rounds=2，应该已过期）
    state = check_and_expire_fields(TEST_USER_ID, TEST_LLM_ID, rounds_passed)

    # 验证焦点已清空
    assert state.current_focus.value == ""
    logger.info(f"✓ 焦点过期: rounds_passed={rounds_passed}, focus 已清空")


def test_7_summary_output():
    """测试7: 摘要输出格式"""
    logger.info("=" * 50)
    logger.info("测试7: 摘要输出格式")

    # 获取状态
    state = get_current_state(TEST_USER_ID, TEST_LLM_ID)
    rounds_passed = 0

    # 获取有效字段
    valid_fields = state.get_valid_fields_for_injection(rounds_passed)

    # 构建摘要
    lines = ["【当前状态】"]
    if "emotion" in valid_fields:
        lines.append(f"- 情绪：{valid_fields['emotion']}")
    if "relation_state" in valid_fields:
        lines.append(f"- 关系：{valid_fields['relation_state']}")
    if "unfinished_items" in valid_fields:
        for item in valid_fields["unfinished_items"][:2]:
            lines.append(f"- 未完成：{item}")

    summary = "\n".join(lines)
    logger.info(f"摘要输出:\n{summary}")

    # 验证格式
    assert "【当前状态】" in summary
    assert "- 情绪：" in summary
    logger.info("✓ 摘要格式验证通过")


def test_8_migration():
    """测试8: 从 legacy emotion_state 迁移"""
    logger.info("=" * 50)
    logger.info("测试8: 从 legacy emotion_state 迁移")

    # 清理 current_state
    redis_client.delete(build_memory_key(LLMChatConstant.ROLE_CURRENT_STATE, TEST_USER_ID, TEST_LLM_ID))

    # 写入 legacy emotion_state
    import json
    legacy_key = build_memory_key(LLMChatConstant.ROLE_EMOTION_STATE, TEST_USER_ID, TEST_LLM_ID)
    legacy_state = {
        "emotion": "愤怒",
        "certainty": "确定",
        "last_update": datetime.now().isoformat(),
    }
    redis_client.set(legacy_key, json.dumps(legacy_state))

    # 读取 current_state（应该触发迁移）
    state = get_current_state(TEST_USER_ID, TEST_LLM_ID)

    assert state.emotion.value == "愤怒"
    logger.info(f"✓ 迁移成功: emotion 从 legacy 迁移为 {state.emotion.value}")


def run_all_tests():
    """运行所有测试"""
    logger.info("=" * 60)
    logger.info("当前状态生命周期测试")
    logger.info("=" * 60)

    try:
        test_1_default_state()
        test_2_emotion_update()
        test_3_focus_update()
        test_4_unfinished_items()
        test_5_overwrite_rules()
        test_6_expiry()
        test_7_summary_output()
        test_8_migration()

        logger.info("=" * 60)
        logger.info("所有测试通过 ✓")
        logger.info("=" * 60)

    finally:
        cleanup_test_data()


if __name__ == "__main__":
    run_all_tests()