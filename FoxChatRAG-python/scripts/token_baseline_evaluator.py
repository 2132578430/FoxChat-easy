"""
Token 基线评估脚本

阶段 0: 建立各记忆组件的 Token 消耗基线数据

职责:
- 复用现有 chat_msg_service 的核心函数
- 模拟 N 轮对话，记录每轮 Token 消耗
- 从 API response_metadata 获取真实 Token 数据
- 手动触发总结流程（绕过阈值限制）
- 输出 Markdown 格式的基线评估报告

运行方式:
    cd FoxChatRAG-python
    python scripts/token_baseline_evaluator.py [--rounds N] [--output PATH]
"""

import asyncio
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger

# ==================== 配置常量 (任务 1.3) ====================

TEST_USER_ID = "token_test_user_001"
TEST_LLM_ID = "token_test_llm_001"
TEST_ROUNDS = 5  # 默认测试轮数
SUMMARY_INTERVAL = 3  # 每 3 轮触发一次总结
CLEANUP_AFTER_TEST = True  # 测试后清理数据
OUTPUT_PATH = "docs/token_baseline_report.md"


# ==================== 数据结构 (任务 1.4) ====================

@dataclass
class ComponentSizes:
    """各组件的字符数"""
    soul: int = 0
    role_declaration: int = 0
    core_anchor: int = 0
    character_card: int = 0
    character_card_detail: int = 0
    user_profile: int = 0
    memory_bank: int = 0
    current_state: int = 0
    relevant_memories: int = 0
    history_msg: int = 0
    user_input: int = 0

    def total(self) -> int:
        return sum([
            self.soul, self.role_declaration, self.core_anchor,
            self.character_card, self.character_card_detail,
            self.user_profile, self.memory_bank, self.current_state,
            self.relevant_memories, self.history_msg, self.user_input
        ])


@dataclass
class TokenData:
    """Token 消耗数据"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class RoundResult:
    """单轮测试结果"""
    round_number: int
    user_input: str
    ai_response: str
    component_sizes: ComponentSizes
    token_data: TokenData
    memory_bank_items: int = 0
    current_state_value: str = ""
    timestamp: str = ""


# ==================== 测试数据 (任务 2.1, 2.2) ====================

MOCK_SOUL = """
你是一个温柔、善解人意的陪伴者。你关心用户的情绪，善于倾听，愿意在用户需要时提供安慰和支持。
你不会评判用户，而是尝试理解他们的处境，给予真诚的回应。
"""

MOCK_ROLE_DECLARATION = """
我是你的倾听者和陪伴者。我会认真听你说每一句话，记住我们之间的重要约定，在你需要时给予支持。
"""

MOCK_CORE_ANCHOR = """
【角色核心锚点】
- 善于倾听，不急于给出建议
- 记住用户的重要事项和约定
- 用温柔的语气回应
- 保持真诚，不做虚假承诺

