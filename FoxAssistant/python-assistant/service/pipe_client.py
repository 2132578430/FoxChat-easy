"""
FoxAssistant Python - Named Pipe 客户端
与 C# 服务进行进程间通信
"""

import json
import time
import ctypes
import threading
from typing import Optional, Callable
from loguru import logger

# Windows API 常量
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
PIPE_ACCESS_DUPLEX = GENERIC_READ | GENERIC_WRITE
PIPE_TYPE_MESSAGE = 0x00000004
PIPE_READMODE_MESSAGE = 0x00000002
PIPE_WAIT = 0x00000000
NMPWAIT_USE_DEFAULT_WAIT = 0x00000000
ERROR_PIPE_BUSY = 231
ERROR_PIPE_NOT_CONNECTED = 233


# ============================================================
# Pipe 客户端
# ============================================================

class PipeClient:
    """Named Pipe 客户端"""

    def __init__(self, pipe_name: str = "FoxAssistant"):
        self.pipe_name = pipe_name
        self.full_pipe_name = f"\\\\.\\pipe\\{pipe_name}"
        self.pipe_handle: Optional[int] = None
        self.connected = False
        self._lock = threading.Lock()

        # 连续失败计数（超过阈值触发退出）
        self._consecutive_failures = 0
        self._max_failures = 3
        self._should_exit = False

        # 回调：收到消息时
        self.on_message: Optional[Callable[dict, None]] = None

    def should_exit(self) -> bool:
        """检查是否应该退出服务"""
        return self._should_exit

    # --------------------------------------------------------
    # 连接 Pipe
    # --------------------------------------------------------

    def connect(self, timeout: float = 5.0, retries: int = 3) -> bool:
        """
        连接到 C# Named Pipe 服务端

        Args:
            timeout: 单次连接超时（秒）
            retries: 重试次数

        Returns:
            bool: 是否连接成功
        """
        for attempt in range(retries):
            try:
                logger.info(f"【Pipe】尝试连接 {self.full_pipe_name} (第{attempt + 1}次)")

                # 使用 Win32 API 连接
                kernel32 = ctypes.windll.kernel32

                # 设置函数签名
                kernel32.CreateFileW.argtypes = [
                    ctypes.c_wchar_p,  # lpFileName
                    ctypes.c_ulong,    # dwDesiredAccess
                    ctypes.c_ulong,    # dwShareMode
                    ctypes.c_void_p,   # lpSecurityAttributes
                    ctypes.c_ulong,    # dwCreationDisposition
                    ctypes.c_ulong,    # dwFlagsAndAttributes
                    ctypes.c_void_p    # hTemplateFile
                ]
                kernel32.CreateFileW.restype = ctypes.c_void_p

                kernel32.SetNamedPipeHandleState.argtypes = [
                    ctypes.c_void_p,   # hNamedPipe
                    ctypes.POINTER(ctypes.c_ulong),  # lpMode
                    ctypes.POINTER(ctypes.c_ulong),  # lpMaxCollectionCount
                    ctypes.POINTER(ctypes.c_ulong)   # lpCollectDataTimeout
                ]
                kernel32.SetNamedPipeHandleState.restype = ctypes.c_int

                kernel32.WriteFile.argtypes = [
                    ctypes.c_void_p,   # hFile
                    ctypes.c_void_p,   # lpBuffer
                    ctypes.c_ulong,    # nNumberOfBytesToWrite
                    ctypes.POINTER(ctypes.c_ulong),  # lpNumberOfBytesWritten
                    ctypes.c_void_p    # lpOverlapped
                ]
                kernel32.WriteFile.restype = ctypes.c_int

                kernel32.ReadFile.argtypes = [
                    ctypes.c_void_p,   # hFile
                    ctypes.c_void_p,   # lpBuffer
                    ctypes.c_ulong,    # nNumberOfBytesToRead
                    ctypes.POINTER(ctypes.c_ulong),  # lpNumberOfBytesRead
                    ctypes.c_void_p    # lpOverlapped
                ]
                kernel32.ReadFile.restype = ctypes.c_int

                kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
                kernel32.CloseHandle.restype = ctypes.c_int

                kernel32.GetLastError.argtypes = []
                kernel32.GetLastError.restype = ctypes.c_ulong

                # 连接 Pipe
                self.pipe_handle = kernel32.CreateFileW(
                    self.full_pipe_name,
                    PIPE_ACCESS_DUPLEX,
                    0,  # No sharing
                    None,  # No security
                    3,  # OPEN_EXISTING
                    0,  # No attributes
                    None
                )

                # INVALID_HANDLE_VALUE = -1 as void_p
                INVALID_HANDLE = ctypes.c_void_p(-1).value
                if self.pipe_handle == INVALID_HANDLE or self.pipe_handle is None:
                    error = kernel32.GetLastError()
                    if error == ERROR_PIPE_BUSY:
                        logger.warning(f"【Pipe】Pipe 端口繁忙，等待...")
                        time.sleep(0.5)
                        continue
                    logger.error(f"【Pipe】连接失败，错误码: {error}")
                    time.sleep(1)
                    continue

                # 设置消息读取模式
                mode = ctypes.c_ulong(PIPE_READMODE_MESSAGE)
                max_count = ctypes.c_ulong(0)
                timeout = ctypes.c_ulong(0)

                result = kernel32.SetNamedPipeHandleState(
                    self.pipe_handle,
                    ctypes.byref(mode),
                    None,  # 不设置 max collection count
                    None   # 不设置 timeout
                )

                if not result:
                    error = kernel32.GetLastError()
                    logger.error(f"【Pipe】设置消息模式失败，错误码: {error}")
                    kernel32.CloseHandle(self.pipe_handle)
                    self.pipe_handle = None
                    time.sleep(1)
                    continue

                self.connected = True
                logger.info("【Pipe】连接成功")
                return True

            except Exception as e:
                logger.error(f"【Pipe】连接异常: {e}")
                time.sleep(1)

        logger.error("【Pipe】连接失败，已达到最大重试次数")
        return False

    # --------------------------------------------------------
    # 发送消息
    # --------------------------------------------------------

    def send_message(self, message: dict) -> bool:
        """
        发送 JSON 消息到 C# 服务（失败时自动重连）

        Args:
            message: 消息字典，包含 type 和可选的 state

        Returns:
            bool: 是否发送成功
        """
        # 未连接时尝试重连
        if not self.connected or self.pipe_handle is None:
            logger.warning("【Pipe】未连接，尝试重连...")
            if not self.connect(timeout=2.0, retries=1):
                self._consecutive_failures += 1
                if self._consecutive_failures >= self._max_failures:
                    logger.error(f"【Pipe】连续失败 {self._consecutive_failures} 次，标记退出")
                    self._should_exit = True
                return False

        with self._lock:
            try:
                kernel32 = ctypes.windll.kernel32

                # 确保 message 有 timestamp
                message["timestamp"] = int(time.time() * 1000)

                json_str = json.dumps(message, ensure_ascii=False)
                data = json_str.encode("utf-8")

                # 写入消息
                bytes_written = ctypes.c_ulong(0)
                buffer = ctypes.c_char_p(data)

                result = kernel32.WriteFile(
                    self.pipe_handle,
                    buffer,
                    len(data),
                    ctypes.byref(bytes_written),
                    None
                )

                if not result:
                    error = kernel32.GetLastError()
                    logger.error(f"【Pipe】写入失败，错误码: {error}")
                    # 断开连接，下次发送时会重连
                    self.connected = False
                    self._consecutive_failures += 1
                    if self._consecutive_failures >= self._max_failures:
                        logger.error(f"【Pipe】连续失败 {self._consecutive_failures} 次，标记退出")
                        self._should_exit = True
                    return False

                # 发送成功，重置失败计数
                self._consecutive_failures = 0
                logger.debug(f"【Pipe】发送成功: {message.get('type')} ({bytes_written.value} bytes)")
                return True

            except Exception as e:
                logger.error(f"【Pipe】发送异常: {e}")
                self.connected = False
                self._consecutive_failures += 1
                if self._consecutive_failures >= self._max_failures:
                    logger.error(f"【Pipe】连续失败 {self._consecutive_failures} 次，标记退出")
                    self._should_exit = True
                return False

    # --------------------------------------------------------
    # 状态上报
    # --------------------------------------------------------

    def send_state(self, state: str) -> bool:
        """
        发送状态变化消息

        Args:
            state: 状态名称 (thinking, yes, no, idle)

        Returns:
            bool: 是否发送成功
        """
        return self.send_message({
            "type": "STATE_CHANGE",
            "state": state
        })

    def send_idle_timeout(self) -> bool:
        """
        发送静息超时消息
        """
        return self.send_message({
            "type": "IDLE_TIMEOUT"
        })

    def send_ping(self) -> bool:
        """
        发送心跳消息
        """
        return self.send_message({
            "type": "PING"
        })

    # --------------------------------------------------------
    # 接收消息（阻塞）
    # --------------------------------------------------------

    def receive_message(self, timeout_ms: int = 5000) -> Optional[dict]:
        """
        接收一条消息（阻塞）

        Args:
            timeout_ms: 超时时间（毫秒）

        Returns:
            dict: 解析后的消息，超时返回 None
        """
        if not self.connected or self.pipe_handle is None:
            return None

        try:
            kernel32 = ctypes.windll.kernel32

            buffer = ctypes.create_string_buffer(1024)
            bytes_read = ctypes.c_ulong(0)

            result = kernel32.ReadFile(
                self.pipe_handle,
                buffer,
                1024,
                ctypes.byref(bytes_read),
                None
            )

            if not result:
                error = kernel32.GetLastError()
                if error == ERROR_PIPE_NOT_CONNECTED:
                    logger.warning("【Pipe】连接已断开")
                    self.connected = False
                return None

            data = buffer.raw[:bytes_read.value].decode("utf-8").strip()
            return json.loads(data)

        except json.JSONDecodeError:
            logger.warning("【Pipe】消息解析失败")
            return None
        except Exception as e:
            logger.error(f"【Pipe】接收异常: {e}")
            return None

    # --------------------------------------------------------
    # 等待关闭确认
    # --------------------------------------------------------

    def wait_shutdown_ack(self, timeout: float = 2.0) -> bool:
        """
        等待 C# 发送的关闭确认（简化版：只等待超时，不阻塞读取）

        Args:
            timeout: 超时时间（秒）

        Returns:
            bool: 是否收到确认（目前总是返回 True，因为 C# 收到后会关闭）
        """
        # 简化处理：等待一小段时间让 C# 处理，然后直接返回
        # C# 收到 IDLE_TIMEOUT 后会发送 SHUTDOWN_ACK 并隐藏 Orb
        # Python 不需要阻塞等待确认，直接退出即可
        time.sleep(0.5)
        logger.info("【Pipe】等待关闭确认完成")
        return True

    # --------------------------------------------------------
    # 断开连接
    # --------------------------------------------------------

    def disconnect(self):
        """关闭 Pipe 连接"""
        if self.pipe_handle:
            kernel32 = ctypes.windll.kernel32
            kernel32.CloseHandle(self.pipe_handle)
            self.pipe_handle = None
            self.connected = False
            logger.info("【Pipe】连接已关闭")

    # --------------------------------------------------------
    # 资源释放
    # --------------------------------------------------------

    def __del__(self):
        self.disconnect()


