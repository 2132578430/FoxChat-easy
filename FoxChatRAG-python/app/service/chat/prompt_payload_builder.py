"""
统一 Prompt Payload 构建器

阶段6收敛：在 LLM 调用前一次性决定：
- 哪些块注入
- 注入顺序
- 空块是否省略
- 跨层去重
- 冲突优先级

职责：
- 接收各层原始内容
- 执行空块抑制
- 执行跨层去重
- 执行冲突优先级
- 输出最终 payload 字典

使用方式：
    from app.service.chat.prompt_payload_builder import build_prompt_payload

    payload = build_prompt_payload(
        static_anchors=...,
        user_profile_summary=...,
        historical_context=...,
        current_state=...,
        recent_messages=...,
        user_input=...,
    )
"""

from dataclasses import dataclass
from typing import List, Optional, Set
from loguru import logger


@dataclass
class PromptPayload:
    """最终 Prompt Payload 结构"""
    static_anchors: str
    user_profile_summary: str
    historical_context: str
    current_state: str
    history_msg: List  # LangChain BaseMessage list
    user_message: str

    # 元信息（调试用）
    blocks_injected: List[str]  # 实际注入的块名
    blocks_omitted: List[str]   # 空块省略的块名
    duplicates_removed: List[str]  # 被去重的内容摘要


def _is_empty_block(content: str) -> bool:
    """判断块内容是否为空（应省略）"""
    if not content:
        return True
    # 去除空白后判断
    stripped = content.strip()
    if not stripped:
        return True
    # 不应注入"默认占位文本"
    # 当前已知默认值：
    # - "- 情绪：平静\n- 关系：中性\n- 互动方式：闲聊"
    # - 空的标题行如 "【硬边界】\n\n"
    if stripped in ("", "无", "暂无", "未提及"):
        return True
    return False


def _extract_keywords(text: str) -> Set[str]:
    """从文本中提取关键词（简化版：字符级分词）"""
    if not text:
        return set()
    # 中文简化处理：按字符分
    # 实际应用中可用更精细的分词器
    keywords = set()
    # 提取明显的词组（2-4个字符的组合）
    for i in range(len(text)):
        for length in range(2, 5):
            if i + length <= len(text):
                segment = text[i:i+length].strip()
                if segment and not segment.isspace():
                    keywords.add(segment)
    return keywords


def _calculate_overlap(text1: str, text2: str) -> float:
    """计算两段文本的重叠度"""
    if not text1 or not text2:
        return 0.0
    kw1 = _extract_keywords(text1)
    kw2 = _extract_keywords(text2)
    if not kw1 or not kw2:
        return 0.0
    overlap = len(kw1 & kw2)
    union = len(kw1 | kw2)
    return overlap / union if union > 0 else 0.0


def _suppress_duplicates_across_layers(
    a2_content: str,
    b_content: str,
    c_content: str,
    recent_messages: List[str],
    overlap_threshold: float = 0.6,
) -> tuple[str, str, str, List[str]]:
    """
    跨层去重：优先保留高层信息，抑制低层重复

    优先级: A2 > B > C > D (recent_messages)

    Args:
        a2_content: A2 层内容（用户画像+硬边界）
        b_content: B 层内容（当前状态）
        c_content: C 层内容（历史上下文）
        recent_messages: D 层内容（最近窗口）
        overlap_threshold: 重叠阈值

    Returns:
        (a2_content, b_content_suppressed, c_content_suppressed, removed_summary)
    """
    removed = []

    # 1. B 层与 A2 层去重
    b_suppressed = b_content
    if a2_content and b_content:
        overlap = _calculate_overlap(a2_content, b_content)
        if overlap >= overlap_threshold:
            # B 层与 A2 高重叠，抑制 B 层中的重复部分
            # 简化处理：若整体高度重叠，可能 B 层完全被 A2 覆盖
            # 但通常 B 层是状态摘要，A2 是画像/边界，不会完全重叠
            # 这里只做标记，不做实际删减（需要更精细的行级去重）
            logger.debug(f"【跨层去重】B层与A2重叠度 {overlap:.2f}，可能存在重复表达")
            # 实际去重：去掉 B 层中与 A2 关键词高度重叠的行
            b_lines = b_content.split("\n")
            a2_keywords = _extract_keywords(a2_content)
            filtered_lines = []
            for line in b_lines:
                line_kw = _extract_keywords(line)
                line_overlap = len(line_kw & a2_keywords) / max(len(line_kw), 1) if line_kw else 0
                if line_overlap < 0.5:  # 行级阈值
                    filtered_lines.append(line)
                else:
                    removed.append(f"B→A2: {line[:30]}...")
            b_suppressed = "\n".join(filtered_lines) if filtered_lines else ""

    # 2. C 层与 D 层（最近窗口）去重
    c_suppressed = c_content
    if c_content and recent_messages:
        recent_text = "\n".join(recent_messages[-6:])  # 最近6条
        overlap = _calculate_overlap(c_content, recent_text)
        if overlap >= overlap_threshold:
            logger.debug(f"【跨层去重】C层与D层重叠度 {overlap:.2f}，可能存在重复")
            # 历史事件与最近窗口去重已在 retrieval 层处理
            # 这里只做二次检查

    # 3. C 层与 A2/B 层去重
    if c_content and (a2_content or b_suppressed):
        upper_content = (a2_content + "\n" + b_suppressed).strip()
        if upper_content:
            overlap = _calculate_overlap(c_content, upper_content)
            if overlap >= overlap_threshold:
                logger.debug(f"【跨层去重】C层与A2/B重叠度 {overlap:.2f}")
                # C 层是历史，A2/B 是当前约束，通常不应完全抑制 C
                # 只标记，不强制删除

    return a2_content, b_suppressed, c_suppressed, removed


