# FoxAssistant

轻量级语音唤醒助手，按需启动，自动休眠。

## 架构

```
┌─────────────────┐
│   Python 命令层 │
│                 │
│  /command API   │
│  命令执行       │
│  30s → 退出     │
└─────────────────┘
```

注：C# 唤醒服务已移除，认证改为 HTTPOnly Cookie。

## 快速启动

### 启动 Python 服务（测试）

```bash
cd FoxAssistant/python-assistant
pip install -r requirements.txt
python main.py
```

测试命令：
```bash
curl -X POST http://127.0.0.1:9000/command -H "Content-Type: application/json" -d '{"text": "放一首歌"}'
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| PORT | 9000 | Python服务端口 |
| IDLE_TIMEOUT | 30 | 无请求自动退出时间（秒） |

## 命令列表

| 命令 | 口令示例 | 说明 |
|------|----------|------|
| play_music | 放歌、播放音乐、听歌 | 启动QQ音乐 |
| pause_music | 暂停、停止播放 | 暂停音乐 |
| query_time | 现在几点、时间 | 查询系统时间 |
| query_weather | 天气、今天天气 | wttr.in天气查询 |

## 响应格式（R格式）

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "command": "play_music",
    "result": "已启动QQ音乐",
    "success": true
  }
}