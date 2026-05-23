"""
角色记忆压力测试脚本

用法：python memory_stress_test.py

前提：FoxChatRAG 服务已在 localhost:8000 运行
"""

import asyncio
import json
import time
from dataclasses import dataclass, field

import httpx

# ============================================================
# 配置 - 按需修改
# ============================================================
BASE_URL = "http://localhost:8000"
USER_ID = "2021923959349370882"
LLM_ID = "2055976371882237954"

# 轮数控制
SEEDING_ROUNDS = 12      # 播种期轮数
POLLUTION_ROUNDS = 200   # 污染期轮数
ROUND_DELAY = 2.0        # 轮间等待秒数（等后台总结等异步任务）
REQUEST_TIMEOUT = 120    # 单次请求超时秒数

# ============================================================
# 播种期：记忆点定义
# ============================================================
# 格式: (轮次对话内容, [(验证问题, 期望关键词), ...])
# 每条对话自然混入1-2个记忆点

SEEDING_CONVERSATIONS: list[tuple[str, list[tuple[str, list[str]]]]] = [
    # 第1轮 - 名字 + 年龄
    (
        "你好！我叫林小满，今年28岁，以后请多关照啦~",
        [
            ("你还记得我叫什么名字吗？", ["林小满"]),
            ("我今年多大了？", ["28"]),
        ],
    ),
    # 第2轮 - 职业 + 爱好
    (
        "我是一名UI设计师，平时工作还挺忙的，不过周末我喜欢在家画水彩画，感觉很解压",
        [
            ("我的职业是什么？", ["UI", "设计"]),
            ("我周末喜欢做什么？", ["水彩", "画"]),
        ],
    ),
    # 第3轮 - 宠物
    (
        "对了，我养了一只柯基，叫豆包，超级可爱的！每天回家它都会摇着屁股跑过来迎接我",
        [
            ("我养了什么宠物？", ["柯基", "豆包"]),
        ],
    ),
    # 第4轮 - 妹妹
    (
        "我有个妹妹，我们都叫她小林，她还在上大学呢，学的是计算机专业",
        [
            ("我妹妹叫什么？", ["小林"]),
            ("我妹妹在读什么？", ["大学", "计算机"]),
        ],
    ),
    # 第5轮 - 喜欢的食物（川菜/水煮鱼）
    (
        "说到吃的，我超级喜欢川菜，尤其是水煮鱼！每次去川菜馆必点，那个麻辣鲜香的味道简直绝了",
        [
            ("我喜欢吃什么菜？", ["川菜", "水煮鱼"]),
        ],
    ),
    # 第6轮 - 讨厌的食物（香菜）
    (
        "不过有一件事我完全受不了——香菜！那股味道我真的不行，每次看到菜上面撒了香菜我都会一根一根挑出来",
        [
            ("我讨厌吃什么？", ["香菜"]),
        ],
    ),
    # 第7轮 - 喜欢蓝色
    (
        "哦对了，你知道我最喜欢什么颜色吗？是蓝色！我的手机壳、电脑壁纸、甚至家里的窗帘都是蓝色的",
        [
            ("我最喜欢什么颜色？", ["蓝"]),
        ],
    ),
    # 第8轮 - 成都经历
    (
        "说起来，去年我在成都呆了三个月，是公司派我去那边做项目，那段时间真的太美好了，火锅串串吃了个够",
        [
            ("我之前在哪个城市呆过三个月？", ["成都"]),
        ],
    ),
    # 第9轮 - 日本旅游计划
    (
        "最近在计划一件开心的事！下个月我要去日本旅游，第一次去日本，攻略做了一大堆，主要想去京都和东京",
        [
            ("我下个月有什么计划？", ["日本", "旅游"]),
        ],
    ),
    # 第10轮 - 边界（前男友）
    (
        "那个……能跟你约定一件事吗？以后千万别跟我提前男友，我跟前任分手分得很不愉快，提到他就烦，拜托了",
        [
            ("有什么话题不能跟我提？", ["前男友"]),
        ],
    ),
    # 第11轮 - 日常强化（综合提及之前信息）
    (
        "今天工作累死了，画了一整天的界面，晚上带豆包出去散步的时候突然想吃水煮鱼了，回家点了个外卖当犒劳自己~",
        [],
    ),
    # 第12轮 - 日常强化2
    (
        "周末准备带小林一起去逛街，她说想买几件蓝色的衣服，果然审美是会遗传的哈哈。对了还要去旅行社确认一下日本的行程。",
        [],
    ),
]

