#!/usr/bin/env python3
"""
Deterministic calculation and journaling helper for the invest-workflow skill.
Provides:
  1. dcf       - Forward DCF, Reverse DCF (implied 5-year FCF CAGR), and 5x5 sensitivity matrix
  2. portfolio - Portfolio concentration (HHI, N_eff), sector breakdown, and underlying factor overlap
  3. journal   - Decision Journal creation for ARTi workflow archival (see invest_journal.py)
"""

from __future__ import annotations

import argparse
import pathlib
import sys
from typing import Dict, List, Tuple

# `python -I` drops the script directory from sys.path; restore it for the sibling module.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from invest_journal import DEFAULT_JOURNAL_DIR, cmd_journal  # noqa: E402

# Single-factor exposure above this weight triggers a concentration warning (see SKILL.md / playbooks.md).
FACTOR_WARN_THRESHOLD = 0.30
# Implied FCF CAGR search bounds for the reverse DCF.
REVERSE_DCF_G_LOW, REVERSE_DCF_G_HIGH = -0.50, 2.00


def calc_equity_value_per_share(
    fcf: float,
    growth_rate: float,
    wacc: float,
    term_growth: float,
    years: int,
    net_debt: float,
    shares: float,
) -> Tuple[float, float, float]:
    """
    Returns (intrinsic_value_per_share, enterprise_value, terminal_value_weight).
    net_debt = Total Debt - Cash (negative if net cash).
    """
    if wacc <= term_growth:
        raise ValueError(f"WACC ({wacc:.2%}) must be strictly greater than terminal growth ({term_growth:.2%}).")
    if shares <= 0:
        raise ValueError("Shares must be positive.")

    pv_fcfs = 0.0
    projected_fcf = fcf
    for t in range(1, years + 1):
        projected_fcf *= 1.0 + growth_rate
        pv_fcfs += projected_fcf / ((1.0 + wacc) ** t)

    terminal_fcf = projected_fcf * (1.0 + term_growth)
    terminal_value = terminal_fcf / (wacc - term_growth)
    pv_terminal = terminal_value / ((1.0 + wacc) ** years)

    enterprise_value = pv_fcfs + pv_terminal
    equity_value = enterprise_value - net_debt
    per_share = equity_value / shares
    tv_weight = pv_terminal / enterprise_value if enterprise_value > 0 else 0.0
    return per_share, enterprise_value, tv_weight


def solve_reverse_dcf(
    target_price: float,
    fcf: float,
    wacc: float,
    term_growth: float,
    years: int,
    net_debt: float,
    shares: float,
) -> float:
    """Binary search for the implied annual FCF growth rate matching target_price."""
    low, high = REVERSE_DCF_G_LOW, REVERSE_DCF_G_HIGH
    val_low, _, _ = calc_equity_value_per_share(fcf, low, wacc, term_growth, years, net_debt, shares)
    val_high, _, _ = calc_equity_value_per_share(fcf, high, wacc, term_growth, years, net_debt, shares)
    if not val_low <= target_price <= val_high:
        raise ValueError(
            f"Price {target_price:.2f} is outside the solvable range [{val_low:.2f}, {val_high:.2f}] "
            f"for implied growth in [{low:.0%}, {high:.0%}]; check FCF, shares, and net debt units."
        )
    for _ in range(80):
        mid = (low + high) / 2.0
        val, _, _ = calc_equity_value_per_share(fcf, mid, wacc, term_growth, years, net_debt, shares)
        if val < target_price:
            low = mid
        else:
            high = mid
    return (low + high) / 2.0