【绝对边界】
- 不讨论敏感话题
- 不代替专业心理咨询
"""

MOCK_CHARACTER_CARD = {
    "性格关键词": "温柔、善解人意、耐心",
    "动作风格": "轻声细语，用拥抱和安慰的语气",
    "常用动作": ["轻拍肩膀", "递上一杯温水", "静静陪伴"],
    "核心描述": "一个温暖的陪伴者，愿意倾听用户的烦恼",
    "示例对话": [
        "用户：我今天感觉很累。\n角色：辛苦了，来，坐下休息一会儿，有什么想聊聊的吗？"
    ]
}

MOCK_USER_PROFILE = {
    "基本信息": {
        "年龄": "大学生",
        "状态": "考试期间"
    },
    "偏好": {
        "称呼方式": "朋友",
        "互动风格": "温柔陪伴"
    },
    "近期关注": ["考试压力", "作息调整"]
}

# 测试对话剧本 (5轮)
TEST_CONVERSATION_SCRIPT = [
    "你好，我今天心情不太好，想找人聊聊。",
    "其实是因为最近考试压力很大，感觉复习不完，很焦虑。",
    "谢谢你愿意听我说。我答应自己明天要早起继续复习，但总是做不到。",
    "今天又拖延了一天，感觉好失败，可能我真的不适合这种高强度学习。",
    "你说得对，我需要调整心态。你能帮我想想怎么安排明天的复习计划吗？"
]


# ==================== Redis 初始化与清理 (任务 2.3, 2.4) ====================

def initialize_test_redis_data(redis_client) -> None:
    """初始化测试 Redis 数据"""
    from app.common.constant.LLMChatConstant import LLMChatConstant, build_memory_key

    # 写入模拟的 character_card
    character_card_key = build_memory_key(LLMChatConstant.CHARACTER_CARD, TEST_USER_ID, TEST_LLM_ID)
    redis_client.set(character_card_key, json.dumps(MOCK_CHARACTER_CARD, ensure_ascii=False))

    # 写入模拟的 core_anchor
    core_anchor_key = build_memory_key(LLMChatConstant.CORE_ANCHOR, TEST_USER_ID, TEST_LLM_ID)
    redis_client.set(core_anchor_key, MOCK_ROLE_DECLARATION + MOCK_CORE_ANCHOR)

    # 写入模拟的 user_profile
    user_profile_key = build_memory_key(LLMChatConstant.USER_PROFILE, TEST_USER_ID, TEST_LLM_ID)
    redis_client.set(user_profile_key, json.dumps(MOCK_USER_PROFILE, ensure_ascii=False))

    logger.info(f"测试数据初始化完成: user={TEST_USER_ID}, llm={TEST_LLM_ID}")


def cleanup_test_redis_data(redis_client) -> None:
    """清理测试 Redis 数据"""
    from app.common.constant.LLMChatConstant import LLMChatConstant, build_memory_key

    keys_to_delete = [
        build_memory_key(LLMChatConstant.RAW_EXPERIENCE, TEST_USER_ID, TEST_LLM_ID),
        build_memory_key(LLMChatConstant.CORE_ANCHOR, TEST_USER_ID, TEST_LLM_ID),
        build_memory_key(LLMChatConstant.USER_PROFILE, TEST_USER_ID, TEST_LLM_ID),
        build_memory_key(LLMChatConstant.CHARACTER_CARD, TEST_USER_ID, TEST_LLM_ID),
        build_memory_key(LLMChatConstant.MEMORY_BANK, TEST_USER_ID, TEST_LLM_ID),
        build_memory_key(LLMChatConstant.INIT_MEMORY, TEST_USER_ID, TEST_LLM_ID),
        build_memory_key(LLMChatConstant.RECENT_MSG, TEST_USER_ID, TEST_LLM_ID),
        build_memory_key(LLMChatConstant.ROLE_CURRENT_STATE, TEST_USER_ID, TEST_LLM_ID),
        build_memory_key(LLMChatConstant.ROLE_TIME_NODES, TEST_USER_ID, TEST_LLM_ID),
        LLMChatConstant.CHAT_MEMORY + TEST_USER_ID + ":" + TEST_LLM_ID + ":" + LLMChatConstant.RECENT_MSG,
    ]

    pip = redis_client.pipeline()
    for key in keys_to_delete:
        pip.delete(key)
    pip.execute()

    logger.info(f"测试数据清理完成: user={TEST_USER_ID}, llm={TEST_LLM_ID}")


# ==================== 核心评估逻辑 (任务 3.x) ====================

async def traced_invoke_llm(
    parsed: Any,
    history_msg: List[Any],
    soul: str,
    msg_content: str,
    user_id: str,
    llm_id: str
) -> tuple[str, ComponentSizes, TokenData]:
    """
    包装 LLM 调用，记录各组件大小和 Token 消耗

    关键：直接调用 LLM 而不经过 StrOutputParser，以获取 response_metadata
    """
    from app.core.llm_model import model as llm_model
    from app.core.prompts.prompt_manager import PromptManager
    from app.common.constant.ChromaTypeConstant import ChromaTypeConstant
    from app.util import chroma_util
    from app.util.template_util import escape_template
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

    # 记录各组件字符数
    sizes = ComponentSizes(
        soul=len(soul or ""),
        role_declaration=len(parsed.role_declaration or ""),
        core_anchor=len(parsed.core_anchor_text or ""),
        character_card=len(parsed.character_card_examples or ""),
        character_card_detail=len(parsed.character_card_detail or ""),
        user_profile=len(parsed.user_profile_summary or ""),
        memory_bank=len(parsed.memory_bank_summary or ""),
        current_state=len(parsed.current_state or ""),
        relevant_memories=0,
        history_msg=sum(len(str(m.content)) for m in history_msg) if history_msg else 0,
        user_input=len(msg_content)
    )

    # 检索相关记忆
    try:
        documents = await chroma_util.search(
            ChromaTypeConstant.CHAT,
            msg_content,
            {"user_id": user_id, "llm_id": llm_id}
        )
        relevant_memories = "\n".join([f"- {doc.page_content}" for doc in documents[:3]]) if documents else ""
        sizes.relevant_memories = len(relevant_memories)
    except Exception as e:
        logger.warning(f"检索相关记忆失败: {e}")
        relevant_memories = ""
        sizes.relevant_memories = 0

    # 获取 LLM 模型
    llm = await llm_model.get_chat_model()

    # 构建 Prompt Template（复用 markdown 模板）
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

    static_anchors = "\n\n".join(
        part for part in [
            soul or "",
            parsed.role_declaration or "",
            parsed.core_anchor_text or "",
            parsed.character_card_detail or "",
            parsed.character_card_examples or "",
        ] if part
    )

    historical_context = relevant_memories if relevant_memories else parsed.memory_bank_summary

    # 构建 chain，但不使用 StrOutputParser，以保留 metadata
    chain = template | llm

    # 调用 LLM，获取 AIMessage (而非字符串)
    aimessage = await chain.ainvoke({
        "static_anchors": static_anchors,
        "user_profile_summary": parsed.user_profile_summary,
        "historical_context": historical_context,
        "current_state": parsed.current_state,
        "history_msg": history_msg,
        "user_message": msg_content,
    })

    # 提取响应文本
    response_text = aimessage.content if hasattr(aimessage, 'content') else str(aimessage)

    # 提取 Token 数据
    token_data = TokenData()
    if hasattr(aimessage, 'response_metadata'):
        usage = aimessage.response_metadata.get('token_usage', {})
        if usage:
            token_data.prompt_tokens = usage.get('prompt_tokens', 0)
            token_data.completion_tokens = usage.get('completion_tokens', 0)
            token_data.total_tokens = usage.get('total_tokens', 0)

    # 备用方案：某些模型可能通过其他方式返回
    if token_data.total_tokens == 0 and hasattr(aimessage, 'usage_metadata'):
        meta = aimessage.usage_metadata
        token_data.prompt_tokens = meta.get('input_tokens', 0)
        token_data.completion_tokens = meta.get('output_tokens', 0)
        token_data.total_tokens = token_data.prompt_tokens + token_data.completion_tokens

    return response_text, sizes, token_data


def get_memory_bank_count(redis_client, user_id: str, llm_id: str) -> int:
    """获取 Memory Bank 当前条数"""
    from app.common.constant.LLMChatConstant import LLMChatConstant, build_memory_key

    key = build_memory_key(LLMChatConstant.MEMORY_BANK, user_id, llm_id)
    data = redis_client.get(key)

    if not data:
        return 0

    try:
        bank = json.loads(data)
        return len(bank) if isinstance(bank, list) else 0
    except json.JSONDecodeError:
        return 0


def get_current_state_value(redis_client, user_id: str, llm_id: str) -> str:
    """获取当前状态摘要文本"""
    from app.common.constant.LLMChatConstant import LLMChatConstant, build_memory_key

    key = build_memory_key(LLMChatConstant.ROLE_CURRENT_STATE, user_id, llm_id)
    data = redis_client.execute_command('JSON.GET', key)

    if not data:
        return ""

    try:
        if isinstance(data, dict):
            state = data
        else:
            state = json.loads(data)
        return json.dumps(state, ensure_ascii=False)
    except (json.JSONDecodeError, TypeError):
        return ""


# ==================== 主循环逻辑 (任务 3.4, 4.x) ====================

async def run_evaluation_loop(
    rounds: int,
    redis_client,
    user_id: str,
    llm_id: str
) -> List[RoundResult]:
    """运行评估主循环"""
    from app.service.chat.chat_msg_service import (
        _fetch_all_memories,
        _parse_all_memories,
        _build_history_message,
        _build_recent_msg_key
    )
    from app.service.chat.memory_summary_service import async_summary_msg
    from app.common.constant.LLMChatConstant import LLMChatConstant
    from app.core.prompts.prompt_manager import PromptManager

    results: List[RoundResult] = []
    recent_msg_key = _build_recent_msg_key(user_id, llm_id)

    for round_num in range(1, rounds + 1):
        logger.info(f"========== 第 {round_num}/{rounds} 轮测试 ========== ")

        # 获取用户输入
        user_input = TEST_CONVERSATION_SCRIPT[round_num - 1] if round_num <= len(TEST_CONVERSATION_SCRIPT) else "继续聊天..."

        # 1. 获取所有记忆
        memories = await _fetch_all_memories(user_id, llm_id)

        # 2. 解析记忆
        parsed = _parse_all_memories(memories)

        # 3. 构建历史消息
        history_msg = await _build_history_message(memories.recent_msg)

        # 4. 获取 soul (使用 mock 数据，因为 PromptManager 可能没有测试用的 soul)
        soul = MOCK_SOUL  # 测试场景使用 mock 数据

        # 5. 调用 LLM (带追踪)
        response, sizes, token_data = await traced_invoke_llm(
            parsed, history_msg, soul, user_input, user_id, llm_id
        )

        # 6. 保存对话到 Redis
        pip = redis_client.pipeline()
        pip.lpush(recent_msg_key, json.dumps({"role": "human", "content": user_input}))
        pip.lpush(recent_msg_key, json.dumps({"role": "ai", "content": response}))
        result = pip.execute()
        msg_count = len(memories.recent_msg) + 2  # 估算消息数

        # 7. 记录结果
        result_obj = RoundResult(
            round_number=round_num,
            user_input=user_input,
            ai_response=response[:200] + "..." if len(response) > 200 else response,
            component_sizes=sizes,
            token_data=token_data,
            memory_bank_items=get_memory_bank_count(redis_client, user_id, llm_id),
            current_state_value=get_current_state_value(redis_client, user_id, llm_id),
            timestamp=datetime.now().isoformat()
        )
        results.append(result_obj)

        # 8. 手动触发总结 (每 SUMMARY_INTERVAL 轮)
        if round_num % SUMMARY_INTERVAL == 0 and round_num > 0:
            logger.info(f"触发记忆总结 (第 {round_num} 轮)")
            await async_summary_msg(recent_msg_key, msg_count, user_id, llm_id)

            # 记录总结后的 Memory Bank 变化
            new_count = get_memory_bank_count(redis_client, user_id, llm_id)
            logger.info(f"Memory Bank 条数: {result_obj.memory_bank_items} -> {new_count}")

        # 打印本轮摘要
        logger.info(f"Prompt Tokens: {token_data.prompt_tokens}, Completion: {token_data.completion_tokens}")
        logger.info(f"组件字符总数: {sizes.total()}, Memory Bank条数: {result_obj.memory_bank_items}")

    return results


# ==================== 数据分析 (任务 5.x) ====================

def calculate_component_percentages(results: List[RoundResult]) -> Dict[str, List[float]]:
    """计算各组件占比"""
    percentages = {
        "soul": [],
        "anchor": [],
        "profile": [],
        "memory_bank": [],
        "current_state": [],
        "history": [],
        "user_input": [],
    }

    for result in results:
        total_chars = result.component_sizes.total()
        if total_chars == 0:
            continue

        percentages["soul"].append(result.component_sizes.soul / total_chars * 100)
        percentages["anchor"].append(
            (result.component_sizes.role_declaration + result.component_sizes.core_anchor) / total_chars * 100
        )
        percentages["profile"].append(result.component_sizes.user_profile / total_chars * 100)
        percentages["memory_bank"].append(result.component_sizes.memory_bank / total_chars * 100)
        percentages["current_state"].append(result.component_sizes.current_state / total_chars * 100)
        percentages["history"].append(result.component_sizes.history_msg / total_chars * 100)
        percentages["user_input"].append(result.component_sizes.user_input / total_chars * 100)

    return percentages


def project_50_round_trend(results: List[RoundResult]) -> Dict[str, Any]:
    """基于 5 轮数据推断 50 轮趋势"""
    if len(results) < 2:
        return {"error": "数据不足"}

    first = results[0]
    last = results[-1]

    # Memory Bank 增长假设
    memory_growth_per_interval = last.memory_bank_items - first.memory_bank_items
    intervals_in_50 = 50 // SUMMARY_INTERVAL
    projected_memory_items = first.memory_bank_items + memory_growth_per_interval * intervals_in_50

    # History 增长假设
    history_chars_growth = last.component_sizes.history_msg - first.component_sizes.history_msg
    rounds_growth = len(results) - 1
    history_chars_per_round = history_chars_growth / rounds_growth if rounds_growth > 0 else 0
    projected_history_chars = first.component_sizes.history_msg + history_chars_per_round * 49

    # Token 增长推断
    token_growth = last.token_data.prompt_tokens - first.token_data.prompt_tokens
    token_per_round = token_growth / rounds_growth if rounds_growth > 0 else 0
    projected_50_prompt_tokens = first.token_data.prompt_tokens + token_per_round * 49

    return {
        "projected_memory_bank_items": projected_memory_items,
        "projected_history_chars": int(projected_history_chars),
        "projected_50_prompt_tokens": int(projected_50_prompt_tokens),
        "memory_growth_rate": memory_growth_per_interval,
        "history_growth_rate": history_chars_per_round,
        "token_growth_rate": token_per_round,
    }


def identify_fastest_growing_component(percentages: Dict[str, List[float]]) -> str:
    """识别增长最快的组件"""
    growth_rates = {}

    for component, values in percentages.items():
        if len(values) >= 2:
            growth = values[-1] - values[0]
            growth_rates[component] = growth

    if not growth_rates:
        return "unknown"

    fastest = max(growth_rates, key=growth_rates.get)
    return f"{fastest} (增长率: {growth_rates[fastest]:.2f}%)"


def identify_problems(results: List[RoundResult], percentages: Dict[str, List[float]], projection: Dict) -> List[str]:
    """识别问题点"""
    problems = []

    if percentages.get("memory_bank") and len(percentages["memory_bank"]) >= 2:
        growth = percentages["memory_bank"][-1] - percentages["memory_bank"][0]
        if growth > 5:
            problems.append(f"Memory Bank 占比增长过快 (+{growth:.1f}%)，需考虑按需检索而非全量注入")

    if percentages.get("history") and percentages["history"][-1] > 30:
        problems.append(f"History 占比过高 ({percentages['history'][-1]:.1f}%)，需控制最近对话窗口大小")

    if projection.get("projected_50_prompt_tokens") and projection["projected_50_prompt_tokens"] > 8000:
        problems.append(f"50轮推断 Prompt Token 可能超过 {projection['projected_50_prompt_tokens']}，接近模型限制")

    if results and results[-1].memory_bank_items > 10:
        problems.append(f"Memory Bank 已有 {results[-1].memory_bank_items} 条，可能存在重复事件，需去重机制")

    return problems


# ==================== 报告生成 (任务 6.x) ====================

def generate_token_table(results: List[RoundResult]) -> str:
    """生成 Token 消耗表格"""
    lines = [
        "| 轮次 | Prompt Tokens | Completion Tokens | Total Tokens | Memory Bank条数 |",
        "|------|---------------|-------------------|--------------|-----------------|"
    ]

    for r in results:
        lines.append(
            f"| {r.round_number} | {r.token_data.prompt_tokens} | {r.token_data.completion_tokens} | {r.token_data.total_tokens} | {r.memory_bank_items} |"
        )

    return "\n".join(lines)


def generate_component_table(percentages: Dict[str, List[float]]) -> str:
    """生成组件占比表格"""
    rounds = len(percentages.get("soul", []))

    header = "| 组件 | 轮次1 | 轮次2 | 轮次3 | 轮次4 | 轮次5 | 增长趋势 |"
    separator = "|------|-------|-------|-------|-------|-------|----------|"

    lines = [header, separator]

    for component in ["soul", "anchor", "profile", "memory_bank", "current_state", "history", "user_input"]:
        values = percentages.get(component, [])
        row = f"| {component} |"
        for i in range(min(5, rounds)):
            val = values[i] if i < len(values) else 0
            row += f" {val:.1f}% |"

        for i in range(rounds, 5):
            row += " - |"

        if len(values) >= 2:
            trend = values[-1] - values[0]
            trend_str = f"+{trend:.1f}%" if trend > 0 else f"{trend:.1f}%"
            row += f" {trend_str} |"
        else:
            row += " - |"

        lines.append(row)

    return "\n".join(lines)


def generate_ascii_trend_chart(percentages: Dict[str, List[float]]) -> str:
    """生成 ASCII 趋势图"""
    chart = """
