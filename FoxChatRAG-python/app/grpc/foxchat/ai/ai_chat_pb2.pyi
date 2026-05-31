from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class ChatRequest(_message.Message):
    __slots__ = ("user_id", "llm_id", "msg_content")
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    LLM_ID_FIELD_NUMBER: _ClassVar[int]
    MSG_CONTENT_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    llm_id: str
    msg_content: str
    def __init__(self, user_id: _Optional[str] = ..., llm_id: _Optional[str] = ..., msg_content: _Optional[str] = ...) -> None: ...

class ChatResponse(_message.Message):
    __slots__ = ("content", "is_final", "block_type", "is_block_start", "is_block_end", "emotion", "error_code", "error_msg", "sequence")
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    IS_FINAL_FIELD_NUMBER: _ClassVar[int]
    BLOCK_TYPE_FIELD_NUMBER: _ClassVar[int]
    IS_BLOCK_START_FIELD_NUMBER: _ClassVar[int]
    IS_BLOCK_END_FIELD_NUMBER: _ClassVar[int]
    EMOTION_FIELD_NUMBER: _ClassVar[int]
    ERROR_CODE_FIELD_NUMBER: _ClassVar[int]
    ERROR_MSG_FIELD_NUMBER: _ClassVar[int]
    SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    content: str
    is_final: bool
    block_type: str
    is_block_start: bool
    is_block_end: bool
    emotion: str
    error_code: int
    error_msg: str
    sequence: int
    def __init__(self, content: _Optional[str] = ..., is_final: bool = ..., block_type: _Optional[str] = ..., is_block_start: bool = ..., is_block_end: bool = ..., emotion: _Optional[str] = ..., error_code: _Optional[int] = ..., error_msg: _Optional[str] = ..., sequence: _Optional[int] = ...) -> None: ...

class DeleteRequest(_message.Message):
    __slots__ = ("user_id", "llm_id")
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    LLM_ID_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    llm_id: str
    def __init__(self, user_id: _Optional[str] = ..., llm_id: _Optional[str] = ...) -> None: ...

class DeleteResponse(_message.Message):
    __slots__ = ("success", "message")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    def __init__(self, success: bool = ..., message: _Optional[str] = ...) -> None: ...
