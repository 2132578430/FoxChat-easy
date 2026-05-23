from enum import Enum


class MsgStatusConstant(Enum):
    RAG_MESSAGE_EXAM_ERROR = (20000, "rag消息校验错误")
    CHAT_MSG_SERVICE_ERROR = (20001, "chat_msg_service服务异常")
    UNKNOWN_ROLE_ERROR = (20002, "未知消息角色")

    def __init__(self, code: int, msg: str):
        self.code = code
        self.msg = msg