```
组件占比趋势 (字符数百分比)

轮次:    1      2      3      4      5
         │      │      │      │      │
"""

    for component in ["memory_bank", "history", "user_input"]:
        values = percentages.get(component, [])
        if not values:
            continue

        bars = ""
        for v in values:
            bar_len = int(v / 5)
            bars += "█" * bar_len + " "

        chart += f"{component:>12}: {bars}\n"

    chart += "```\n"
    return chart


def generate_report(results: List[RoundResult], percentages: Dict[str, List[float]], projection: Dict, fastest: str, problems: List[str]) -> str:
    """生成完整报告"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    report = f"""# Token 基线评估报告

> 生成时间: {now}
> 测试轮次: {len(results)}
> 测试用户: {TEST_USER_ID}
> 测试角色: {TEST_LLM_ID}

---

## 1. 测试配置

| 参数 | 值 |
|------|-----|
| 测试轮数 | {TEST_ROUNDS} |
| 总结触发间隔 | 每 {SUMMARY_INTERVAL} 轮 |
| 使用模型 | DeepSeek (通过 get_chat_model) |

---

## 2. Token 消耗记录

{generate_token_table(results)}

---

## 3. 各组件占比趋势

{generate_component_table(percentages)}

---

## 4. 占比趋势可视化