def _enforce_conflict_priority(
    a2_content: str,
    b_content: str,
    c_content: str,
) -> tuple[str, str, str]:
    """
    冲突优先级强制执行

    规则: A2 > B > C

    当内容存在明确冲突时，低层内容应被标记或抑制。
    V2升级：实现关键词模式匹配的冲突检测

    处理策略：
    - 检测 A2 边界关键词（不要/禁止/避免/不许/不能）
    - 检查 B/C 是否包含与边界直接相反的内容
    - 对冲突内容添加警告标记或移除
    """
    if not a2_content:
        return a2_content, b_content, c_content

    # 1. 提取 A2 边界约束
    boundary_markers = ["不要", "禁止", "避免", "不许", "不能", "拒绝"]
    extracted_boundaries = []

    for line in a2_content.split("\n"):
        for marker in boundary_markers:
            if marker in line:
                # 提取边界内容（去掉标记词后的部分）
                boundary_content = line.split(marker)[-1].strip()
                if boundary_content:
                    extracted_boundaries.append((marker, boundary_content))
                    logger.debug(f"【冲突检测】提取边界: {marker} {boundary_content}")

    if not extracted_boundaries:
        return a2_content, b_content, c_content

    # 2. 检查 B 层冲突
    b_suppressed = b_content
    b_conflicts = []

    for marker, boundary in extracted_boundaries:
        # 检测 B 中是否有与边界相反的表达
        # 简化：如果边界关键词的直接反面出现在 B 中
        opposite_patterns = {
            "不要": ["要", "应该", "可以", "请"],
            "禁止": ["允许", "可以", "许可"],
            "避免": ["使用", "采用", "应用"],
            "不许": ["允许", "可以"],
            "不能": ["可以", "能", "应该"],
            "拒绝": ["接受", "同意", "答应"],
        }

        opposites = opposite_patterns.get(marker, [])
        for opp in opposites:
            if opp in b_content and boundary in b_content:
                # 检测到冲突
                b_conflicts.append((marker, boundary, opp))

    if b_conflicts:
        # 移除 B 中的冲突行
        b_lines = b_content.split("\n")
        filtered_lines = []
        for line in b_lines:
            is_conflict = False
            for marker, boundary, opp in b_conflicts:
                if opp in line and boundary in line:
                    is_conflict = True
                    logger.warning(f"【冲突抑制】B层冲突: '{line[:30]}...' 与 A2边界 '{marker} {boundary}' 冲突，已移除")
                    break
            if not is_conflict:
                filtered_lines.append(line)
        b_suppressed = "\n".join(filtered_lines) if filtered_lines else ""

    # 3. 检查 C 层冲突（历史事件通常不应被抑制，但需添加警告）
    c_warnings = []
    for marker, boundary in extracted_boundaries:
        # 检测 C 中是否有违反边界的建议
        if boundary in c_content:
            # C 中提到了边界相关内容，但可能不是冲突
            # 只做标记，不抑制
            c_warnings.append(f"[注意：该内容可能与A2边界 '{marker} {boundary}' 相关]")

    c_final = c_content
    if c_warnings:
        # 在 C 块开头添加警告
        warning_block = "\n".join(c_warnings[:2])  # 最多 2 条警告
        c_final = f"{warning_block}\n{c_content}"
        logger.info(f"【冲突标记】C层添加 {len(c_warnings)} 条边界相关警告")

    return a2_content, b_suppressed, c_final


