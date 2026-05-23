"""
意图配置文件

用于两层意图判断系统：
- 第一层：规则模板库（正则匹配，微秒级）
- 第二层：语义样例库（向量匹配，毫秒级）

意图类型与 memory_event_extractor.md 的 event_type 严格对齐：
  identity_q    → event_type: identity
  preference_q  → event_type: preference
  boundary_q    → event_type: boundary
  relation_q    → event_type: relation_change
  follow_up_q   → event_type: follow_up, commitment
  share_exp_q   → event_type: share_experience
  emotion_q     → event_type: express_emotion
  interaction_q → event_type: interaction, other
  deep_recall   → 全库检索（scope=[]）
  casual_chat   → 跳过检索
"""

import re
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional

# ============================================================
# 第一层：规则模板库
# ============================================================
# 格式: (pattern, intent, scope, description)

INTENT_RULES: List[Tuple[str, str, str, str]] = [
    # ────────────────────────────────────────────────────────────
    # casual_chat: 日常闲聊，跳过检索
    # ────────────────────────────────────────────────────────────
    (r"^(你好|嗨|hi|hello|hey)$", "casual_chat", "skip", "问候语"),
    (r"^(怎么样|如何|还行|不错|挺好的|好的)$", "casual_chat", "skip", "简单回应"),
    (r"^(是吗|对啊|嗯|哦|啊|好的|明白|了解)$", "casual_chat", "skip", "确认词"),
    (r"^.*(哈哈|嘿嘿|嘻嘻|呵呵|笑死).*$", "casual_chat", "skip", "笑声表达"),
    (r"^(谢谢|感谢|多谢|麻烦你了|辛苦了)$", "casual_chat", "skip", "感谢语"),
    (r"^(没事|没关系|不客气|不用谢)$", "casual_chat", "skip", "客套回应"),
    (r"^(好的好的|行行行|可以可以|OK|ok|OK)$", "casual_chat", "skip", "同意重复"),
    (r"^(拜拜|再见|晚安|早安|晚安)$", "casual_chat", "skip", "告别语"),

    # ────────────────────────────────────────────────────────────
    # identity_q: 身份查询 → event_type: identity
    # ────────────────────────────────────────────────────────────
    (r"^.*叫.*什么.*名字.*$", "identity_q", "identity", "我叫什么名字"),
    (r"^.*名字.*是什么.*$", "identity_q", "identity", "名字是什么"),
    (r"^.*多大了.*$", "identity_q", "identity", "多大了"),
    (r"^.*年龄.*$", "identity_q", "identity", "年龄"),
    (r"^.*职业.*是什么.*$", "identity_q", "identity", "职业是什么"),
    (r"^.*做什么工作.*$", "identity_q", "identity", "做什么工作"),
    (r"^.*我是谁.*$", "identity_q", "identity", "我是谁"),
    (r"^.*身份.*$", "identity_q", "identity", "身份信息"),

    # ────────────────────────────────────────────────────────────
    # preference_q: 偏好查询 → event_type: preference
    # ────────────────────────────────────────────────────────────
    (r"^.*喜欢.*什么.*(颜色|菜|食物|音乐|电影|书|运动|游戏).*$", "preference_q", "preference", "喜欢什么XX"),
    (r"^.*喜欢.*什么.*$", "preference_q", "preference", "喜欢什么"),
    (r"^.*最爱.*什么.*$", "preference_q", "preference", "最爱什么"),
    (r"^.*讨厌.*什么.*$", "preference_q", "preference", "讨厌什么"),
    (r"^.*不喜欢.*什么.*$", "preference_q", "preference", "不喜欢什么"),
    (r"^.*偏好.*什么.*$", "preference_q", "preference", "偏好什么"),

    # ────────────────────────────────────────────────────────────
    # boundary_q: 边界查询 → event_type: boundary
    # ────────────────────────────────────────────────────────────
    (r"^.*不能.*提.*$", "boundary_q", "boundary", "不能提什么"),
    (r"^.*不要.*说.*$", "boundary_q", "boundary", "不要说什么"),
    (r"^.*不能.*说.*$", "boundary_q", "boundary", "不能说什么"),
    (r"^.*禁忌.*$", "boundary_q", "boundary", "禁忌"),
    (r"^.*边界.*$", "boundary_q", "boundary", "边界"),
    (r"^.*有什么.*不能.*$", "boundary_q", "boundary", "有什么不能的"),
    (r"^.*不要.*提.*$", "boundary_q", "boundary", "不要提什么"),
    (r"^.*避开.*什么.*$", "boundary_q", "boundary", "避开什么"),

    # ────────────────────────────────────────────────────────────
    # relation_q: 关系查询 → event_type: relation_change
    # ────────────────────────────────────────────────────────────
    (r"^.*关系.*怎么样.*$", "relation_q", "relation_change", "关系怎么样"),
    (r"^.*关系.*如何.*$", "relation_q", "relation_change", "关系如何"),
    (r"^.*关系.*变化.*$", "relation_q", "relation_change", "关系变化"),
    (r"^.*人际关系.*$", "relation_q", "relation_change", "人际关系"),
    (r"^.*关系.*好吗.*$", "relation_q", "relation_change", "关系好吗"),
    (r"^.*对我.*态度.*$", "relation_q", "relation_change", "对我的态度"),
    (r"^.*对我.*怎么样.*$", "relation_q", "relation_change", "对我怎么样"),
    (r"^.*怎么看.*我.*$", "relation_q", "relation_change", "怎么看我"),
    (r"^.*印象.*怎么样.*$", "relation_q", "relation_change", "印象怎么样"),

    # ────────────────────────────────────────────────────────────
    # follow_up_q: 跟进事项查询 → event_type: follow_up, commitment
    # ────────────────────────────────────────────────────────────
    (r"^刚才.*干什么.*$", "follow_up_q", "follow_up", "刚才准备干什么"),
    (r"^准备.*什么.*$", "follow_up_q", "follow_up", "准备做什么"),
    (r"^几小时后.*什么.*$", "follow_up_q", "follow_up", "几小时后干什么"),
    (r"^明天.*什么.*$", "follow_up_q", "follow_up", "明天做什么"),
    (r"^.*约定.*怎么样.*$", "follow_up_q", "follow_up", "约定怎么样了"),
    (r"^.*承诺.*完成了.*$", "follow_up_q", "follow_up", "承诺完成了吗"),
    (r"^刚才说.*准备.*$", "follow_up_q", "follow_up", "刚才说准备"),
    (r"^记得.*说.*要做.*$", "follow_up_q", "follow_up", "记得说要做什么"),
    (r"^下.*月.*什么.*计划.*$", "follow_up_q", "follow_up", "下个月计划"),

    # ────────────────────────────────────────────────────────────
    # share_exp_q: 经历查询 → event_type: share_experience
    # ────────────────────────────────────────────────────────────
    (r"^去过.*哪里.*$", "share_exp_q", "share_experience", "去过哪里"),
    (r"^做过.*什么.*$", "share_exp_q", "share_experience", "做过什么"),
    (r"^经历.*什么.*$", "share_exp_q", "share_experience", "经历过什么"),
    (r"^上次.*去.*$", "share_exp_q", "share_experience", "上次去"),
    (r"^.*在.*呆过.*$", "share_exp_q", "share_experience", "在哪呆过"),

    # ────────────────────────────────────────────────────────────
    # emotion_q: 情绪查询 → event_type: express_emotion
    # ────────────────────────────────────────────────────────────
    (r"^.*当时.*心情.*$", "emotion_q", "express_emotion", "当时心情"),
    (r"^.*那时候.*感觉.*$", "emotion_q", "express_emotion", "那时候感觉"),
    (r"^.*什么.*情绪.*$", "emotion_q", "express_emotion", "什么情绪"),
    (r"^.*感受.*怎么样.*$", "emotion_q", "express_emotion", "感受怎么样"),

    # ────────────────────────────────────────────────────────────
    # interaction_q: 互动/测试查询 → event_type: interaction, other
    # ────────────────────────────────────────────────────────────
    (r"^测试.*什么.*$", "interaction_q", "interaction", "测试有什么"),
    (r"^我们.*测试.*$", "interaction_q", "interaction", "我们测试"),
    (r"^刚才.*测试.*$", "interaction_q", "interaction", "刚才测试"),
    (r"^.*测试.*记录.*$", "interaction_q", "interaction", "测试记录"),

    # ────────────────────────────────────────────────────────────
    # deep_recall: 深度回忆，全库检索
    # ────────────────────────────────────────────────────────────
    (r"^说过.*什么.*$", "deep_recall", "all", "说过什么"),
    (r"^聊过.*什么.*$", "deep_recall", "all", "聊过什么"),
    (r"^记得.*什么.*$", "deep_recall", "all", "记得什么"),
    (r"^之前.*说过.*$", "deep_recall", "all", "之前说过"),
    (r"^上次.*聊.*$", "deep_recall", "all", "上次聊"),
    (r"^过去.*经历.*$", "deep_recall", "all", "过去经历"),
    (r"^有什么.*有趣.*$", "deep_recall", "all", "有什么有趣的"),
    (r"^我们.*讨论.*$", "deep_recall", "all", "我们讨论"),
    (r"^回忆.*一下.*$", "deep_recall", "all", "回忆一下"),
]


