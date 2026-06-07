"""
流式标签解析器

职责：接收 LLM 逐 token 输出，实时检测 <action> 标签边界，
产出带 block_type 标注的 StreamToken。

工作原理：
- 字符缓冲区 + 状态机（TEXT / INSIDE_ACTION）
- TEXT 状态：积累文本 → 检测到 <action> → 推送前面文本 → 切 INSIDE_ACTION
- INSIDE_ACTION 状态：积累动作文本 → 检测到 </action> → 推送动作内容 → 切回 TEXT
- 标签字符（"<action>" "</action>"）被丢弃，不推送给前端
- 残缺标签前缀（如 "<act"）保留在 buffer 等下一个 token 补全

Author: bedFox
"""

import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List


class ParseState(Enum):
    TEXT = auto()
    INSIDE_ACTION = auto()


@dataclass
class StreamToken:
    """流式解析器产出的最小推送单元"""
    content: str               # 文本内容（text类型=单token，action类型=完整动作文本）
    block_type: str = "text"   # "text" | "action"
    is_block_start: bool = False
    is_block_end: bool = False


# 只识别 action 标签
_OPEN_TAG  = "<action>"
_CLOSE_TAG = "</action>"


class StreamingTagParser:
    """
    流式标签解析器
    """

    def __init__(self):
        self.buffer = ""
        self.state = ParseState.TEXT
        self.block_seq: int = 0

    def feed(self, token: str) -> List[StreamToken]:
        """
        喂入一个 LLM token，返回可以推送的 StreamToken 列表。
        token 可能包含不完整的标签，解析器会缓冲等待。
        """
        if not token:
            return []
        self.buffer += token
        results: List[StreamToken] = []
        self._process(results)
        return results

    def flush(self) -> List[StreamToken]:
        """
        流结束时调用，刷新缓冲区残留字符。
        """
        results: List[StreamToken] = []
        if self.buffer:
            block_type = "action" if self.state == ParseState.INSIDE_ACTION else "text"
            results.append(StreamToken(
                content=self.buffer,
                block_type=block_type,
                is_block_end=True,
            ))
            self.buffer = ""
        return results

    # 状态机核心
    def _process(self, results: List[StreamToken]) -> None:
        """循环处理 buffer，直到无法继续（需要更多字符）"""
        while self.buffer:
            if self.state == ParseState.TEXT:
                if not self._try_enter_action(results):
                    return  # buffer 不足，等下一批
            elif self.state == ParseState.INSIDE_ACTION:
                if not self._try_exit_action(results):
                    return

    def _try_enter_action(self, results: List[StreamToken]) -> bool:
        """TEXT 状态：尝试找到 <action> 开始标签"""
        idx = self.buffer.find(_OPEN_TAG)
        if idx == -1:
            # 没有完整开始标签
            # → 安全推送 buffer 前缀（保留末尾可能在构建 "<action" 的字符）
            safe_end = self._safe_text_cut()
            if safe_end > 0:
                results.append(StreamToken(
                    content=self.buffer[:safe_end],
                    block_type="text",
                    is_block_start=(self.block_seq == 0),
                ))
                self.buffer = self.buffer[safe_end:]
                self.block_seq += 1
            return False  # buffer 耗尽或只剩残缺标签前缀

        # 找到了 <action>
        if idx > 0:
            # 标签前的文本 → 推送
            results.append(StreamToken(
                content=self.buffer[:idx],
                block_type="text",
                is_block_start=(self.block_seq == 0),
            ))
            self.block_seq += 1

        # 切到 INSIDE_ACTION，丢弃 "<action>"
        self.buffer = self.buffer[idx + len(_OPEN_TAG):]
        self.state = ParseState.INSIDE_ACTION
        return True

    def _try_exit_action(self, results: List[StreamToken]) -> bool:
        """INSIDE_ACTION 状态：尝试找到 </action> 结束标签"""
        idx = self.buffer.find(_CLOSE_TAG)
        if idx == -1:
            # 没有结束标签
            # → 安全推送 buffer 前缀（保留末尾可能在构建 "</action" 的字符）
            safe_end = self._safe_action_cut()
            if safe_end > 0:
                results.append(StreamToken(
                    content=self.buffer[:safe_end],
                    block_type="action",
                    is_block_start=True,
                ))
                self.buffer = self.buffer[safe_end:]
                self.block_seq += 1
            return False

        # 找到了 </action>
        if idx > 0:
            results.append(StreamToken(
                content=self.buffer[:idx],
                block_type="action",
                is_block_start=True,
                is_block_end=True,
            ))
            self.block_seq += 1

        # 切回 TEXT，丢弃 "</action>"
        self.buffer = self.buffer[idx + len(_CLOSE_TAG):]
        self.state = ParseState.TEXT
        return True

    # ── 安全截断：防止残缺标签泄露 ────────────────

    def _safe_text_cut(self) -> int:
        """
        TEXT 状态下安全截断位置。
        找到最后一个 '<'，如果它后面可能构成 <action> 标签则保留。
        """
        last_lt = self.buffer.rfind("<")
        if last_lt == -1:
            return len(self.buffer)
        # 保留从 '<' 开始的字符，等补全
        return last_lt

    def _safe_action_cut(self) -> int:
        """
        INSIDE_ACTION 状态下安全截断位置。
        找到最后一个 '<'，如果它后面可能构成 </action> 标签则保留。
        """
        last_lt = self.buffer.rfind("<")
        if last_lt == -1:
            return len(self.buffer)
        # 保留从 '<' 开始的字符（最大可能标签长度 = len("</action>") + 余量）
        remaining = self.buffer[last_lt:]
        if len(remaining) < 12 and _CLOSE_TAG.startswith(remaining):
            return last_lt
        return len(self.buffer)
