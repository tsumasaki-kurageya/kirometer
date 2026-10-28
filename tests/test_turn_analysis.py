import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from turn_analysis import credit_rows, session_turns, parent_diagnostics


class TurnAnalysisTests(unittest.TestCase):
    def test_credit_and_missing(self):
        data = {"session_state": {"conversation_metadata": {"user_turn_metadatas": [
            {"metering_usage": [{"unit": "credit", "value": 1.25}, {"unit": "token", "value": 200}]},
            {"metering_usage": []},
            {"metering_usage": [{"unit": "credit", "value": 2.5}]},
        ]}}}
        self.assertEqual(credit_rows(data), [
            {"turn": 1, "credits": 1.25},
            {"turn": 2, "credits": None},
            {"turn": 3, "credits": 2.5},
        ])

    def test_safe_session_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "s1.json").write_text(json.dumps({
                "session_id": "s1",
                "session_state": {"conversation_metadata": {"user_turn_metadatas": [
                    {"metering_usage": [{"unit": "credit", "value": 4}]}
                ]}}
            }))
            self.assertEqual(session_turns(root, "s1")[0]["credits"], 4)
            self.assertEqual(session_turns(root, "../s1"), [])

    def test_parent_diagnostics_do_not_deduct(self):
        s = [
            SimpleNamespace(session_id="parent", parent_session_id=None, credits=10),
            SimpleNamespace(session_id="child", parent_session_id="parent", credits=3),
            SimpleNamespace(session_id="orphan", parent_session_id="missing", credits=2),
        ]
        result = parent_diagnostics(s)
        self.assertEqual(result["child_sessions"], 2)
        self.assertEqual(result["linked_children"], 1)
        self.assertEqual(result["linked_credit_sum"], 3)


if __name__ == "__main__":
    unittest.main()
