import argparse
import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("invest_tool.py")
SPEC = importlib.util.spec_from_file_location("invest_tool", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class InvestToolTests(unittest.TestCase):
    def test_calc_equity_value_and_reverse_dcf_roundtrip(self):
        target_g = 0.25
        fair_price, ev, tv_weight = MODULE.calc_equity_value_per_share(
            fcf=12.48,
            growth_rate=target_g,
            wacc=0.115,
            term_growth=0.03,
            years=5,
            net_debt=-92.76,
            shares=3.52,
        )
        self.assertGreater(fair_price, 0.0)
        self.assertGreater(ev, 0.0)
        self.assertGreater(tv_weight, 0.5)

        implied_g = MODULE.solve_reverse_dcf(
            target_price=fair_price,
            fcf=12.48,
            wacc=0.115,
            term_growth=0.03,
            years=5,
            net_debt=-92.76,
            shares=3.52,
        )
        self.assertAlmostEqual(implied_g, target_g, places=4)

    def test_wacc_less_than_or_equal_to_term_growth_raises(self):
        with self.assertRaisesRegex(ValueError, "strictly greater"):
            MODULE.calc_equity_value_per_share(
                fcf=10.0,
                growth_rate=0.15,
                wacc=0.03,
                term_growth=0.03,
                years=5,
                net_debt=0.0,
                shares=1.0,
            )

    def test_cmd_dcf_rejects_non_positive_fcf(self):
        args = argparse.Namespace(
            price=182.10,
            shares=3.52,
            fcf=-2.80,
            net_debt=-92.76,
            wacc=0.115,
            term_growth=0.03,
            growth_rate=0.30,
            years=5,
        )
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            rc = MODULE.cmd_dcf(args)
        self.assertEqual(rc, 1)
        self.assertIn("must be positive", stderr.getvalue())

    def test_cmd_dcf_outputs_summary_and_sensitivity_matrix(self):
        args = argparse.Namespace(
            price=135.0,
            shares=24.5,
            fcf=60.0,
            net_debt=-25.0,
            wacc=0.095,
            term_growth=0.03,
            growth_rate=0.22,
            years=5,
        )
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            rc = MODULE.cmd_dcf(args)
        output = stdout.getvalue()
        self.assertEqual(rc, 0)
        self.assertIn("逆向 DCF 隐含 5 年复合增速", output)
        self.assertIn("敏感性标尺矩阵", output)

    def test_cmd_portfolio_detects_disguised_concentration(self):
        args = argparse.Namespace(
            holdings=(
                "NVDA:25:半导体:AI资本开支,"
                "CEG:15:公用事业:AI资本开支,"
                "VRT:15:工业设备:AI资本开支,"
                "AAPL:25:消费电子:终端换机,"
                "BRK.B:20:金融保险:美国内需"
            )
        )
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            rc = MODULE.cmd_portfolio(args)
        output = stdout.getvalue()
        self.assertEqual(rc, 0)
        self.assertIn("伪分散预警（跨行业同押单一因子）", output)
        self.assertIn("AI资本开支", output)
        self.assertIn("55.0%", output)

    def test_cmd_portfolio_rejects_invalid_holding_format(self):
        args = argparse.Namespace(holdings="INVALID_ITEM_WITHOUT_COLON")
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            rc = MODULE.cmd_portfolio(args)
        self.assertEqual(rc, 1)
        self.assertIn("Invalid holding format", stderr.getvalue())

    def test_cmd_journal_creates_markdown_entry(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            args = argparse.Namespace(
                dir=tmp_dir,
                ticker="00100.HK",
                price=182.10,
                implied_cagr="33.21%",
                action="第一档观察仓",
                assumptions="ARR转化率>=70%; 2H26毛利率突破25%",
                kill_criteria="2H26收入<2.2亿美元; 经调整净亏损>3.2亿美元; 应收账款DSO跳升>25天",
                date="2026-10-19",
            )
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                rc = MODULE.cmd_journal(args)
            self.assertEqual(rc, 0)
            saved_file = Path(tmp_dir) / "00100.HK-2026-10-19.md"
            self.assertTrue(saved_file.exists())
            content = saved_file.read_text(encoding="utf-8")
            self.assertIn('ticker: "00100.HK"', content)
            self.assertIn("## 2. 承重墙假设（Load-Bearing Assumptions）", content)
            self.assertIn("## 3. 反方证伪与认错信号（Kill Criteria — 触发即复盘离场）", content)


if __name__ == "__main__":
    unittest.main()
