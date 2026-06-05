"""
条件路由函数

读取 ChatState 中的 intent_result，决定走检索路径还是跳过检索。
"""

from app.service.chat.graph.state import ChatState
from loguru import logger


def need_retrieval(state: ChatState) -> str:
    """根据意图分类结果返回下一步节点名"""
    intent_result = state.get("intent_result")
    if intent_result and intent_result.get("skip"):
        logger.debug(f"[Graph] need_retrieval → skip_retrieval")
        return "skip_retrieval"
    logger.debug(f"[Graph] need_retrieval → retrieve")
    return "retrieve"
