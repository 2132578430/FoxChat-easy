import logging

from fastapi import Request, FastAPI
from app.exception.BusinessException import BusinessException
from app.schemas.M import M


def register_exception_handlers(app: FastAPI):
    """
    统一注册所有的全局异常处理器
    """
    
    @app.exception_handler(BusinessException)
    async def business_exception_handler(request: Request, exc: BusinessException):
        logging.error(f"业务异常: code={exc.code}, msg={exc.msg}")
        return M.get_msg(
            data=exc.msg,
            msg_id=str(exc.code)
        )
    @app.exception_handler(Exception)
    async def message_handler(request: Request, exc: Exception):
        error_type = type(exc).__name__
        error_msg = str(exc) if str(exc) else "(no message)"
        logging.error(f"未知异常 [{error_type}]: {error_msg}", exc_info=True)
        # 返回真实错误类型和消息给调用方（Java），方便定位根因
        detail = f"[{error_type}] {error_msg}" if error_msg else f"[{error_type}]"
        return M.get_msg(data=detail, msg_id="500")