def build_prompt_payload(
    static_anchors: str,
    user_profile_summary: str,
    historical_context: str,
    current_state: str,
    history_msg: List,
    user_message: str,
    recent_messages: Optional[List[str]] = None,
    enable_dedup: bool = True,
    enable_conflict_priority: bool = True,
) -> PromptPayload:
    """
    构建最终 Prompt Payload

    Args:
        static_anchors: A1 静态锚点内容
        user_profile_summary: A2 用户画像+硬边界内容
        historical_context: C 历史上下文内容
        current_state: B 当前状态内容
        history_msg: D 最近窗口消息（LangChain BaseMessage list）
        user_message: 用户当前输入
        recent_messages: 最近窗口原始消息列表（用于去重）
        enable_dedup: 是否启用跨层去重
        enable_conflict_priority: 是否启用冲突优先级

    Returns:
        PromptPayload 对象
    """
    blocks_injected = []
    blocks_omitted = []
    duplicates_removed = []

    # 1. 空块抑制
    final_static_anchors = static_anchors
    if _is_empty_block(static_anchors):
        final_static_anchors = ""
        blocks_omitted.append("static_anchors")
        logger.debug("【空块抑制】A1 static_anchors 为空，已省略")
    else:
        blocks_injected.append("static_anchors")

    final_user_profile = user_profile_summary
    if _is_empty_block(user_profile_summary):
        final_user_profile = ""
        blocks_omitted.append("user_profile_summary")
        logger.debug("【空块抑制】A2 user_profile_summary 为空，已省略")
    else:
        blocks_injected.append("user_profile_summary")

    final_historical_context = historical_context
    if _is_empty_block(historical_context):
        final_historical_context = ""
        blocks_omitted.append("historical_context")
        logger.debug("【空块抑制】C historical_context 为空，已省略")
    else:
        blocks_injected.append("historical_context")

    final_current_state = current_state
    if _is_empty_block(current_state):
        final_current_state = ""
        blocks_omitted.append("current_state")
        logger.debug("【空块抑制】B current_state 为空，已省略")
    else:
        blocks_injected.append("current_state")

    # 2. 跨层去重
    if enable_dedup and (final_user_profile or final_current_state or final_historical_context):
        final_user_profile, final_current_state, final_historical_context, duplicates_removed = \
            _suppress_duplicates_across_layers(
                final_user_profile,
                final_current_state,
                final_historical_context,
                recent_messages or [],
            )
        if duplicates_removed:
            logger.info(f"【跨层去重】移除 {len(duplicates_removed)} 处重复")

    # 3. 冲突优先级
    if enable_conflict_priority:
        final_user_profile, final_current_state, final_historical_context = \
            _enforce_conflict_priority(
                final_user_profile,
                final_current_state,
                final_historical_context,
            )

    # 4. 最终 payload
    payload = PromptPayload(
        static_anchors=final_static_anchors,
        user_profile_summary=final_user_profile,
        historical_context=final_historical_context,
        current_state=final_current_state,
        history_msg=history_msg,
        user_message=user_message,
        blocks_injected=blocks_injected,
        blocks_omitted=blocks_omitted,
        duplicates_removed=duplicates_removed,
    )

    # 5. 日志输出（调试）
    logger.debug(f"【Payload构建】注入块: {blocks_injected}, 空块省略: {blocks_omitted}")

    return payload


def payload_to_invoke_dict(payload: PromptPayload) -> dict:
    """
    将 PromptPayload 转换为 chain.ainvoke() 所需的字典格式
    """
    return {
        "static_anchors": payload.static_anchors,
        "user_profile_summary": payload.user_profile_summary,
        "historical_context": payload.historical_context,
        "current_state": payload.current_state,
        "history_msg": payload.history_msg,
        "user_message": payload.user_message,
    }