{generate_ascii_trend_chart(percentages)}

---

## 5. 50轮趋势推断

基于 {len(results)} 轮真实数据推断 50 轮后的情况:

| 指标 | 当前值 (第{len(results)}轮) | 推断值 (第50轮) |
|------|---------------------------|-----------------|
| Memory Bank 条数 | {results[-1].memory_bank_items if results else 0} | {projection.get('projected_memory_bank_items', 'N/A')} |
| History 字符数 | {results[-1].component_sizes.history_msg if results else 0} | {projection.get('projected_history_chars', 'N/A')} |
| Prompt Tokens | {results[-1].token_data.prompt_tokens if results else 0} | {projection.get('projected_50_prompt_tokens', 'N/A')} |

---

## 6. 增长最快组件

**{fastest}**

---

## 7. 问题识别

"""
    if problems:
        for p in problems:
            report += f"- ⚠️ {p}\n"
    else:
        report += "暂无明显问题\n"

    report += """
---

## 8. 优化建议

基于设计文档 `memory_flow_recommended.md` 的建议:

1. **Memory Bank 应改为按需检索** - 当前全量注入最后 5 条，应改为向量检索 + 相关性过滤
2. **建立当前状态层** - 将 current_state 扩展为完整的 current_state (包含 relation_state, current_focus 等)
3. **信息路由机制** - 总结结果应按职责路由，而非一股脑塞入 Memory Bank
4. **Token 预算控制** - 各层应有明确 Token 预算，避免无限增长

