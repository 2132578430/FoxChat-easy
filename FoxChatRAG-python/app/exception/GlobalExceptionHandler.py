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
        return M.get_msg(
            data=exc.msg,
            msg_id=str(exc.code)
        )
    @app.exception_handler(Exception)
    async def message_handler(request: Request, exc: Exception):
        logging.error("未知异常，捕获到信息：" + str(exc))
