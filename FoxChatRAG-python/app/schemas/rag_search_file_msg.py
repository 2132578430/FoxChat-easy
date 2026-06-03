from pydantic import BaseModel


class RagSearchFileMsg(BaseModel):
    msg: str
    userId: str


