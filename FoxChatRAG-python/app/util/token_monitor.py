"""
Token 消耗实时监控工具

用途：
1. 记录每次 LLM 调用的 token 消耗
2. 测试不同 memory_bank 条数对 token 的影响
3. 输出各组件占比分析

使用方法：
1. 在 chat_msg_service.py 中导入：from app.util.token_monitor import token_monitor
2. 替换 _invoke_llm 调用：chat_response = await token_monitor.traced_invoke_llm(...)
3. 测试不同 memory_bank 条数：修改 MAX_MEMORY_BANK_ITEMS 常量
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Any
from dataclasses import dataclass, field, asdict

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger


@dataclass
class TokenRecord:
    """单次调用 token 记录"""
    timestamp: str
    round_number: int
    user_id: str
    llm_id: str
    user_input: str

    # Token 消耗
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    # Memory Bank 相关
    memory_bank_total_items: int = 0  # 总条数
    memory_bank_injected_items: int = 0  # 注入条数
    memory_bank_chars: int = 0  # 字符数

    # 各组件字符数
    soul_chars: int = 0
    anchor_chars: int = 0
    profile_chars: int = 0  # 包含 A2 边界 + user_profile
    current_state_chars: int = 0  # 当前状态字符数
    history_chars: int = 0  # 历史消息字符数
    user_input_chars: int = 0
    historical_context_chars: int = 0  # 历史上下文（memory_bank 或向量检索结果）

    # 向量检索相关
    retrieval_triggered: bool = False  # 是否触发向量检索
    retrieval_items: int = 0  # 检索返回条数
    retrieval_chars: int = 0  # 检索结果字符数

    # 响应
    response_chars: int = 0


@dataclass
class TokenMonitorConfig:
    """监控配置"""
    max_memory_bank_items: int = 5  # Memory Bank 最大注入条数（可调整测试）
    enable_retrieval: bool = True  # 是否启用向量检索
    log_to_file: bool = True  # 是否记录到文件
    log_file_path: str = "logs/token_monitor.json"  # 日志文件路径


class TokenMonitor:
    """Token 消耗监控器"""

    def __init__(self, config: Optional[TokenMonitorConfig] = None):
        self.config = config or TokenMonitorConfig()
        self.records: List[TokenRecord] = []
        self._round_counter = 0

    def set_memory_bank_limit(self, limit: int):
        """动态设置 memory_bank 注入条数（测试用）"""
        self.config.max_memory_bank_items = limit
        logger.info(f"【Token监控】Memory Bank 注入条数调整为: {limit}")

    def parse_memory_bank_with_limit(self, json_str: str) -> tuple[str, int]:
        """
        解析 Memory Bank，按配置限制注入条数

        Returns:
            (摘要文本, 注入条数)
        """
        if not json_str:
            return "", 0

        try:
            bank = json.loads(json_str)
            if not isinstance(bank, list) or not bank:
                return "", 0

            # 按配置限制条数
            limit = self.config.max_memory_bank_items
            recent_items = bank[-limit:] if len(bank) > limit else bank

            lines = []
            for item in recent_items:
                time_val = item.get("time", "某时")
                content_val = item.get("content", "")
                type_val = item.get("type", "event")
                lines.append(f"- [{time_val}]（{type_val}）{content_val}")

            summary = "\n".join(lines)
            return summary, len(recent_items)

        except json.JSONDecodeError:
            logger.warning("memory_bank JSON解析失败")
            return "", 0

    async def traced_invoke_llm(
        self,
        payload: Any,
        user_id: str,
        llm_id: str,
        memory_bank_json: str,
        retrieval_result: Optional[str] = None,
        retrieval_triggered: bool = False,
    ) -> tuple[str, TokenRecord]:
        """
        包装 LLM 调用，记录 token 消耗

        Args:
            payload: PromptPayload 对象
            user_id: 用户 ID
            llm_id: 模型 ID
            memory_bank_json: Memory Bank 原始 JSON
            retrieval_result: 向量检索结果文本
            retrieval_triggered: 是否触发了向量检索

        Returns:
            (响应文本, token记录)
        """
        from app.core.llm_model.model import LLM_MAP, _resolve_model_name
        from app.service.chat.prompt_payload_builder import payload_to_invoke_dict

        self._round_counter += 1

        # 解析 memory_bank（按配置限制条数）
        memory_bank_summary, injected_items = self.parse_memory_bank_with_limit(memory_bank_json)

        # 计算 memory_bank 总条数
        memory_bank_total = 0
        if memory_bank_json:
            try:
                bank = json.loads(memory_bank_json)
                memory_bank_total = len(bank) if isinstance(bank, list) else 0
            except:
                pass

        # 计算各组件字符数
        record = TokenRecord(
            timestamp=datetime.now().isoformat(),
            round_number=self._round_counter,
            user_id=user_id,
            llm_id=llm_id,
            user_input=payload.user_message[:50] + "..." if len(payload.user_message) > 50 else payload.user_message,

            memory_bank_total_items=memory_bank_total,
            memory_bank_injected_items=injected_items,
            memory_bank_chars=len(memory_bank_summary),

            soul_chars=len(payload.static_anchors or ""),
            profile_chars=len(payload.user_profile_summary or ""),  # A2 边界 + user_profile
            current_state_chars=len(payload.current_state or ""),
            history_chars=len(str(payload.history_msg) or ""),
            user_input_chars=len(payload.user_message),
            historical_context_chars=len(payload.historical_context or ""),

            retrieval_triggered=retrieval_triggered,
            retrieval_items=0,
            retrieval_chars=len(retrieval_result or ""),
        )

        # 获取模型（使用后台任务接口）
        model_name = _resolve_model_name("default")
        llm = LLM_MAP.get(model_name)

        # 构建调用参数（使用限制后的 memory_bank）
        invoke_dict = payload_to_invoke_dict(payload)
        if memory_bank_summary:
            invoke_dict["memory_bank_summary"] = memory_bank_summary

        # 调用 LLM（不使用 StrOutputParser，保留 metadata）
        chain = llm
        aimessage = await chain.ainvoke(invoke_dict)

        # 提取响应文本
        response_text = aimessage.content if hasattr(aimessage, 'content') else str(aimessage)
        record.response_chars = len(response_text)

        # 提取 token 数据
        if hasattr(aimessage, 'response_metadata'):
            usage = aimessage.response_metadata.get('token_usage', {})
            if usage:
                record.prompt_tokens = usage.get('prompt_tokens', 0)
                record.completion_tokens = usage.get('completion_tokens', 0)
                record.total_tokens = usage.get('total_tokens', 0)

        # 备用方案
        if record.total_tokens == 0 and hasattr(aimessage, 'usage_metadata'):
            meta = aimessage.usage_metadata
            record.prompt_tokens = meta.get('input_tokens', 0)
            record.completion_tokens = meta.get('output_tokens', 0)
            record.total_tokens = record.prompt_tokens + record.completion_tokens

        # 记录
        self.records.append(record)

        # 输出日志
        logger.info(
            f"【Token监控】轮次{record.round_number}: "
            f"Prompt={record.prompt_tokens}, "
            f"Completion={record.completion_tokens}, "
            f"Total={record.total_tokens}, "
            f"MB注入={record.memory_bank_injected_items}/{record.memory_bank_total_items}, "
            f"检索={record.retrieval_triggered}"
        )

        # 写入文件
        if self.config.log_to_file:
            self._write_record(record)

        return response_text, record

    def _write_record(self, record: TokenRecord):
        """写入单条记录到日志文件"""
        import os
        log_dir = Path(self.config.log_file_path).parent
        log_dir.mkdir(parents=True, exist_ok=True)

        with open(self.config.log_file_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")

    def generate_report(self) -> str:
        """生成分析报告"""
        if not self.records:
            return "暂无记录"

        # 统计
        total_prompt = sum(r.prompt_tokens for r in self.records)
        total_completion = sum(r.completion_tokens for r in self.records)
        avg_mb_items = sum(r.memory_bank_injected_items for r in self.records) / len(self.records)

        # 各组件占比（取最后一次记录）
        last = self.records[-1]
        total_chars = (
            last.soul_chars + last.profile_chars +
            last.current_state_chars +
            last.history_chars + last.user_input_chars +
            last.historical_context_chars
        )

        report = f"""
