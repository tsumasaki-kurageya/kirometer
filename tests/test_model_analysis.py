import json
import tempfile
import unittest
from pathlib import Path
from model_analysis import model_snapshots

class ModelTests(unittest.TestCase):
    def test_model_counts_and_missing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            records = [
                {"session_state":{"rts_model_state":{"model_info":{"model_id":"auto"}},"conversation_metadata":{"user_turn_metadatas":[{"metering_usage":[{"unit":"credit","value":2}]}]}}},
                {"session_state":{"rts_model_state":{"model_info":{"model_id":"claude-opus-5.5"}},"conversation_metadata":{"user_turn_metadatas":[]}}},
                {"session_state":{"rts_model_state":{"model_info":None}}},
            ]
            for i, record in enumerate(records):
                (root / f"{i}.json").write_text(json.dumps(record))
            result=model_snapshots(root)
            self.assertEqual(result["total"],3)
            self.assertEqual(result["counts"]["auto"],1)
            self.assertEqual(result["counts"]["記録なし"],1)
            self.assertEqual(result["metered"]["auto"],1)
            filtered=model_snapshots(root, {"0", "2"})
            self.assertEqual(filtered["total"], 2)
            self.assertEqual(filtered["counts"].get("claude-opus-5.5", 0), 0)
            self.assertEqual(filtered["counts"]["auto"], 1)
            self.assertEqual(model_snapshots(root, set())["total"], 0)

if __name__ == "__main__":
    unittest.main()