# ============================================================
# 第二层：语义样例库
# ============================================================

INTENT_EXAMPLES: Dict[str, List[str]] = {
    "casual_chat": [
        "你好", "嗨", "怎么样", "还行", "不错", "挺好的", "好的",
        "是吗", "对啊", "嗯", "哦", "哈哈", "嘿嘿", "谢谢", "感谢",
        "没事", "没关系", "拜拜", "再见", "晚安", "OK",
        "好的好的", "行行行", "可以可以", "笑死我了",
        "辛苦了", "麻烦你了", "不客气", "了解", "明白",
    ],

    "identity_q": [
        "我叫什么名字", "我的名字是什么", "你记得我叫什么吗",
        "我多大了", "我今年多大", "我的年龄是多少",
        "我的职业是什么", "我是做什么工作的", "我是什么职业",
        "你还记得我是谁吗", "我的身份是什么",
        "我妹叫什么", "我妹妹的名字", "我家里有谁",
        "我养了什么宠物", "我的狗叫什么名字",
        "我是哪里人", "我在哪个城市",
        "我叫什么来着", "你记得我的名字吗",
    ],

    "preference_q": [
        "我喜欢什么颜色", "我最爱什么颜色",
        "我喜欢吃什么", "我喜欢吃什么菜", "我喜欢的食物",
        "我讨厌吃什么", "我不喜欢吃什么",
        "我喜欢什么音乐", "我喜欢什么电影",
        "我的爱好是什么", "我喜欢做什么",
        "我喜欢什么运动", "我的偏好是什么",
        "我爱什么", "我讨厌什么",
        "我周末喜欢做什么", "我有什么爱好",
        "我喜欢的颜色是什么",
        "我养了什么", "我有什么宠物",
    ],

    "boundary_q": [
        "有什么话题不能提", "有什么不能说的",
        "不能提什么", "不要说什么",
        "禁忌话题是什么", "有什么禁忌",
        "边界在哪里", "我的底线是什么",
        "有什么不能聊的", "不能讨论什么",
        "你不该说什么", "要避开什么话题",
        "有什么话不能说", "什么话题要避开",
        "不要跟我提什么", "不能跟我提什么",
        "我对什么敏感", "有什么雷区",
    ],

    "relation_q": [
        "我和他的关系怎么样", "我们的关系怎么样",
        "关系有什么变化", "关系怎么样",
        "我和同事的关系好吗", "人际关系怎么样",
        "他对我的态度怎么样", "他对我怎么样",
        "他是怎么看我的", "我对他印象怎么样",
        "我和家里人的关系", "和XX的关系有什么变化",
        "我们关系好吗", "你对我印象如何",
        "现在我和他的关系", "最近关系有变化吗",
    ],

    "follow_up_q": [
        "刚才准备干什么", "准备干什么来着",
        "几小时后干什么", "明天做什么",
        "那个约定怎么样了", "承诺的事情完成了吗",
        "刚才说要做什么", "记得说要做什么吗",
        "之后准备干嘛", "我们约好的事呢",
        "刚才的计划是什么", "准备做的事情是什么",
        "几小时后的安排", "明天有什么计划",
        "下个月有什么计划", "我有什么计划",
        "上次说的那个事怎么样了", "记得刚才说准备干什么吗",
        "我们的约定进展怎么样", "承诺的事情有没有完成",
    ],

    "share_exp_q": [
        "去过哪里", "去过什么地方", "去过哪些地方",
        "做过什么有意思的事", "经历过什么",
        "上次去哪了", "上次去了哪里",
        "经历分享有什么", "做过哪些有趣的事",
        "经历过什么有趣的事", "上次去的那个地方",
        "去过的地方有哪些", "做过的事情有什么",
        "经历过的有趣的事",
        "在哪个城市呆过", "之前在哪里待过",
    ],

    "emotion_q": [
        "我当时什么心情", "我那时候什么感受",
        "我对这件事什么情绪", "我当时感觉怎么样",
        "我那时候开心吗", "我当时难过吗",
        "我当时是什么情绪", "我什么感受",
        "我对那个什么感觉", "那时候我的心情",
        "我当时反应怎么样", "我当时情绪如何",
    ],

    "interaction_q": [
        "测试都有什么", "我们刚才测试了什么",
        "测试记录有什么", "刚才的测试内容",
        "测试回复都有什么", "我们测试过什么",
        "测试的内容是什么", "刚才测试的结果",
        "测试记录有哪些", "我们做过的测试",
        "刚才测试的内容是什么", "测试回复都有哪些",
        "测试的记录都在这里吗", "我们之前测试过什么",
        "测试结果怎么样",
    ],

    "deep_recall": [
        "说过什么有趣的事", "聊过什么话题",
        "记得我说过什么吗", "之前我们讨论过什么",
        "上次聊的内容是什么", "过去的经历有什么",
        "有什么有趣的事情", "我们讨论过哪些话题",
        "回忆一下我们聊过什么", "之前说过什么重要的事",
        "记得我们聊过什么吗", "上次我们讨论了什么",
        "过去的对话内容", "有什么值得记住的事",
        "之前聊过什么有意思的", "记得我们说过什么吗",
        "上次聊了哪些内容", "过去的经历分享",
        "有什么有趣的故事", "我们讨论过什么有趣的事",
    ],
}