def cmd_dcf(args: argparse.Namespace) -> int:
    if args.fcf <= 0:
        print("Error: Base FCF (--fcf) must be positive for standard DCF/Reverse-DCF.", file=sys.stderr)
        return 1

    try:
        implied_g = solve_reverse_dcf(
            target_price=args.price,
            fcf=args.fcf,
            wacc=args.wacc,
            term_growth=args.term_growth,
            years=args.years,
            net_debt=args.net_debt,
            shares=args.shares,
        )

        base_g = args.growth_rate if args.growth_rate is not None else implied_g
        fair_price, ev, tv_weight = calc_equity_value_per_share(
            fcf=args.fcf,
            growth_rate=base_g,
            wacc=args.wacc,
            term_growth=args.term_growth,
            years=args.years,
            net_debt=args.net_debt,
            shares=args.shares,
        )
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    market_cap = args.price * args.shares
    current_ev = market_cap + args.net_debt
    upside = (fair_price - args.price) / args.price if args.price > 0 else float("nan")

    print("## 1. DCF & Reverse-DCF 估值标尺摘要\n")
    print("| 指标 | 数值 | 说明 |")
    print("| :--- | :--- | :--- |")
    print(f"| 当前股价 | `{args.price:.2f}` | 当前市值 `{market_cap:.2f}`，企业价值 (EV) `{current_ev:.2f}` |")
    print(f"| 基准自由现金流 (FCF) | `{args.fcf:.2f}` | 当前 EV/FCF = `{current_ev / args.fcf:.1f}x` |")
    print(f"| 折现率 (WACC) / 永续增速 (g) | `{args.wacc:.2%}` / `{args.term_growth:.2%}` | 预测期 `{args.years}` 年 |")
    print(
        f"| **逆向 DCF 隐含 {args.years} 年复合增速** | **`{implied_g:.2%}`** | 当前股价要求未来 {args.years} 年 FCF 每年增长 `{implied_g:.2%}` |"
    )
    if args.growth_rate is not None:
        print(
            f"| 设定增速 (`{base_g:.2%}`) 对应内在价值 | **`{fair_price:.2f}`** | 较当前股价空间 `{upside:+.1%}`，终值占比 `{tv_weight:.1%}` |"
        )
    else:
        print(f"| 终值 (Terminal Value) 现值占比 | `{tv_weight:.1%}` | 占比 >75% 时对远期折现率高度敏感 |")

    print(f"\n## 2. 敏感性标尺矩阵（每股内在价值：WACC vs 未来 {args.years} 年 FCF 增速）\n")
    wacc_steps = [args.wacc - 0.01, args.wacc - 0.005, args.wacc, args.wacc + 0.005, args.wacc + 0.01]
    center_g = base_g
    g_steps = [center_g - 0.06, center_g - 0.03, center_g, center_g + 0.03, center_g + 0.06]

    header = "| WACC \\ FCF CAGR | " + " | ".join(f"`{g:.1%}`" for g in g_steps) + " |"
    sep = "| :--- | " + " | ".join(":---:" for _ in g_steps) + " |"
    print(header)
    print(sep)
    for w in wacc_steps:
        row_cells = []
        for g in g_steps:
            if w <= args.term_growth:
                row_cells.append("N/A")
            else:
                val, _, _ = calc_equity_value_per_share(
                    args.fcf, g, w, args.term_growth, args.years, args.net_debt, args.shares
                )
                marker = "**" if (abs(w - args.wacc) < 1e-6 and abs(g - center_g) < 1e-6) else ""
                row_cells.append(f"{marker}{val:.2f}{marker}")
        print(f"| **`{w:.2%}`** | " + " | ".join(row_cells) + " |")
    return 0


