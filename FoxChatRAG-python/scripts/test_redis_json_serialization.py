"""
RedisJSON 字符串安全写入回归测试

运行方式：
    python scripts/test_redis_json_serialization.py
"""

import json
import sys
import unittest
from pathlib import Path


project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

STATE_MANAGER_PATH = project_root / "app" / "service" / "chat" / "state_manager.py"


try:
    from app.util.redis_json_util import json_set_safe, serialize_redis_json_value
    IMPORT_ERROR = None
except ImportError as exc:  # 先允许失败，用于 TDD 的红灯阶段
    json_set_safe = None
    serialize_redis_json_value = None
    IMPORT_ERROR = exc


class FakeRedisClient:
    def __init__(self):
        self.commands = []

    def execute_command(self, *args):
        self.commands.append(args)


class RedisJsonSerializationTests(unittest.TestCase):
    def test_module_is_available(self):
        self.assertIsNone(
            IMPORT_ERROR,
            f"app.util.redis_json_util 应该存在并可导入: {IMPORT_ERROR}",
        )

    def test_plain_string_is_serialized_as_valid_json_string(self):
        self.assertIsNotNone(serialize_redis_json_value)
        self.assertEqual(
            serialize_redis_json_value("runtime"),
            json.dumps("runtime", ensure_ascii=False),
        )

    def test_iso_datetime_is_serialized_as_valid_json_string(self):
        self.assertIsNotNone(serialize_redis_json_value)
        self.assertEqual(
            serialize_redis_json_value("2026-04-28T20:28:25.890123"),
            json.dumps("2026-04-28T20:28:25.890123", ensure_ascii=False),
        )

    def test_empty_string_is_serialized_as_empty_json_string(self):
        self.assertIsNotNone(serialize_redis_json_value)
        self.assertEqual(
            serialize_redis_json_value(""),
            json.dumps("", ensure_ascii=False),
        )

    def test_json_set_safe_uses_serialized_payload(self):
        self.assertIsNotNone(json_set_safe)
        fake_client = FakeRedisClient()

        json_set_safe(fake_client, "chat:key", "$.update_source", "runtime")

        self.assertEqual(
            fake_client.commands,
            [
                (
                    "JSON.SET",
                    "chat:key",
                    "$.update_source",
                    json.dumps("runtime", ensure_ascii=False),
                )
            ],
        )

    def test_state_manager_uses_safe_writer_for_last_update(self):
        content = STATE_MANAGER_PATH.read_text(encoding="utf-8")
        self.assertIn("_json_set(key, '$.last_update', datetime.now().isoformat())", content)
        self.assertNotIn(
            "redis_client.execute_command('JSON.SET', key, '$.last_update', datetime.now().isoformat())",
            content,
        )

    def test_state_manager_uses_safe_writer_for_update_source(self):
        content = STATE_MANAGER_PATH.read_text(encoding="utf-8")
        self.assertIn("_json_set(key, '$.update_source', source.value)", content)
        self.assertNotIn(
            "redis_client.execute_command('JSON.SET', key, '$.update_source', source.value)",
            content,
        )

    def test_state_manager_clears_focus_to_empty_string(self):
        content = STATE_MANAGER_PATH.read_text(encoding="utf-8")
        self.assertIn("_json_set(key, '$.current_focus.value', \"\")", content)
        self.assertNotIn('"[]"', content)


if __name__ == "__main__":
    unittest.main(verbosity=2)