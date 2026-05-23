from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class RagSearchFileMsg(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    msg: str
    userId: str = Field(validation_alias=AliasChoices("userId", "userName"))