# ============================================================
# 污染期：无关话题池
# ============================================================
POLLUTION_TOPICS = [
    "今天天气真不错，阳光明媚的",
    "你听说过量子计算吗？感觉好神奇",
    "最近有没有什么好看的电影推荐？",
    "我觉得Python真的是一门很优雅的语言",
    "你喜欢听什么类型的音乐？",
    "中午吃了碗牛肉面，味道还不错",
    "最近在学做菜，西红柿炒蛋算是入门级别吧",
    "听说今年夏天会特别热",
    "你觉得人工智能会取代人类的工作吗？",
    "昨天看到一只流浪猫，好可怜",
    "有没有什么好用的笔记软件推荐？",
    "春节你一般怎么过？",
    "我最近在减肥，但总是管不住嘴",
    "你觉得早起难还是早睡难？",
    "咖啡和茶你更喜欢哪个？",
    "今天路上堵车堵了好久",
    "听说最近有流星雨，想去看吗？",
    "我觉得运动真的能让人心情变好",
    "你喜欢看小说还是看漫画？",
    "最近迷上了种多肉植物",
    "你觉得线上办公好还是线下办公好？",
    "手机电池越来越不耐用了",
    "有没有什么好喝的奶茶推荐？",
    "我昨天做梦梦到自己会飞了",
    "你觉得人应该有存款还是及时行乐？",
    "最近在玩一个叫星露谷物语的游戏",
    "今天下班打算去健身房",
    "你会不会有时候也觉得时间过得特别快？",
    "酸菜鱼和水煮鱼你更喜欢哪个？",
    "最近朋友圈都在晒旅游照",
    "你觉得什么样的工作才算是好工作？",
    "我刚换了新手机，拍照效果很好",
    "周末一般几点起床？",
    "你喜欢爬山还是喜欢去海边？",
    "最近睡眠质量不太好",
    "有没有推荐的播客节目？",
    "今天心情莫名有点低落",
    "你觉得人生的意义是什么？",
    "我打算学一门外语，你有什么建议？",
    "最近外卖越来越贵了",
    "你喜欢城市生活还是乡村生活？",
    "你觉得读书有用吗？",
    "我今天煮了一锅汤，味道还可以",
    "你喜欢冬天还是夏天？",
    "最近总看到无人机送货的新闻",
    "你相不相信星座？",
    "我说今天地铁上人特别多",
    "有没有什么高效的记忆方法？",
    "最近打算换一个发型",
    "你觉得朋友之间应该AA制吗？",
    "今天看到了一个很搞笑的短视频",
    "你喜欢吃甜的还是咸的？",
    "我最近开始学习冥想",
    "你觉得电动车真的环保吗？",
    "昨天帮朋友搬家，累坏了",
    "有没有什么好用的桌面整理工具？",
    "我觉得摄影是件很有趣的事",
    "你喜欢看纪录片吗？",
    "最近发现了一个不错的餐厅",
    "你觉得应该怎么分配工作和生活？",
    "今年的目标已经完成一半了",
    "我最近在听一个叫黑猫侦探的播客",
    "你喜欢什么样的装修风格？",
    "今天在超市看到了很便宜的水果",
    "你觉得养宠物麻烦吗？",
    "我下周有个重要的面试",
    "最近迷上了烘焙，做了几次饼干",
    "你喜欢玩桌游吗？",
    "今天突然想起来小时候的一些事",
    "你觉得社交媒体的利弊是什么？",
    "我昨天去了趟图书馆，借了几本书",
    "你会不会有时候觉得孤单？",
    "最近在考虑要不要换个城市生活",
    "你喜欢逛商场还是逛网店？",
    "今天泡了杯茶，感觉整个人都静下来了",
    "你觉得善良是一种选择还是一种本能？",
    "我最近开始写日记了",
    "有没有什么好喝的咖啡豆推荐？",
    "你觉得编程难学吗？",
    "今天收到了朋友寄来的明信片",
    "你喜欢安静的环境还是热闹的环境？",
    "最近在研究怎么养护绿植",
    "你觉得旅行最大的意义是什么？",
    "我刚看完一本叫《认知觉醒》的书",
    "你喜欢什么样的电影结局？",
    "今天自己做了顿饭，感觉很有成就感",
    "你觉得人为什么要交朋友？",
    "我最近在学游泳，但是总是呛水",
    "你喜欢有规划的生活还是随性的生活？",
    "今天在公园里看到一群老年人在下棋",
    "如果给你一千万，你第一件事会做什么？",
]

