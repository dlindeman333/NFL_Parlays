import ast
import pathlib
import time
import unittest

# Exercise the actual helper without importing data dependencies or contacting feeds.
source = ast.parse(pathlib.Path(__file__).with_name("export_automated.py").read_text())
helper = next(n for n in source.body if isinstance(n, ast.FunctionDef) and n.name == "load_with_retry")
namespace = {"time": time}
exec(compile(ast.Module(body=[helper], type_ignores=[]), "<retry helper>", "exec"), namespace)
retry = namespace["load_with_retry"]

class FeedRetryTests(unittest.TestCase):
    def test_recovers(self):
        calls, delays = [], []
        def load():
            calls.append(1)
            if len(calls) < 3:
                raise ConnectionError("temporary")
            return "fresh"
        self.assertEqual(retry(load, "schedule", sleep=delays.append), "fresh")
        self.assertEqual(delays, [5, 10])
    def test_persistent_failure(self):
        delays = []
        def load():
            raise ConnectionError("404")
        with self.assertRaisesRegex(RuntimeError, "without substituting stale data"):
            retry(load, "schedule", sleep=delays.append)
        self.assertEqual(delays, [5, 10])
    def test_no_retry_on_invalid_data(self):
        def load():
            raise ValueError("invalid schema")
        with self.assertRaises(ValueError):
            retry(load, "schedule", sleep=lambda _: self.fail("unexpected retry"))
    def test_immediate_success(self):
        self.assertEqual(retry(lambda: 42, "schedule", sleep=lambda _: self.fail("unexpected retry")), 42)

if __name__ == "__main__":
    unittest.main()