---

*此报告由 token_baseline_evaluator.py 自动生成*
"""

    return report


# ==================== 入口点 (任务 7.x) ====================

async def main(rounds: int = TEST_ROUNDS, output_path: str = OUTPUT_PATH) -> None:
    """主入口"""
    logger.info("="*50)
    logger.info("Token 基线评估脚本启动")
    logger.info(f"测试轮数: {rounds}, 输出路径: {output_path}")
    logger.info("="*50)

    from app.core.db.redis_client import redis_client

    initialize_test_redis_data(redis_client)

    try:
        results = await run_evaluation_loop(rounds, redis_client, TEST_USER_ID, TEST_LLM_ID)

        percentages = calculate_component_percentages(results)
        projection = project_50_round_trend(results)
        fastest = identify_fastest_growing_component(percentages)
        problems = identify_problems(results, percentages, projection)

        report = generate_report(results, percentages, projection, fastest, problems)

        report_path = Path(project_root) / output_path
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report, encoding="utf-8")

        logger.info(f"报告已生成: {report_path}")

        print("\n" + "="*50)
        print("评估摘要:")
        print(f"  - 总测试轮次: {len(results)}")
        if results:
            print(f"  - 最后轮 Prompt Tokens: {results[-1].token_data.prompt_tokens}")
            print(f"  - Memory Bank 最终条数: {results[-1].memory_bank_items}")
        print(f"  - 增长最快组件: {fastest}")
        print(f"  - 报告路径: {report_path}")
        print("="*50 + "\n")

    finally:
        if CLEANUP_AFTER_TEST:
            cleanup_test_redis_data(redis_client)


def parse_args():
    """解析命令行参数"""
    import argparse

    parser = argparse.ArgumentParser(description="Token 基线评估脚本")
    parser.add_argument("--rounds", type=int, default=TEST_ROUNDS, help="测试轮数")
    parser.add_argument("--output", type=str, default=OUTPUT_PATH, help="报告输出路径")
    parser.add_argument("--no-cleanup", action="store_true", help="不清理测试数据")

    args = parser.parse_args()

    global CLEANUP_AFTER_TEST
    CLEANUP_AFTER_TEST = not args.no_cleanup

    return args.rounds, args.output


if __name__ == "__main__":
    rounds, output = parse_args()
    asyncio.run(main(rounds, output))