# ============================================================
# 验收期：验证问题（从 SEEDING_CONVERSATIONS 自动提取）
# ============================================================
@dataclass
class VerificationItem:
    question: str
    expected_keywords: list[str]
    passed: bool | None = None
    actual_response: str = ""
    latency_ms: float = 0.0  # 请求延迟（毫秒）


def build_verification_items() -> list[VerificationItem]:
    """从播种期定义中提取所有验证项"""
    items: list[VerificationItem] = []
    seen: set[str] = set()
    for _, verifications in SEEDING_CONVERSATIONS:
        for question, keywords in verifications:
            if question not in seen:
                seen.add(question)
                items.append(VerificationItem(question=question, expected_keywords=keywords))
    return items


# ============================================================
# HTTP 客户端
# ============================================================
class ChatClient:
    def __init__(self, base_url: str, user_id: str, llm_id: str):
        self.base_url = base_url.rstrip("/")
        self.user_id = user_id
        self.llm_id = llm_id

    async def clear_memory(self) -> bool:
        """清除该用户+角色的所有记忆"""
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/delete",
                    params={"userId": self.user_id, "llmId": self.llm_id},
                )
                print(f"  [清除记忆] status={resp.status_code}")
                return resp.status_code == 200
        except Exception as e:
            print(f"  [清除记忆] 失败: {e}")
            return False

    async def send_message(self, content: str) -> str:
        """发送一条消息，返回 AI 回复内容"""
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/msg",
                    json={
                        "userId": self.user_id,
                        "msgContent": content,
                        "llmId": self.llm_id,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return _extract_reply(data)
                else:
                    return f"[HTTP {resp.status_code}] {resp.text[:100]}"
        except httpx.TimeoutException:
            return "[TIMEOUT]"
        except Exception as e:
            return f"[ERROR: {e}]"

    async def send_message_with_latency(self, content: str) -> tuple[str, float]:
        """发送消息并返回 (回复内容, 延迟毫秒)"""
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                start = time.time()
                resp = await client.post(
                    f"{self.base_url}/chat/msg",
                    json={
                        "userId": self.user_id,
                        "msgContent": content,
                        "llmId": self.llm_id,
                    },
                )
                latency_ms = (time.time() - start) * 1000
                if resp.status_code == 200:
                    data = resp.json()
                    return _extract_reply(data), latency_ms
                else:
                    return f"[HTTP {resp.status_code}] {resp.text[:100]}", latency_ms
        except httpx.TimeoutException:
            return "[TIMEOUT]", REQUEST_TIMEOUT * 1000
        except Exception as e:
            return f"[ERROR: {e}]", 0.0

    async def send_message_quiet(self, content: str) -> str:
        """发送消息（静默，不打印）"""
        return await self.send_message(content)


def _extract_reply(response_data: dict) -> str:
    """从 API 响应中提取 AI 回复文本"""
    if not response_data:
        return "[EMPTY RESPONSE]"
    # 尝试多种可能的响应结构
    data = response_data.get("data")
    if isinstance(data, str):
        return data
    if isinstance(data, dict):
        for key in ("content", "msg", "reply", "text", "message"):
            val = data.get(key)
            if isinstance(val, str) and val:
                return val
        for key in ("msgContent", "replyContent", "ai_content"):
            val = data.get(key)
            if isinstance(val, str) and val:
                return val
    if isinstance(data, list) and data:
        # 可能是 MessageBlock 列表
        blocks = data
        texts = []
        for block in blocks:
            if isinstance(block, dict):
                t = block.get("content") or block.get("text") or block.get("msg")
                if t:
                    texts.append(str(t))
        if texts:
            return " ".join(texts)
    return str(response_data)[:200]


# ============================================================
# 判定逻辑
# ============================================================
def check_answer(response: str, expected_keywords: list[str]) -> bool:
    """检查回复中是否包含期望的关键词"""
    resp_lower = response.lower()
    for kw in expected_keywords:
        if kw.lower() in resp_lower:
            return True
    return False


# ============================================================
# 报告输出
# ============================================================
def print_report(items: list[VerificationItem], elapsed: float) -> None:
    passed = sum(1 for it in items if it.passed)
    failed = sum(1 for it in items if it.passed is False)
    total = len(items)
    rate = passed / total * 100 if total > 0 else 0

    # 延迟统计
    latencies = [it.latency_ms for it in items if it.latency_ms > 0]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    max_latency = max(latencies) if latencies else 0
    min_latency = min(latencies) if latencies else 0

    print()
    print("=" * 60)
    print("           记忆压力测试报告")
    print("=" * 60)
    print(f"  播种记忆点: {total}条    污染轮数: {POLLUTION_ROUNDS}轮")
    print(f"  总耗时: {elapsed:.0f}秒")
    print("-" * 60)
    print(f"  检索延迟: 平均 {avg_latency:.0f}ms | 最大 {max_latency:.0f}ms | 最小 {min_latency:.0f}ms")
    print("-" * 60)

    for item in items:
        status = "✅" if item.passed else ("❌" if item.passed is False else "⚠️")
        short_reply = item.actual_response[:50].replace("\n", " ")
        print(f"  {status} {item.question}")
        print(f"     期望: {' / '.join(item.expected_keywords)} | {item.latency_ms:.0f}ms | {short_reply}")

    print("-" * 60)
    print(f"  记忆留存率: {passed}/{total} = {rate:.1f}%")
    print(f"  通过: {passed}  失败: {failed}")
    print("=" * 60)


# ============================================================
# 主流程
# ============================================================
async def main():
    client = ChatClient(BASE_URL, USER_ID, LLM_ID)
    items = build_verification_items()
    start_time = time.time()

    print("=" * 60)
    print("  角色记忆压力测试")
    print(f"  API: {BASE_URL}/chat/msg")
    print(f"  userId={USER_ID[:8]}...  llmId={LLM_ID[:8]}...")
    print(f"  播种 {SEEDING_ROUNDS}轮 + 污染 {POLLUTION_ROUNDS}轮")
    print("=" * 60)

    # ---------- 清除旧数据 ----------
    print("\n[0] 清除旧记忆...")
    await client.clear_memory()
    await asyncio.sleep(1)

    # ---------- Phase 1: 播种期 ----------
    print(f"\n{'='*40}")
    print(f"[1] 播种期 ({SEEDING_ROUNDS}轮)")
    print(f"{'='*40}")

    for i, (content, _) in enumerate(SEEDING_CONVERSATIONS, 1):
        print(f"\n--- 播种第{i}轮 ---")
        print(f"  USER: {content[:50]}...")
        reply = await client.send_message(content)
        short_reply = reply[:80].replace("\n", " ")
        print(f"  AI: {short_reply}")
        await asyncio.sleep(ROUND_DELAY)

    print(f"\n  ✅ 播种期完成，已植入记忆点")

    # ---------- Phase 2: 污染期 ----------
    print(f"\n{'='*40}")
    print(f"[2] 污染期 ({POLLUTION_ROUNDS}轮)")
    print(f"{'='*40}")

    topic_count = len(POLLUTION_TOPICS)
    for i in range(1, POLLUTION_ROUNDS + 1):
        topic = POLLUTION_TOPICS[(i - 1) % topic_count]
        reply = await client.send_message_quiet(topic)
        # 每10轮打印一次进度
        if i % 10 == 0 or i == 1:
            short_reply = reply[:60].replace("\n", " ")
            print(f"  第{i}轮 | USER: {topic[:30]}... | AI: {short_reply}")
        await asyncio.sleep(ROUND_DELAY)

    print(f"\n  ✅ 污染期完成 ({POLLUTION_ROUNDS}轮)")

    # ---------- Phase 3: 验证期 ----------
    print(f"\n{'='*40}")
    print(f"[3] 验证期 ({len(items)}个记忆点)")
    print(f"{'='*40}")

    for i, item in enumerate(items, 1):
        print(f"\n--- 验证第{i}个 ---")
        print(f"  Q: {item.question}")
        reply, latency_ms = await client.send_message_with_latency(item.question)
        item.actual_response = reply
        item.latency_ms = latency_ms
        item.passed = check_answer(reply, item.expected_keywords)
        status = "✅" if item.passed else "❌"
        short_reply = reply[:60].replace("\n", " ")
        print(f"  {status} 回复: {short_reply}")
        print(f"     延迟: {latency_ms:.0f}ms")
        await asyncio.sleep(ROUND_DELAY)

    elapsed = time.time() - start_time
    print_report(items, elapsed)


if __name__ == "__main__":
    asyncio.run(main())
