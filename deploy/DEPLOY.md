# FoxChat 中间件迁出部署手册

> 目标：将 MySQL/Redis/MinIO/RabbitMQ/ChromaDB 从 2C2G 服务器迁至本机 WSL Docker，通过 frp 隧道保持连通。服务器仅保留 3 个业务容器 + Gitea Runner。

---

## 架构变化

```
服务器 (2C2G)                          本机 WSL
┌─────────────────────┐              ┌──────────────────────────┐
│ frps :7000 (隧道)    │◄────frp─────│ frpc (隧道客户端)          │
│                     │              │ mysql            :3306   │
│ java-app   :12000   │──frp────────│ redis            :6379   │
│ python-app :8000    │──frp────────│ minio            :9000   │
│ vue-nginx  :80/443  │──frp────────│ rabbitmq         :5672   │
│ gitea runner        │              │ chromadb         :8000   │
│                     │              │                          │
│ 内存 ~1.0G / 2G     │              │ 内存 ~0.9G（本机资源）      │
└─────────────────────┘              └──────────────────────────┘
```

## 端口映射

| 服务 | 本机 | → | 服务器(frp转发) |
|---|---|---|---|
| MySQL | 3306 | → | 13306 |
| Redis | 6379 | → | 16379 |
| MinIO API | 9000 | → | 19000 |
| MinIO Console | 9001 | → | 19001 |
| RabbitMQ AMQP | 5672 | → | 15672 |
| RabbitMQ Mgmt | 15672 | → | 25672 |
| ChromaDB | 8000 | → | 18000 |

---

## 前置准备

- [ ] 本机 WSL 已安装 Docker Desktop 并正常运行
- [ ] 能 SSH 到服务器（`ssh root@<SERVER_IP>`）
- [ ] 知道服务器 IP（假设 `123.57.175.65`，下面用 `<SERVER_IP>` 代替）
- [ ] 服务器 `.env` 文件路径：`/root/home/docker-manager/.env`

---

## Step 1: 修改配置文件中的 token 和 IP

### 1a. 生成 token

```bash
openssl rand -hex 16
# 记录输出，例如：a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
```

### 1b. 编辑 `deploy/frp/frps.toml`

```toml
auth.token = "刚才生成的token"
```

### 1c. 编辑 `deploy/local-middleware/frpc-docker.toml`

```toml
serverAddr = "<SERVER_IP>"       # 服务器公网 IP
auth.token = "刚才生成的token"    # 与 frps.toml 一致
```

### 1d. 编辑 `docker-compose.prod.yml`

```yaml
# 第 42 行左右，把默认 IP 改成你的服务器 IP：
- MINIO_PUBLIC_ENDPOINT=http://<SERVER_IP>:19000
```

### ✅ 验证

```bash
grep 'auth.token' deploy/frp/frps.toml deploy/local-middleware/frpc-docker.toml
# 两行输出必须完全一致
```

---

## Step 2: 本机启动中间件

```bash
cd deploy/local-middleware

# 2a. 复制环境变量（已含服务器同款密码，无需修改）
cp .env.example .env

# 2b. 创建数据目录
mkdir -p mysql-docker/data mysql-docker/log
mkdir -p redis-docker/data
mkdir -p minio/data
mkdir -p rabbitmq-docker/data rabbitmq-docker/log
mkdir -p chroma-docker/data

# 2c. 启动所有中间件
docker compose up -d

# 2d. 等 MySQL 初始化完成（约 30-60 秒）
docker logs fox-mysql -f
# 看到 ready for connections 后 Ctrl+C
```

### ✅ 验证

```bash
docker exec fox-mysql mysql -uroot -proot123 -e "SELECT 1"     # → 1
docker exec fox-redis redis-cli -a root ping                    # → PONG
curl -s http://localhost:9000/health/live                        # → 200 相关响应
curl -s -u admin:admin http://localhost:15672/api/overview       # → JSON
curl -s http://localhost:18000/api/v1/heartbeat                  # → heartbeat
```

---

## Step 3: 服务器部署 frps

### 3a. 本机下载 frp 安装包

```bash
# 在 WSL 中执行，下载到 deploy/frp/ 目录
cd deploy/frp
wget https://github.com/fatedier/frp/releases/download/v0.61.2/frp_0.61.2_linux_amd64.tar.gz
```