def cmd_portfolio(args: argparse.Namespace) -> int:
    raw_items = [item.strip() for item in args.holdings.split(",") if item.strip()]
    if not raw_items:
        print("Error: --holdings cannot be empty.", file=sys.stderr)
        return 1

    parsed: List[Tuple[str, float, str, str]] = []
    total_raw_weight = 0.0
    for item in raw_items:
        parts = [p.strip() for p in item.split(":")]
        if len(parts) < 2:
            print(f"Error: Invalid holding format '{item}'. Expected TICKER:WEIGHT[:SECTOR[:FACTOR]].", file=sys.stderr)
            return 1
        ticker = parts[0]
        weight = float(parts[1])
        sector = parts[2] if len(parts) >= 3 and parts[2] else "未分类行业"
        factor = parts[3] if len(parts) >= 4 and parts[3] else sector
        parsed.append((ticker, weight, sector, factor))
        total_raw_weight += weight

    if total_raw_weight <= 0:
        print("Error: Total portfolio weight must be positive.", file=sys.stderr)
        return 1

    normalized = [(t, w / total_raw_weight, s, f) for t, w, s, f in parsed]
    normalized.sort(key=lambda x: x[1], reverse=True)

    hhi = sum(w * w for _, w, _, _ in normalized)
    n_eff = 1.0 / hhi if hhi > 0 else 0.0
    top1 = normalized[0][1]
    top3 = sum(w for _, w, _, _ in normalized[:3])
    top5 = sum(w for _, w, _, _ in normalized[:5])

    sector_map: Dict[str, List[Tuple[str, float]]] = {}
    factor_map: Dict[str, List[Tuple[str, float, str]]] = {}
    for t, w, s, f in normalized:
        sector_map.setdefault(s, []).append((t, w))
        factor_map.setdefault(f, []).append((t, w, s))

    print("## 1. 组合集中度指标\n")
    print(f"- **持仓数量**: `{len(normalized)}` 只（有效分散持仓数 $N_{{\\text{{eff}}}}$ = **`{n_eff:.2f}`**，HHI = `{hhi:.3f}`）")
    print(f"- **头部集中度**: Top 1 = `{top1:.1%}` | Top 3 = `{top3:.1%}` | Top 5 = `{top5:.1%}`\n")

    print("## 2. 表面行业分布 (Sector Breakdown)\n")
    print("| 行业 | 合计权重 | 包含标的 |")
    print("| :--- | :--- | :--- |")
    for s, items in sorted(sector_map.items(), key=lambda kv: sum(x[1] for x in kv[1]), reverse=True):
        sw = sum(x[1] for x in items)
        tickers_str = ", ".join(f"{t} ({w:.1%})" for t, w in items)
        print(f"| {s} | `{sw:.1%}` | {tickers_str} |")

    print("\n## 3. 底层驱动因子穿透 (Risk-Factor Overlap)\n")
    print("| 底层驱动因子 | 真实暴露权重 | 跨行业数 | 预警状态 | 涉及标的与表面行业 |")
    print("| :--- | :--- | :--- | :--- | :--- |")
    for f, items in sorted(factor_map.items(), key=lambda kv: sum(x[1] for x in kv[1]), reverse=True):
        fw = sum(x[1] for x in items)
        distinct_sectors = len({s for _, _, s in items})
        if fw > FACTOR_WARN_THRESHOLD and distinct_sectors >= 2:
            status = "⚠️ **伪分散预警（跨行业同押单一因子）**"
        elif fw > FACTOR_WARN_THRESHOLD:
            status = f"⚠️ **单一因子重仓 (>{FACTOR_WARN_THRESHOLD:.0%})**"
        else:
            status = "✅ 正常"
        detail_str = ", ".join(f"{t}[{s} {w:.1%}]" for t, w, s in items)
        print(f"| **{f}** | **`{fw:.1%}`** | `{distinct_sectors}` | {status} | {detail_str} |")

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Invest Workflow (ARTi 7-in-1) Deterministic Helper")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_dcf = sub.add_parser("dcf", help="Run Forward DCF, Reverse DCF, and 5x5 sensitivity matrix")
    p_dcf.add_argument("--price", type=float, required=True, help="Current share price")
    p_dcf.add_argument("--shares", type=float, required=True, help="Diluted shares outstanding (same unit scale as FCF)")
    p_dcf.add_argument("--fcf", type=float, required=True, help="Base annual Free Cash Flow (same unit scale as shares/debt)")
    p_dcf.add_argument("--net-debt", type=float, default=0.0, help="Net Debt = Total Debt - Cash (negative for net cash)")
    p_dcf.add_argument("--wacc", type=float, default=0.095, help="Discount rate WACC (e.g. 0.095 for 9.5%%)")
    p_dcf.add_argument("--term-growth", type=float, default=0.025, help="Terminal growth rate (e.g. 0.025 for 2.5%%)")
    p_dcf.add_argument("--growth-rate", type=float, default=None, help="Optional explicit FCF CAGR for forward DCF")
    p_dcf.add_argument("--years", type=int, default=5, help="Explicit forecast horizon in years (default: 5)")
    p_dcf.set_defaults(func=cmd_dcf)

    p_port = sub.add_parser("portfolio", help="Audit portfolio concentration and underlying risk-factor overlap")
    p_port.add_argument(
        "--holdings",
        type=str,
        required=True,
        help="Comma-separated list of TICKER:WEIGHT[:SECTOR[:FACTOR]]",
    )
    p_port.set_defaults(func=cmd_portfolio)

    p_journal = sub.add_parser("journal", help="Save an ARTi Decision Journal entry")
    p_journal.add_argument("--dir", type=str, default=DEFAULT_JOURNAL_DIR, help="Directory to store journal files")
    p_journal.add_argument("--ticker", type=str, required=True, help="Ticker symbol")
    p_journal.add_argument("--price", type=float, required=True, help="Current stock price at decision time")
    p_journal.add_argument("--implied-cagr", type=str, required=True, help="Implied FCF CAGR from Reverse DCF")
    p_journal.add_argument("--action", type=str, default="观察 / 建档", help="Position action or sizing note")
    p_journal.add_argument("--assumptions", type=str, required=True, help="Semicolon-separated core assumptions")
    p_journal.add_argument("--kill-criteria", type=str, required=True, help="Semicolon-separated quantifiable kill criteria")
    p_journal.add_argument("--date", type=str, default=None, help="Optional YYYY-MM-DD override")
    p_journal.set_defaults(func=cmd_journal)

    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
