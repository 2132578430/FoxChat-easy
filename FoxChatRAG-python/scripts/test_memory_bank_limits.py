"""
Memory Bank 条数对比测试脚本

用途：测试不同 memory_bank 注入条数对 token 消耗的影响

使用方法：
    python scripts/test_memory_bank_limits.py --user-id <用户ID> --llm-id <模型ID>

输出：
    - 各配置下的 token 消耗对比
    - 各组件占比分析
    - 推荐的 memory_bank 条数
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from app.core.db.redis_client import redis_client
from app.common.constant.LLMChatConstant import LLMChatConstant, build_memory_key
from app.util.token_monitor import TokenMonitor, TokenMonitorConfig


# 配置日志
logger.remove()
logger.add(sys.stderr, level="INFO", format="{time} | {level} | {message}")


async def test_memory_bank_config(
    user_id: str,
    llm_id: str,
    memory_bank_limit: int,
    test_rounds: int = 12
) -> dict:
    """
    测试特定 memory_bank 配置下的 token 消耗

    Args:
        user_id: 用户 ID
        llm_id: 模型 ID
        memory_bank_limit: memory_bank 注入条数限制
        test_rounds: 测试轮数（建议 >= 12，因为第一次 summary 在第 9 轮触发）

    Returns:
        测试结果统计
    """
    from app.util.token_monitor import TokenMonitor, TokenMonitorConfig
    from app.service.chat.chat_msg_service import (
        _fetch_all_memories, _parse_all_memories, _build_static_anchors,
    )
    from app.service.chat.prompt_payload_builder import build_prompt_payload, payload_to_invoke_dict
    from app.core.llm_model import model as llm_model
    from app.core.prompts.prompt_manager import PromptManager
    from app.util.template_util import escape_template

    # 创建监控器
    config = TokenMonitorConfig(max_memory_bank_items=memory_bank_limit)
    monitor = TokenMonitor(config)

    # 获取 memory_bank 数据
    memory_bank_key = build_memory_key(LLMChatConstant.MEMORY_BANK, user_id, llm_id)
    memory_bank_json = redis_client.get(memory_bank_key) or ""

    # 检查 memory_bank 当前状态
    mb_count = 0
    if memory_bank_json:
        try:
            bank = json.loads(memory_bank_json)
            mb_count = len(bank) if isinstance(bank, list) else 0
        except:
            pass

    logger.info(f"【初始状态】Memory Bank 当前条数: {mb_count}")

    # 获取所有记忆数据（异步调用）
    memories = await _fetch_all_memories(user_id, llm_id)

    # 测试对话消息（模拟真实对话流程）
    test_messages = [
        "你好，我是用户",
        "最近心情不太好",
        "工作上遇到了一些困难",
        "项目进度一直拖延",
        "团队沟通也不顺畅",
        "感觉压力很大",
        "有时候想放弃",
        "但又觉得不能轻易放弃",
        "你能给我一些建议吗",  # 第9轮：触发第一次 summary
        "谢谢你的建议",
        "我会试着调整心态",
        "希望接下来能顺利一些",
    ]

    # 如果轮数超过预设消息数，循环使用
    if test_rounds > len(test_messages):
        test_messages = test_messages * (test_rounds // len(test_messages) + 1)

    results = []
    history_msg = []  # 积累历史消息

    for i, msg_content in enumerate(test_messages[:test_rounds]):
        logger.info(f"测试轮次 {i+1}/{test_rounds} (MB限制={memory_bank_limit})")

        # 解析记忆
        parsed = _parse_all_memories(memories, current_round=i)

        # 使用监控器解析 memory_bank（按限制条数）
        memory_bank_summary, injected_items = monitor.parse_memory_bank_with_limit(
            memories.memory_bank_json
        )

        # 构建静态锚点
        static_anchors = _build_static_anchors(
            soul="",
            role_declaration=parsed.role_declaration,
            core_anchor=parsed.core_anchor_text,
            character_card="",
            character_card_detail=parsed.character_card_detail,
            mes_example=parsed.character_card_examples,
        )

        # 构建 payload
        payload = build_prompt_payload(
            static_anchors=static_anchors,
            user_profile_summary=parsed.user_profile_summary,
            historical_context=memory_bank_summary,  # 使用限制后的 memory_bank
            current_state=parsed.current_state,
            history_msg=history_msg,  # 使用积累的历史消息
            user_message=msg_content,
            recent_messages=[],
            enable_dedup=True,
            enable_conflict_priority=True,
        )

        # 构建 Prompt Template（复用 markdown 模板）
        from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

        prompt_text = await PromptManager.get_prompt("chat_system")
        prompt_text = escape_template(
            prompt_text,
            ["static_anchors", "user_profile_summary", "historical_context", "current_state"],
        )
        template = ChatPromptTemplate(
            [
                ("system", prompt_text),
                MessagesPlaceholder("history_msg"),
                ("human", "Reply with a response that matches the current memory and identity according to the above prompts and memory template:\n{user_message}")
            ]
        )

        # 获取模型
        llm = await llm_model.get_chat_model()

        # 构建 chain（不使用 StrOutputParser，保留 metadata）
        chain = template | llm

        # 调用 LLM，获取 AIMessage（而非字符串）
        invoke_dict = payload_to_invoke_dict(payload)
        aimessage = await chain.ainvoke(invoke_dict)

        # 提取 token 数据
        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0

        if hasattr(aimessage, 'response_metadata'):
            usage = aimessage.response_metadata.get('token_usage', {})
            prompt_tokens = usage.get('prompt_tokens', 0)
            completion_tokens = usage.get('completion_tokens', 0)
            total_tokens = usage.get('total_tokens', 0)

        response_text = aimessage.content if hasattr(aimessage, 'content') else str(aimessage)

        # 将响应添加到历史消息（模拟真实对话流程）
        from langchain_core.messages import HumanMessage, AIMessage
        history_msg.append(HumanMessage(content=msg_content))
        history_msg.append(AIMessage(content=response_text))

        # 计算组件字符数
        total_chars = (
            len(static_anchors or "") +
            len(parsed.user_profile_summary or "") +
            len(parsed.current_state or "") +
            len(memory_bank_summary) +
            len(msg_content)
        )

        result = {
            "round": i + 1,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "memory_bank_items": injected_items,
            "memory_bank_chars": len(memory_bank_summary),
            "total_chars": total_chars,
            "mb_chars_ratio": len(memory_bank_summary) / total_chars * 100 if total_chars > 0 else 0,
        }

        results.append(result)

        logger.info(
            f"  Prompt={prompt_tokens}, Completion={completion_tokens}, "
            f"MB注入={injected_items}条, MB占比={result['mb_chars_ratio']:.1f}%"
        )

    # 统计汇总
    avg_prompt = sum(r["prompt_tokens"] for r in results) / len(results)
    avg_completion = sum(r["completion_tokens"] for r in results) / len(results)
    avg_mb_ratio = sum(r["mb_chars_ratio"] for r in results) / len(results)

    return {
        "config": {
            "memory_bank_limit": memory_bank_limit,
            "test_rounds": test_rounds,
        },
        "results": results,
        "summary": {
            "avg_prompt_tokens": avg_prompt,
            "avg_completion_tokens": avg_completion,
            "avg_mb_chars_ratio": avg_mb_ratio,
        }
    }


async def compare_memory_bank_limits(
    user_id: str,
    llm_id: str,
    limits: List[int] = [0, 3, 5, 7, 10],
    test_rounds: int = 12
) -> dict:
    """
    对比不同 memory_bank 条数限制的效果

    Args:
        user_id: 用户 ID
        llm_id: 模型 ID
        limits: 要测试的条数限制列表

    Returns:
        对比结果
    """
    logger.info(f"开始对比测试: limits={limits}")

    comparison_results = []

    for limit in limits:
        logger.info(f"\n{'='*50}")
        logger.info(f"测试配置: Memory Bank 限制 = {limit} 条")

        result = await test_memory_bank_config(
            user_id=user_id,
            llm_id=llm_id,
            memory_bank_limit=limit,
            test_rounds=test_rounds  # 使用传入的测试轮数
        )

        comparison_results.append(result)

    # 生成对比报告
    report = generate_comparison_report(comparison_results)

    return {
        "comparison": comparison_results,
        "report": report,
    }


def generate_comparison_report(results: List[dict]) -> str:
    """生成对比报告"""

    report = f"""
