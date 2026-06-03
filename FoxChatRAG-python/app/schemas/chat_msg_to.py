from pydantic import BaseModel


class ChatMsgTo(BaseModel):
    userId: str
    msgContent: str
    llmId: str
