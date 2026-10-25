# -*- coding: utf-8 -*-
"""_load_event_list 截断打捞的单元测试（临时验证用）"""
import sys
sys.stdout.reconfigure(encoding="utf-8")

from app.service.chat.memory.memory_summary_service import _load_event_list

# 1. 正常完整输出
ok = '{"events":[{"content":"a","event_type":"other"}]}'
assert len(_load_event_list(ok)) == 1

# 2. 外层被截断，第 3 个事件被砍一半 → 应捞回前 2 个
truncated = '{"events":[{"event_id":"evt_1","content":"magnetic","event_type":"commitment"},{"event_id":"evt_2","content":"cats","event_type":"preference"},{"event_id":"evt_3","content":"trunc'
events = _load_event_list(truncated)
assert len(events) == 2, events
print("[1] outer-truncated -> salvage 2/3 OK")

# 3. 事件内部含嵌套 dict 字段且被截断 → 极大对象过滤后只留事件本身
nested = '{"events":[{"content":"e1","meta":{"k":"v"},"event_type":"other"},{"content":"e2","meta":{"k":"trunc'
events = _load_event_list(nested)
assert len(events) == 1 and events[0].get("content") == "e1", events
print("[2] nested-field truncation -> maximal objects only OK")

# 4. 前缀噪音 + 完整包装（唯一极大对象含 events）→ 解包
noisy = 'sure! here is the json {"events":[{"content":"x","event_type":"interaction"}]} done'
events = _load_event_list(noisy)
assert len(events) == 1 and events[0].get("content") == "x", events
print("[3] noisy prefix + single wrapper unwrap OK")

# 5. 字符串字面量里的花括号不干扰配平
tricky = r'{"events":[{"content":"braces {inside} string","event_type":"other"},{"content":"trunc'
events = _load_event_list(tricky)
assert len(events) == 1, events
print("[4] braces inside string literal OK")

# 6. 完全垃圾 → 仍然抛 JSONDecodeError（保持旧行为）
try:
    _load_event_list("no json at all")
    raise AssertionError("should raise")
except Exception as e:
    assert type(e).__name__ == "JSONDecodeError"
print("[5] garbage input still raises OK")

print("\nall salvage tests passed")
