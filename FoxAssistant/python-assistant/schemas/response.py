"""
响应格式（参考Java R类）

统一响应格式：
- code: 状态码 (200=成功, 其他=错误)
- msg: 消息
- data: 数据（泛型）
"""

from pydantic import BaseModel
from typing import Generic, TypeVar, Optional, Any

T = TypeVar('T')


class Response(BaseModel, Generic[T]):
    """统一响应格式（参考Java R类）"""
    code: int
    msg: str
    data: Optional[T] = None

    @classmethod
    def ok(cls, data: Optional[T] = None, msg: str = "success") -> "Response[T]":
        return cls(code=200, msg=msg, data=data)

    @classmethod
    def error(cls, code: int = 500, msg: str = "error") -> "Response[T]":
        return cls(code=code, msg=msg, data=None)