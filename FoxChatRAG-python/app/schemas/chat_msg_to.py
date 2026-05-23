from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class ChatMsgTo(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    userId: str = Field(validation_alias=AliasChoices("userId", "userName"))
    msgContent: str
    llmId: str
