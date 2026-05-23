import py_compile
import unittest
from pathlib import Path


class TestHistoryEventRetrievalServiceCompile(unittest.TestCase):
    def test_module_compiles_cleanly(self):
        project_root = Path(__file__).resolve().parents[1]
        target_file = project_root / "app" / "service" / "chat" / "history_event_retrieval_service.py"

        try:
            py_compile.compile(str(target_file), doraise=True)
        except py_compile.PyCompileError as exc:
            self.fail(
                "history_event_retrieval_service.py 应能通过语法编译，但当前失败："
                f"{exc.msg}"
            )


if __name__ == "__main__":
    unittest.main()