import unittest
from phase2 import project_name

class WorktreeTests(unittest.TestCase):
    def test_worktree(self):
        self.assertEqual(project_name("/home/u/dk-connect-bm.worktrees/main"), "dk-connect-bm")
        self.assertEqual(project_name("/home/u/dk-connect-bm.worktrees/feature", False), "feature")
        self.assertEqual(project_name("/home/u/dk-connect-bm"), "dk-connect-bm")

    def test_empty_path(self):
        self.assertEqual(project_name(""), "(不明)")

if __name__ == "__main__":
    unittest.main()
