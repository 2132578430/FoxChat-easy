# 中间件数据迁移指南

将服务器上的中间件数据迁移到本机 WSL Docker。

## 前置条件

- [ ] 本机 WSL 已安装 Docker
- [ ] 能 SSH 到服务器
- [ ] 服务器 `.env` 文件已知（在 `/root/home/docker-manager/.env`）

---

## 1. 本机启动中间件（空库）

```bash
# 在 deploy/local-middleware/ 目录下
cp .env.example .env
# 编辑 .env，填入与服务器一致的密码

# 创建数据目录（首次需要）
mkdir -p mysql-docker/data mysql-docker/log
mkdir -p redis-docker/data
mkdir -p minio/data
mkdir -p rabbitmq-docker/data rabbitmq-docker/log
mkdir -p chroma-docker/data

# 启动
docker compose up -d

# 等待 MySQL 初始化完成（约 30 秒）
docker logs fox-mysql -f
# 看到 "ready for connections" 即可 Ctrl+C
```

---

## 2. MySQL 数据迁移

```bash
# === 在服务器上执行 ===
# 导出数据库
docker exec fox-mysql mysqldump \
  -uroot -p${MYSQL_ROOT_PASSWORD} \
  --single-transaction \
  --routines \
  --triggers \
  --databases FoxChat \
  > /tmp/foxchat_dump.sql

# 压缩（通常能压缩到 1/5）
gzip /tmp/foxchat_dump.sql

# === 传回本机 ===
# 在本机 WSL 执行
scp root@<服务器IP>:/tmp/foxchat_dump.sql.gz .

# === 在本机导入 ===
gunzip foxchat_dump.sql.gz
docker exec -i fox-mysql mysql -uroot -p${MYSQL_ROOT_PASSWORD} < foxchat_dump.sql

# 验证
docker exec fox-mysql mysql -uroot -p${MYSQL_ROOT_PASSWORD} -e "SHOW TABLES;" FoxChat
```

---

## 3. MinIO 文件迁移

```bash
# === 方案 A: mc mirror（推荐）===
# 在本机安装 minio client
wget https://dl.min.io/client/mc/release/linux-amd64/mc
chmod +x mc
sudo mv mc /usr/local/bin/

# 添加两边 MinIO
mc alias set server-minio http://<服务器IP>:9000 minioadmin minioadmin
mc alias set local-minio http://localhost:9000 minioadmin minioadmin

# 同步所有 bucket
mc mirror server-minio/bedfox-chat local-minio/bedfox-chat

# === 方案 B: 如果文件不多，直接 rsync 数据目录 ===
# 在服务器上
docker exec fox-minio tar czf /tmp/minio-data.tar.gz -C /data .
# 传回本机
scp root@<服务器IP>:/tmp/minio-data.tar.gz .
# 解压到本机 MinIO 数据目录
tar xzf minio-data.tar.gz -C ./minio/data/
```

---

## 4. ChromaDB 数据迁移

向量数据直接复制即可（ChromaDB 使用 SQLite + 文件存储）：

```bash
# 在服务器上打包
docker exec fox-chromadb tar czf /tmp/chroma-data.tar.gz -C /chroma/chroma .

# 传回本机
scp root@<服务器IP>:/tmp/chroma-data.tar.gz .

# 解压到本机（先停掉 chromadb 容器）
docker compose stop chromadb
tar xzf chroma-data.tar.gz -C ./chroma-docker/data/
docker compose start chromadb
```

---

## 5. Redis & RabbitMQ

**Redis**：缓存数据，可以跳过。如果需要迁移：

```bash
# 服务器上触发 BGSAVE
docker exec fox-redis redis-cli -a ${REDIS_PASSWORD} BGSAVE
# 等几秒后复制 dump.rdb
docker cp fox-redis:/data/dump.rdb ./redis-docker/data/dump.rdb
# 传回本机放到 redis-docker/data/ 下
```

**RabbitMQ**：队列消息是临时的，无需迁移。但需要确认队列定义一致。可以手动在管理界面 (localhost:15672) 重建，或者依赖应用启动时自动声明队列（Spring AMQP / aio_pika 都会自动声明）。

---

## 6. 验证

```bash
# MySQL
docker exec fox-mysql mysql -uroot -p${MYSQL_ROOT_PASSWORD} -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='FoxChat';"

# Redis
docker exec fox-redis redis-cli -a ${REDIS_PASSWORD} ping

# MinIO
curl http://localhost:9000/health/live

# RabbitMQ
curl -u admin:admin http://localhost:15672/api/overview

# ChromaDB
curl http://localhost:18000/api/v1/heartbeat
```