# ============================================================
# 检索策略配置 — scope 与 event_type 严格对齐
# ============================================================

RETRIEVAL_STRATEGY: Dict[str, Dict] = {
    "casual_chat": {
        "skip": True,
        "top_k": 0,
        "scope": [],
    },
    "identity_q": {
        "skip": False,
        "top_k": 6,
        "scope": ["identity"],
    },
    "preference_q": {
        "skip": False,
        "top_k": 6,
        "scope": ["preference"],
    },
    "boundary_q": {
        "skip": False,
        "top_k": 4,
        "scope": ["boundary"],
    },
    "relation_q": {
        "skip": False,
        "top_k": 4,
        "scope": ["relation_change"],
    },
    "follow_up_q": {
        "skip": False,
        "top_k": 8,
        "scope": ["follow_up", "commitment"],
    },
    "share_exp_q": {
        "skip": False,
        "top_k": 6,
        "scope": ["share_experience"],
    },
    "emotion_q": {
        "skip": False,
        "top_k": 4,
        "scope": ["express_emotion"],
    },
    "interaction_q": {
        "skip": False,
        "top_k": 8,
        "scope": ["interaction", "other"],
    },
    "deep_recall": {
        "skip": False,
        "top_k": 8,
        "scope": [],  # 空=全库检索
    },
    "default": {
        "skip": False,
        "top_k": 4,
        "scope": [],
    },
}


