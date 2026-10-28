import json
import tempfile
import unittest
from pathlib import Path
from multi_source import load_multiple, parse_roots


class MultiSourceTests(unittest.TestCase):
    def make_session(self, root, sid, credits, stamp):
        data = {
            "session_id": sid,
            "title": "example",
            "updated_at": stamp,
            "session_state": {"conversation_metadata": {"user_turn_metadatas": [
                {"metering_usage": [{"unit": "credit", "value": credits}]}
            ]}},
        }
        (root / (sid + ".json")).write_text(json.dumps(data), encoding="utf-8")

    def test_deduplicates_by_session_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a", Path(tmp) / "b"
            a.mkdir()
            b.mkdir()
            self.make_session(a, "shared", 4, "2026-10-01T00:00:00Z")
            self.make_session(b, "shared", 6, "2026-10-02T00:00:00Z")
            self.make_session(a, "unique", 2, "2026-10-01T00:00:00Z")
            sessions, mapping, stats = load_multiple([a, b])
            self.assertEqual(len(sessions), 2)
            self.assertEqual(stats["duplicate_sessions"], 1)
            self.assertEqual(sum(s.credits or 0 for s in sessions), 8)
            self.assertEqual(mapping["shared"], b)

    def test_duplicate_directory_is_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = parse_roots(Path(tmp), tmp + "\n" + tmp)
            self.assertEqual(len(paths), 1)

    def test_missing_source_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            sessions, _, stats = load_multiple([Path(tmp), Path(tmp) / "missing"])
            self.assertEqual(sessions, [])
            self.assertEqual(stats["missing_sources"], 1)


if __name__ == "__main__":
    unittest.main()
