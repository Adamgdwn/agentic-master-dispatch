from pathlib import Path
import tempfile
import unittest

from governed_agent_lab.reporting import load_price_series, sample_strategy_report, summarize_backtest, summarize_price_series


class ReportingTests(unittest.TestCase):
    def test_summarize_backtest_returns_expected_keys(self) -> None:
        report = summarize_backtest([100.0, -50.0, 80.0], fees=[1.0, 1.0, 1.0])
        self.assertEqual(report["trades"], 3)
        self.assertIn("profit_factor", report)
        self.assertIn("equity_curve", report)

    def test_load_price_series_and_summarize(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "prices.csv"
            path.write_text("timestamp,close\n2026-01-01,100\n2026-01-02,101\n2026-01-03,102\n", encoding="utf-8")
            series = load_price_series(path)
            report = summarize_price_series(series, window=2)
            self.assertEqual(report["observations"], 3)
            self.assertEqual(len(report["chart"]), 3)

    def test_sample_strategy_report_contains_market_and_backtest(self) -> None:
        report = sample_strategy_report()
        self.assertIn("market", report)
        self.assertIn("backtest", report)


if __name__ == "__main__":
    unittest.main()
