import json
import tempfile
import unittest
from pathlib import Path

from data_quality import audit_metadata


class DataQualityTests(unittest.TestCase):
    def test_counts_and_does_not_emit_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = {
                "title": "private title",
                "session_state": {
                    "rts_model_state": {"model": "secret-model-name"},
                    "conversation_metadata": {"user_turn_metadatas": [
                        {"model": "secret-model-name", "metering_usage": [
                            {"unit": "credit", "value": 1.5}]},
                        {"metering_usage": []}
                    ]}
                }
            }
            (root / "sample.json").write_text(json.dumps(payload))
            (root / "bad.json").write_text("invalid json")
            result = audit_metadata(root)
            self.assertEqual(result["counts"]["files"], 2)
            self.assertEqual(result["counts"]["unreadable"], 1)
            self.assertEqual(result["counts"]["metered_turns"], 1)
            self.assertEqual(result["counts"]["unmetered_turns"], 1)
            self.assertEqual(result["model_fields"]["turn.model"], 1)
            self.assertNotIn("secret-model-name", str(result))
            self.assertNotIn("private title", str(result))


if __name__ == "__main__":
    unittest.main()
