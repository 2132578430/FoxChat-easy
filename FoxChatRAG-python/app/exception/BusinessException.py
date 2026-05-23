from app.common.constant import MsgStatusConstant


class BusinessException(Exception):
    def __init__(self, msg: MsgStatusConstant):
        self.code = msg.code
        self.msg = msg.msg
