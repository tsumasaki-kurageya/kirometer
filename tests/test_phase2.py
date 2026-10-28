import json
import tempfile
import unittest
from pathlib import Path

from phase2 import project_name, scan_session_jsonl


class Phase2Tests(unittest.TestCase):
    def test_worktree(self):
        self.assertEqual(project_name("/home/u/dk-connect-bm.worktrees/main"), "dk-connect-bm")
        self.assertEqual(project_name("/home/u/dk-connect-bm.worktrees/feature-x", False), "feature-x")
        self.assertEqual(project_name("/home/u/dk-connect-bm"), "dk-connect-bm")

    def test_skill_read_and_shell_candidates(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "one.jsonl"
            events = [
                {"kind": "AssistantMessage", "data": {"content": [
                    {"name": "read", "input": {"path": "/home/u/.kiro/skills/review/SKILL.md"}},
                    {"name": "shell", "input": {"command": "cat /tmp/skills/test/SKILL.md"}},
                    {"name": "write", "input": {"path": "/tmp/skills/no/SKILL.md"}},
                ]}},
                {"kind": "Prompt", "data": {"content": "SKILL.md"}},
            ]
            p.write_text("\n".join(json.dumps(e) for e in events))
            result = scan_session_jsonl(p)
            self.assertEqual(result.read_calls, 1)
            self.assertEqual(result.shell_calls, 1)
            self.assertEqual(result.named_skills["review"], 1)
            self.assertEqual(result.named_skills["test"], 1)

    def test_missing_file(self):
        result = scan_session_jsonl(Path("/unlikely-kirometer-missing-session.jsonl"))
        self.assertEqual(result.read_calls, 0)


if __name__ == "__main__":
    unittest.main()
