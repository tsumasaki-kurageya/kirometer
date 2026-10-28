import json
import tempfile
import unittest
from pathlib import Path

from kirometer import extract_credits, load_sessions, parse_date


class SessionTests(unittest.TestCase):
    def test_credit_extraction(self):
        state = {"session_state": {"conversation_metadata": {"user_turn_metadatas": [
            {"metering_usage": [{"unit": "credit", "value": 1.25}, {"unit": "token", "value": 100}]},
            {"metering_usage": [{"unit": "credit", "value": 2.5}]},
        ]}}}
        self.assertEqual(extract_credits(state), (3.75, 2))

    def test_no_metering_is_missing_not_zero(self):
        self.assertEqual(extract_credits({"session_state": {"conversation_metadata": {}}}), (None, 0))

    def test_load_without_private_text(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "one.json").write_text(json.dumps({
                "session_id": "s1", "cwd": "/project/main", "title": "Test",
                "created_at": "2026-10-28T01:00:00Z",
                "session_state": {"conversation_metadata": {"user_turn_metadatas": [
                    {"metering_usage": [{"unit": "credit", "value": 4.0}]}
                ]}},
            }))
            sessions, diag = load_sessions(Path(directory))
            self.assertEqual(len(sessions), 1)
            self.assertEqual(sessions[0].project, "main")
            self.assertEqual(sessions[0].credits, 4.0)
            self.assertEqual(diag["with_credit"], 1)

    def test_timestamp(self):
        self.assertEqual(parse_date("2026-10-28T01:00:00Z").year, 2026)


if __name__ == "__main__":
    unittest.main()
