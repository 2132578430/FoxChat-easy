import socket

import redis
from redis.retry import Retry
from redis.backoff import ExponentialBackoff

from app.core.settings import global_settings

_pool = redis.ConnectionPool(
    host=global_settings.redis.host,
    port=global_settings.redis.port,
    db=global_settings.redis.db,
    password=global_settings.redis.password,
    decode_responses=True,
    # ——— 连接 & 读写超时（避免 frp 隧道静默断开后无限阻塞）———
    socket_connect_timeout=5,
    socket_timeout=10,
    # ——— TCP keepalive（frp / NAT 隧道必备，防止连接被中间设备静默丢弃）———
    socket_keepalive=True,
    socket_keepalive_options={
        socket.TCP_KEEPIDLE: 30,   # 30s 空闲后开始探测
        socket.TCP_KEEPINTVL: 10,  # 探测包间隔 10s
        socket.TCP_KEEPCNT: 3,     # 3 次探测失败 → 判定连接断开
    },
    # ——— redis-py 内置健康检查（每 30s 自动 PING，踢掉死连接）———
    health_check_interval=30,
    # ——— 超时后指数退避重试（1s → 2s → 4s，最多 3 次）———
    retry_on_timeout=True,
    retry=Retry(ExponentialBackoff(cap=10, base=1), 3),
    max_connections=20,
)

redis_client = redis.Redis(connection_pool=_pool)