# Token 消耗监控报告

## 测试配置
- Memory Bank 注入条数限制: {self.config.max_memory_bank_items}
- 向量检索启用: {self.config.enable_retrieval}
- 测试轮数: {len(self.records)}

## Token 消耗汇总
- 总 Prompt Tokens: {total_prompt}
- 总 Completion Tokens: {total_completion}
- 平均 Prompt Tokens: {total_prompt / len(self.records):.1f}
- 平均 Memory Bank 注入条数: {avg_mb_items:.1f}

## 最后一轮各组件占比（字符数）
- Soul/Anchor: {last.soul_chars} ({last.soul_chars/total_chars*100:.1f}%)
- Profile(A2+画像): {last.profile_chars} ({last.profile_chars/total_chars*100:.1f}%)
- 当前状态: {last.current_state_chars} ({last.current_state_chars/total_chars*100:.1f}%)
- 历史上下文(MB/检索): {last.historical_context_chars} ({last.historical_context_chars/total_chars*100:.1f}%)
- 历史消息: {last.history_chars} ({last.history_chars/total_chars*100:.1f}%)
- 用户输入: {last.user_input_chars} ({last.user_input_chars/total_chars*100:.1f}%)
- Memory Bank 注入: {last.memory_bank_chars} ({last.memory_bank_chars/total_chars*100:.1f}%)

## 详细记录
"""
        for r in self.records[-5:]:  # 最近5轮
            report += f"\n### 轮次 {r.round_number}\n"
            report += f"- Prompt: {r.prompt_tokens}, Completion: {r.completion_tokens}\n"
            report += f"- Memory Bank: 注入 {r.memory_bank_injected_items}/{r.memory_bank_total_items} 条\n"
            report += f"- 向量检索: {r.retrieval_triggered} ({r.retrieval_items}条)\n"

        return report


# 全局单例
token_monitor = TokenMonitor()


# 测试脚本
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Token 消耗监控工具")
    parser.add_argument("--limit", type=int, default=5, help="Memory Bank 注入条数限制")
    parser.add_argument("--report", action="store_true", help="生成分析报告")

    args = parser.parse_args()

    monitor = TokenMonitor(TokenMonitorConfig(max_memory_bank_items=args.limit))

    print(f"Token 监控工具已配置:")
    print(f"  - Memory Bank 注入条数限制: {args.limit}")
    print(f"  - 日志文件: {monitor.config.log_file_path}")
    print(f"\n使用方法:")
    print(f"  1. 在代码中导入: from app.util.token_monitor import token_monitor")
    print(f"  2. 调整注入条数: token_monitor.set_memory_bank_limit(10)")
    print(f"  3. 查看报告: print(token_monitor.generate_report())")

    if args.report and monitor.records:
        print(monitor.generate_report())