> 如果本机 WSL 也访问不了 GitHub，用 Windows 浏览器下载后放到 `deploy\frp\` 目录即可。

### 3b. 上传到服务器并安装

```bash
# 上传整个 frp 目录（含安装包 + 脚本 + 配置）
scp -r deploy/frp root@<SERVER_IP>:/tmp/

# SSH 到服务器
ssh root@<SERVER_IP>
cd /tmp/frp
bash install-frps.sh
# 脚本会自动检测同目录下的 tar.gz，跳过下载
```

### ✅ 验证

```bash
systemctl status frps        # → active (running)
ss -tlnp | grep 7000         # → 0.0.0.0:7000 在监听
```

**⚠️ 检查防火墙：** 确保服务器安全组/iptables 放行以下端口：
`7000, 13306, 16379, 15672, 18000, 19000, 19001, 25672`

---

## Step 4: 本机启动 frpc 隧道

```bash
cd deploy/local-middleware
docker compose up -d frpc
docker logs fox-frpc
```

### ✅ 验证

```bash
# 本机：确认 7 条代理全部成功
docker logs fox-frpc 2>&1 | grep -c "start proxy success"
# → 7

# 服务器：确认转发端口全部在监听
ssh root@<SERVER_IP> "ss -tlnp | grep -E '13306|16379|15672|18000|19000|19001'"
# → 应显示 7 行

# 服务器：实际测试隧道连通（以 MySQL 为例）
ssh root@<SERVER_IP> "echo > /dev/tcp/127.0.0.1/13306 && echo 'OK' || echo 'FAIL'"
# → OK
```

---

## Step 5: 数据迁移

**⚠️ 确认 Step 2-4 全部验证通过后再做这一步。**

### 5a. MySQL（必须迁移）

```bash
# 服务器导出
ssh root@<SERVER_IP> "docker exec fox-mysql mysqldump -uroot -proot123 \
  --single-transaction --routines --triggers --databases FoxChat | gzip" > foxchat_dump.sql.gz

# 本机导入
gunzip -c foxchat_dump.sql.gz | docker exec -i fox-mysql mysql -uroot -proot123
```

### 5b. MinIO（如果有文件则迁移）

```bash
# 服务器打包
ssh root@<SERVER_IP> "docker exec fox-minio tar czf /tmp/minio-data.tar.gz -C /data ."
scp root@<SERVER_IP>:/tmp/minio-data.tar.gz .

# 本机导入
docker compose -f deploy/local-middleware/docker-compose.yml stop minio
tar xzf minio-data.tar.gz -C deploy/local-middleware/minio/data/
docker compose -f deploy/local-middleware/docker-compose.yml start minio
```

### 5c. ChromaDB（如果有向量数据则迁移）

```bash
# 服务器打包
ssh root@<SERVER_IP> "docker exec fox-chromadb tar czf /tmp/chroma-data.tar.gz -C /chroma/chroma ."
scp root@<SERVER_IP>:/tmp/chroma-data.tar.gz .

# 本机导入
docker compose -f deploy/local-middleware/docker-compose.yml stop chromadb
tar xzf chroma-data.tar.gz -C deploy/local-middleware/chroma-docker/data/
docker compose -f deploy/local-middleware/docker-compose.yml start chromadb
```

### 5d. Redis + RabbitMQ

无需迁移。Redis 是缓存，RabbitMQ 是临时消息，应用启动时会自动重建。

### ✅ 验证

```bash
# MySQL 表数量应与服务器一致
docker exec fox-mysql mysql -uroot -proot123 -e \
  "SELECT COUNT(*) AS cnt FROM information_schema.tables WHERE table_schema='FoxChat';"

# MinIO bucket 存在
curl -s http://localhost:9000/bedfox-chat -u minioadmin:minioadmin | head -20
```

---

## Step 6: 部署业务代码到服务器

### 方式 A：push 触发 Gitea Runner 自动部署（推荐）

```bash
git add -A
git commit -m "中间件迁出: frp 隧道方案"
git push origin master
```

Runner 自动执行：拉代码 → 构建镜像 → `docker compose up -d --remove-orphans` → 健康检查。

### 方式 B：手动部署

```bash
ssh root@<SERVER_IP>
cd <FoxChat workspace>
git pull origin master
docker compose -f docker-compose.prod.yml --env-file /root/home/docker-manager/.env up -d --remove-orphans
```

### ✅ 验证

```bash
# 服务器上执行
docker compose -f docker-compose.prod.yml ps
# → 只有 fox-java, fox-python, fox-vue 三个容器！
# → 不应出现 fox-mysql, fox-redis, fox-minio, fox-rabbitmq, fox-chromadb