# ============================================================
# 全局 Pipe 客户端实例
# ============================================================

_pipe_client: Optional[PipeClient] = None


def init_pipe_client(pipe_name: str = "FoxAssistant") -> Optional[PipeClient]:
    """
    初始化全局 Pipe 客户端

    Args:
        pipe_name: Pipe 名称

    Returns:
        PipeClient: 客端实例，失败返回 None
    """
    global _pipe_client

    try:
        _pipe_client = PipeClient(pipe_name)

        if _pipe_client.connect(timeout=5.0, retries=3):
            logger.info("【Pipe】Pipe 客户端初始化成功")
            return _pipe_client
        else:
            logger.warning("【Pipe】Pipe 客户端连接失败，继续运行（无状态同步）")
            _pipe_client = None
            return None

    except Exception as e:
        logger.error(f"【Pipe】初始化异常: {e}")
        _pipe_client = None
        return None


def get_pipe_client() -> Optional[PipeClient]:
    """获取全局 Pipe 客户端"""
    return _pipe_client


def send_orb_state(state: str):
    """
    发送 Orb 状态（简化接口）

    Args:
        state: 状态名称 (thinking, yes, no, idle)
    """
    client = get_pipe_client()
    if client:
        client.send_state(state)


def notify_idle_timeout():
    """
    发送静息超时并等待确认
    """
    client = get_pipe_client()
    if client:
        client.send_idle_timeout()
        client.wait_shutdown_ack(timeout=2.0)