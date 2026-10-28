import unittest
import pandas as pd
from trends import daily_trends


class TrendsTests(unittest.TestCase):
    def test_spike_detected_after_baseline(self):
        df = pd.DataFrame([
            {"date": "2026-10-01", "credits": 10.0},
            {"date": "2026-10-02", "credits": 10.0},
            {"date": "2026-10-03", "credits": 10.0},
            {"date": "2026-10-04", "credits": 100.0},
        ])
        result = daily_trends(df, multiplier=2.0, minimum=20)
        self.assertEqual(int(result["is_spike"].sum()), 1)
        self.assertAlmostEqual(float(result.iloc[-1]["previous_7d_avg"]), 10.0)

    def test_gaps_are_zero(self):
        df = pd.DataFrame([
            {"date": "2026-10-01", "credits": 10.0},
            {"date": "2026-10-05", "credits": 100.0},
        ])
        result = daily_trends(df)
        self.assertEqual(len(result), 5)
        self.assertEqual(result.loc[1, "credits"], 0)

    def test_empty(self):
        result = daily_trends(pd.DataFrame(columns=["date", "credits"]))
        self.assertTrue(result.empty)


if __name__ == "__main__":
    unittest.main()