# Memory Bank 条数对比测试报告

> 生成时间: {datetime.now().isoformat()}

## 测试对比

| MB条数限制 | 平均Prompt | 平均Completion | MB字符占比 |
|-----------|-----------|---------------|-----------|
"""

    for r in results:
        config = r["config"]["memory_bank_limit"]
        avg_prompt = r["summary"]["avg_prompt_tokens"]
        avg_completion = r["summary"]["avg_completion_tokens"]
        mb_ratio = r["summary"]["avg_mb_chars_ratio"]

        report += f"| {config} | {avg_prompt:.1f} | {avg_completion:.1f} | {mb_ratio:.1f}% |\n"

    # 分析推荐
    report += "\n## 分析与推荐\n"

    # 找出 token 增长最快的配置
    baseline = results[0]["summary"]["avg_prompt_tokens"]  # 0条作为基线

    report += f"\n### Token 增长分析（以 0 条为基线）\n"
    for r in results[1:]:
        limit = r["config"]["memory_bank_limit"]
        avg_prompt = r["summary"]["avg_prompt_tokens"]
        increase = avg_prompt - baseline
        increase_ratio = (increase / baseline * 100) if baseline > 0 else 0

        report += f"- {limit} 条: 增加 {increase:.1f} tokens ({increase_ratio:.1f}%)\n"

    # 推荐
    report += "\n### 推荐\n"

    # 找到性价比最优的配置（token增长 < 20% 但有足够上下文）
    recommended = None
    for r in results[1:]:
        avg_prompt = r["summary"]["avg_prompt_tokens"]
        increase_ratio = (avg_prompt - baseline) / baseline * 100 if baseline > 0 else 0
        limit = r["config"]["memory_bank_limit"]

        if increase_ratio < 20 and limit >= 3:
            recommended = limit
            break

    if recommended:
        report += f"**推荐配置: {recommended} 条**\n"
        report += f"- 原因: Token增长控制在 20% 以内，同时提供足够的上下文\n"
    else:
        report += f"**推荐配置: 3-5 条**\n"
        report += f"- 原因: 平衡 token 消耗与上下文完整性\n"

    report += "\n---\n"
    report += "*此报告由 test_memory_bank_limits.py 自动生成*\n"

    return report


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Memory Bank 条数对比测试")
    parser.add_argument("--user-id", required=True, help="测试用户 ID")
    parser.add_argument("--llm-id", required=True, help="测试模型 ID")
    parser.add_argument("--rounds", type=int, default=12,
                        help="测试轮数（默认12轮，因为第一次summary在第9轮触发）")
    parser.add_argument("--limits", nargs='+', type=int, default=[0, 3, 5, 7, 10],
                        help="要测试的 memory_bank 条数限制列表")

    parser.add_argument("--output", default="logs/memory_bank_comparison_report.md",
                        help="报告输出路径")

    args = parser.parse_args()

    logger.info(f"开始测试: user_id={args.user_id}, llm_id={args.llm_id}, rounds={args.rounds}")

    # 执行对比测试
    comparison = await compare_memory_bank_limits(
        user_id=args.user_id,
        llm_id=args.llm_id,
        limits=args.limits,
        test_rounds=args.rounds  # 传递测试轮数
    )

    # 输出报告
    report = comparison["report"]
    print(report)

    # 写入文件
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)

    logger.info(f"报告已保存到: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())