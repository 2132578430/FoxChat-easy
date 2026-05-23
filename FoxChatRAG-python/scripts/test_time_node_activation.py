"""
时间节点激活测试脚本

测试场景：
1. 时间节点创建（明天/后天/下周）
2. 时间归一化验证
3. 到期检查与激活
4. 激活后路由到 B 层

运行方式：
    cd FoxChatRAG-python
    python scripts/test_time_node_activation.py
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger

from app.core.db.redis_client import redis_client
from app.common.constant.LLMChatConstant import LLMChatConstant, build_memory_key
from app.service.chat.time_node_service import (
    create_time_node,
    get_all_time_nodes,
    get_pending_time_nodes,
    check_due_time_nodes,
    activate_time_node,
    mark_time_node_done,
    extract_time_node_from_text,
    check_and_activate_due_time_nodes,
)
from app.schemas.time_node import TimeNodeStatus, CreatedFrom


TEST_USER_ID = "test_time_node_user"
TEST_LLM_ID = "test_time_node_llm"


def cleanup_test_data():
    """清理测试数据"""
    keys_to_delete = [
        build_memory_key(LLMChatConstant.ROLE_TIME_NODES, TEST_USER_ID, TEST_LLM_ID),
        build_memory_key(LLMChatConstant.ROLE_CURRENT_STATE, TEST_USER_ID, TEST_LLM_ID),
    ]

    for key in keys_to_delete:
        redis_client.delete(key)

    logger.info(f"测试数据清理完成")


def test_1_create_tomorrow():
    """测试1: 创建"明天"时间节点"""
    logger.info("=" * 50)
    logger.info("测试1: 创建'明天'时间节点")

    cleanup_test_data()

    # 创建节点
    node = create_time_node(
        user_id=TEST_USER_ID,
        llm_id=TEST_LLM_ID,
        content="明天考试",
        time_expression="明天",
        created_from=CreatedFrom.USER_FUTURE_EVENT,
        source_round=1,
    )

    assert node is not None
    assert node.status == TimeNodeStatus.PENDING

    # 验证 due_at 是明天
    tomorrow = datetime.now() + timedelta(days=1)
    expected_due = tomorrow.strftime("%Y-%m-%d")

    assert node.due_at == expected_due
    logger.info(f"✓ 创建成功: id={node.time_node_id}, due_at={node.due_at}")


def test_2_create_next_week():
    """测试2: 创建"下周"时间节点"""
    logger.info("=" * 50)
    logger.info("测试2: 创建'下周'时间节点")

    node = create_time_node(
        user_id=TEST_USER_ID,
        llm_id=TEST_LLM_ID,
        content="下周出结果",
        time_expression="下周",
        created_from=CreatedFrom.USER_FUTURE_EVENT,
        source_round=2,
    )

    assert node is not None

    # 验证 due_at 是下周
    next_week = datetime.now() + timedelta(weeks=1)
    expected_due = next_week.strftime("%Y-%m-%d")

    assert node.due_at == expected_due
    logger.info(f"✓ 创建成功: id={node.time_node_id}, due_at={node.due_at}")


def test_3_extract_from_text():
    """测试3: 从文本提取时间节点"""
    logger.info("=" * 50)
    logger.info("测试3: 从文本提取时间节点")

    # 用户输入场景
    user_node = extract_time_node_from_text(
        user_id=TEST_USER_ID,
        llm_id=TEST_LLM_ID,
        text="我明天考试，很紧张",
        is_ai_reply=False,
        source_round=3,
    )

    assert user_node is not None
    assert user_node.created_from == CreatedFrom.USER_FUTURE_EVENT
    logger.info(f"✓ 用户输入提取: {user_node.content[:30]}...")

    # AI 回复场景
    ai_node = extract_time_node_from_text(
        user_id=TEST_USER_ID,
        llm_id=TEST_LLM_ID,
        text="好的，明天我再陪你聊聊考试结果",
        is_ai_reply=True,
        source_round=4,
    )

    assert ai_node is not None
    assert ai_node.created_from == CreatedFrom.AI_COMMITMENT
    logger.info(f"✓ AI 回复提取: {ai_node.content[:30]}...")


def test_4_no_node_for_past():
    """测试4: 过去事件不创建节点"""
    logger.info("=" * 50)
    logger.info("测试4: 过去事件不创建节点")

    # "昨天"不应该创建节点
    past_node = extract_time_node_from_text(
        user_id=TEST_USER_ID,
        llm_id=TEST_LLM_ID,
        text="昨天我很难过",
        is_ai_reply=False,
        source_round=5,
    )

    assert past_node is None
    logger.info("✓ 过去事件不创建节点")


def test_5_pending_nodes():
    """测试5: 获取 pending 节点"""
    logger.info("=" * 50)
    logger.info("测试5: 获取 pending 节点")

    pending_nodes = get_pending_time_nodes(TEST_USER_ID, TEST_LLM_ID)

    # 应该有之前创建的节点（明天和下周的）
    logger.info(f"当前 pending 节点数: {len(pending_nodes)}")

    for node in pending_nodes:
        logger.info(f"  - {node.time_node_id}: due_at={node.due_at}, content={node.content[:30]}...")

    assert len(pending_nodes) >= 2


def test_6_due_check():
    """测试6: 到期检查"""
    logger.info("=" * 50)
    logger.info("测试6: 到期检查")

    # 创建一个已到期的节点（手动设置 due_at 为今天）
    from app.schemas.time_node import TimeNode, TimeNodeList, TimePrecision

    # 手动创建一个今天到期的节点
    today_node = TimeNode(
        time_node_id=f"tn_{datetime.now().strftime('%Y%m%d')}_999",
        content="今天应该做的事",
        due_at=datetime.now().strftime("%Y-%m-%d"),
        precision=TimePrecision.DAY,
        status=TimeNodeStatus.PENDING,
        created_from=CreatedFrom.USER_FUTURE_EVENT,
        source_round=0,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
    )

    nodes = get_all_time_nodes(TEST_USER_ID, TEST_LLM_ID)
    nodes.add_node(today_node)

    key = build_memory_key(LLMChatConstant.ROLE_TIME_NODES, TEST_USER_ID, TEST_LLM_ID)
    redis_client.set(key, nodes.model_dump_json())

    # 检查到期
    due_nodes = check_due_time_nodes(TEST_USER_ID, TEST_LLM_ID)

    # 今天到期的节点应该被检测到
    due_today = [n for n in due_nodes if n.due_at == datetime.now().strftime("%Y-%m-%d")]
    assert len(due_today) > 0

    logger.info(f"✓ 到期检查: {len(due_nodes)} 个节点到期")
    for node in due_nodes:
        logger.info(f"  - {node.time_node_id}: {node.due_at}")


def test_7_activation():
    """测试7: 激活节点"""
    logger.info("=" * 50)
    logger.info("测试7: 激活节点")

    # 激活今天到期的节点
    due_nodes = check_due_time_nodes(TEST_USER_ID, TEST_LLM_ID)

    if due_nodes:
        node = due_nodes[0]
        activate_time_node(TEST_USER_ID, TEST_LLM_ID, node)

        # 验证状态变化
        nodes = get_all_time_nodes(TEST_USER_ID, TEST_LLM_ID)
        activated = [n for n in nodes.nodes if n.time_node_id == node.time_node_id]

        assert activated[0].status == TimeNodeStatus.ACTIVE
        logger.info(f"✓ 激活成功: {node.time_node_id} -> active")


def test_8_mark_done():
    """测试8: 标记完成"""
    logger.info("=" * 50)
    logger.info("测试8: 标记完成")

    # 获取 active 节点
    nodes = get_all_time_nodes(TEST_USER_ID, TEST_LLM_ID)
    active_nodes = nodes.get_active_nodes()

    if active_nodes:
        mark_time_node_done(TEST_USER_ID, TEST_LLM_ID, active_nodes[0].time_node_id)

        # 验证状态变化
        nodes = get_all_time_nodes(TEST_USER_ID, TEST_LLM_ID)
        done_nodes = [n for n in nodes.nodes if n.time_node_id == active_nodes[0].time_node_id]

        assert done_nodes[0].status == TimeNodeStatus.DONE
        logger.info(f"✓ 标记完成: {active_nodes[0].time_node_id} -> done")


def test_9_full_activation_flow():
    """测试9: 完整激活流程"""
    logger.info("=" * 50)
    logger.info("测试9: 完整激活流程")

    # 清理并创建新的今天到期节点
    cleanup_test_data()

    from app.schemas.time_node import TimeNode, TimeNodeList, TimePrecision

    today_node = TimeNode(
        time_node_id=f"tn_{datetime.now().strftime('%Y%m%d')}_001",
        content="今天要跟进的事项",
        due_at=datetime.now().strftime("%Y-%m-%d"),
        precision=TimePrecision.DAY,
        status=TimeNodeStatus.PENDING,
        created_from=CreatedFrom.USER_FUTURE_FOLLOWUP,
        source_round=10,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
    )

    nodes = TimeNodeList()
    nodes.add_node(today_node)

    key = build_memory_key(LLMChatConstant.ROLE_TIME_NODES, TEST_USER_ID, TEST_LLM_ID)
    redis_client.set(key, nodes.model_dump_json())

    # 执行完整激活流程
    activated_contents = check_and_activate_due_time_nodes(TEST_USER_ID, TEST_LLM_ID)

    assert len(activated_contents) > 0
    logger.info(f"✓ 完整流程: 激活 {len(activated_contents)} 个节点")
    for content in activated_contents:
        logger.info(f"  - 内容: {content[:50]}...")


def run_all_tests():
    """运行所有测试"""
    logger.info("=" * 60)
    logger.info("时间节点激活测试")
    logger.info("=" * 60)

    try:
        test_1_create_tomorrow()
        test_2_create_next_week()
        test_3_extract_from_text()
        test_4_no_node_for_past()
        test_5_pending_nodes()
        test_6_due_check()
        test_7_activation()
        test_8_mark_done()
        test_9_full_activation_flow()

        logger.info("=" * 60)
        logger.info("所有测试通过 ✓")
        logger.info("=" * 60)

    finally:
        cleanup_test_data()


if __name__ == "__main__":
    run_all_tests()