# ============================================================
# 意图类型枚举 — 与 RETRIEVAL_STRATEGY / event_type 三方对齐
# ============================================================

class IntentType:
    CASUAL_CHAT = "casual_chat"
    IDENTITY_Q = "identity_q"
    PREFERENCE_Q = "preference_q"
    BOUNDARY_Q = "boundary_q"
    RELATION_Q = "relation_q"
    FOLLOW_UP_Q = "follow_up_q"
    SHARE_EXP_Q = "share_exp_q"
    EMOTION_Q = "emotion_q"
    INTERACTION_Q = "interaction_q"
    DEEP_RECALL = "deep_recall"
    DEFAULT = "default"


class RetrievalScope:
    """检索范围常量 — 与 memory_event_extractor.md 的 event_type 完全一致"""
    IDENTITY = "identity"
    PREFERENCE = "preference"
    BOUNDARY = "boundary"
    RELATION_CHANGE = "relation_change"
    FOLLOW_UP = "follow_up"
    COMMITMENT = "commitment"
    SHARE_EXPERIENCE = "share_experience"
    EXPRESS_EMOTION = "express_emotion"
    INTERACTION = "interaction"
    OTHER = "other"
    # 特殊值
    SKIP = "skip"
    ALL = "all"


# ============================================================
# 意图结果结构
# ============================================================

@dataclass
class IntentResult:
    """意图判断结果"""
    intent: str
    scope: List[str]
    top_k: int
    skip: bool
    confidence: float = 1.0  # 规则匹配=1.0，语义匹配为实际相似度
