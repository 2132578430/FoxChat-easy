from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.params import Query
from loguru import logger

from app.schemas import ChatMsgTo
from app.schemas.M import M
from app.service.chat import clear_chat_memory
from app.service.chat.session_lock import acquire_session_lock, release_session_lock
from app.service.chat.graph.graph import main_graph
from app.service import super_chat_service

chat_router = APIRouter(prefix="/chat", tags=["chat"])


@chat_router.post("/msg")
async def chat_msg(chat_msg_to: ChatMsgTo, background_tasks: BackgroundTasks, request: Request):
    """
    处理聊天消息（需要验证用户配置）

    流程：
    1. 验证 llm_config 是否完整（必须有 5 个场景配置）
    2. 如果不完整，返回错误 15001
    3. 如果完整，调用聊天流程
    """
    logger.info(f"接收到消息：{chat_msg_to}")

    user_id = chat_msg_to.userId
    llm_id = chat_msg_to.llmId

    # 验证配置完整性
    from app.core.db.mysql_client import async_session_local
    from app.service.llm_config_service import validate_config_count, get_missing_scenarios

    async with async_session_local() as db:
        is_valid = await validate_config_count(llm_id, db)

        if not is_valid:
            missing_scenarios = await get_missing_scenarios(llm_id, db)
            logger.warning(f"【配置不完整】llm_id={llm_id}, missing={missing_scenarios}")

            # 返回错误 15001（使用 M 格式）
            return {
                "code": 15001,
                "msg": "未完成所有模型配置，请前往设置页面完成配置",
                "data": {"missing_scenarios": missing_scenarios}
            }

    # 配置完整，继续聊天流程
    initial_state = {
        "user_id": user_id,
        "llm_id": llm_id,
        "msg_content": chat_msg_to.msgContent,
    }
    config = {"configurable": {"thread_id": f"{user_id}:{llm_id}"}}

    lock = acquire_session_lock(user_id, llm_id)
    try:
        result = await main_graph.ainvoke(initial_state, config)
        response = {
            "blocks": result.get("blocks", []),
            "emotion": result.get("emotion", "neutral"),
        }
        logger.info(f"收到回复：{response}")
        return M.get_msg(response)
    finally:
        release_session_lock(lock)


@chat_router.post("/superMsg")
async def super_chat_msg(chat_msg_to: ChatMsgTo, background_tasks: BackgroundTasks, request: Request):
    logger.info(f"【导演模式】API层接收到请求：user_id={chat_msg_to.user_id}, llm_id={chat_msg_to.llm_id}, msg_content={chat_msg_to.msg_content}")

    result = await super_chat_service.director_mode_chat(
        user_id=chat_msg_to.userId,
        llm_id=chat_msg_to.llmId,
        msg_content=chat_msg_to.msgContent,
        background_tasks=background_tasks
    )

    logger.info(f"【导演模式】API层返回结果：{result}")
    return M.get_msg(result)


@chat_router.post("/delete")
async def chat_delete(
        user_id: str = Query(..., alias="userId"),
        llm_id: str = Query(..., alias="llmId")
):
    await clear_chat_memory(user_id, llm_id)