# 服务接口
curl -sf http://localhost:12000 && echo "Java ✅"
curl -sf http://localhost:8000/docs && echo "Python ✅"
curl -sf http://localhost:80 && echo "Vue ✅"

# 关键：内存！
free -h
# Mem used 应在 1.2G-1.4G（之前 ~1.7G，89% → 约 65%）
```

---

## Step 7: 端到端功能测试

浏览器打开 `http://<SERVER_IP>`，逐一验证：

| 操作 | 预期 | 数据路径 |
|---|---|---|
| 打开页面 | 正常显示 | vue-nginx 本地 |
| 登录 | 成功 | frp → MySQL（读用户表） |
| 发送消息 | AI 正常回复 | frp → Redis（读上下文）→ MySQL（写消息） |
| 上传文件 | 上传成功，可下载 | frp → MinIO（存储/读取） |
| 查看历史 | 能加载 | frp → MySQL（查消息）+ Redis（缓存） |
| RAG 搜索 | 返回结果 | frp → ChromaDB（向量检索） |

**异常恢复测试：**

```bash
# 本机模拟网络断开重连
docker restart fox-frpc
sleep 5
docker logs fox-frpc --tail 5     # 应看到重连成功
# 再去测前端功能——应自动恢复
```

---

## Step 8: 清理服务器旧中间件

**⚠️ 确认 Step 7 全部正常，稳定运行至少 24 小时后执行。**

```bash
ssh root@<SERVER_IP>

# 停止并删除旧中间件容器
docker stop fox-mysql fox-redis fox-minio fox-rabbitmq fox-chromadb 2>/dev/null
docker rm fox-mysql fox-redis fox-minio fox-rabbitmq fox-chromadb 2>/dev/null

# 删除旧中间件镜像（可选，释放磁盘）
docker rmi mysql:8.0 redis/redis-stack:latest minio/minio:latest \
  rabbitmq:3.12-management chromadb/chroma:latest 2>/dev/null

# 删除旧数据目录（⚠️ 确认数据迁移成功后再删！）
rm -rf /root/home/docker-manager/mysql-docker
rm -rf /root/home/docker-manager/redis-docker
rm -rf /root/home/docker-manager/minio
rm -rf /root/home/docker-manager/rabbitmq-docker
rm -rf /root/home/docker-manager/chroma-docker

# 清理悬空镜像和卷
docker image prune -f
docker volume prune -f

# 确认磁盘释放
df -h /
```

### ✅ 最终确认

```bash
docker ps                    # 仅 fox-java, fox-python, fox-vue
free -h                      # < 70%
df -h /                      # 磁盘增加
```

---

## 回滚方案

如果部署后出现问题：

```bash
ssh root@<SERVER_IP>
cd <FoxChat workspace>

# 恢复旧版 compose
git checkout docker-compose.prod.yml
git checkout FoxChat-vue/nginx.conf

# 重新部署（中间件容器会重新创建）
docker compose -f docker-compose.prod.yml --env-file /root/home/docker-manager/.env up -d

# 验证 8 个容器全部 running
docker compose -f docker-compose.prod.yml ps
```

---

## 常见问题

### Q: frpc 日志 `connect to server error: i/o timeout`

服务器防火墙未放行 TCP 7000 端口。请在安全组/iptables 中放行。

### Q: java-app 启动日志 `Communications link failure`

frp 隧道未建立。检查：
1. 本机中间件是否全部 running：`docker compose -f deploy/local-middleware/docker-compose.yml ps`
2. frpc 是否连接成功：`docker logs fox-frpc | grep "start proxy success"`
3. 服务器转发端口是否在监听：`ssh root@<SERVER_IP> "ss -tlnp | grep 13306"`

### Q: 前端上传文件失败

MinIO 公网端点或 nginx 代理配置问题。确认：
- `docker-compose.prod.yml`：`MINIO_PUBLIC_ENDPOINT=http://<SERVER_IP>:19000`
- `FoxChat-vue/nginx.conf`：`set $minio "host.docker.internal:19000"`
- `docker-compose.prod.yml`：`vue-nginx` 有 `extra_hosts: host.docker.internal:host-gateway`

### Q: 内存没降

服务器上旧中间件容器可能还在运行：
```bash
ssh root@<SERVER_IP> "docker ps --format '{{.Names}}' | grep fox-"
# 如果看到 fox-mysql 等，手动 docker stop + docker rm
```
