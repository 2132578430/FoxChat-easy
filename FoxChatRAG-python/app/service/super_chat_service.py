from typing import List
from loguru import logger
from app.schemas import MessageBlock


async def director_mode_chat(
    user_id: str,
    llm_id: str,
    msg_content: str,
    background_tasks
) -> List[MessageBlock]:
    """
    导演模式聊天处理函数

    Args:
        user_id: 用户ID
        llm_id: LLM ID
        msg_content: 用户消息内容
        background_tasks: FastAPI 后台任务对象

    Returns:
        消息块列表（结构化回复）

    TODO:
        - 实现导演模式的业务逻辑
        - 调用AI模型生成回复
        - 处理记忆和上下文
    """
    logger.info(f"【导演模式】director_mode_chat 被调用")
    logger.info(f"【导演模式】参数: user_id={user_id}, llm_id={llm_id}, msg_content={msg_content}")

    # TODO: 实现导演模式业务逻辑
    # 1. 加载用户记忆和画像
    # 2. 调用导演模式专用的AI提示词
    # 3. 生成结构化回复
    # 4. 更新记忆和事件

    # 返回空列表占位，逻辑待实现
    return []
