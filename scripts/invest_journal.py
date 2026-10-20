"""Decision Journal archival for the ARTi workflow (invest_tool.py `journal` subcommand)."""

from __future__ import annotations

import argparse
import datetime as dt
import pathlib

# Fixed under the user's home so journals do not scatter across working directories.
DEFAULT_JOURNAL_DIR = "~/decision-journal"


def cmd_journal(args: argparse.Namespace) -> int:
    out_dir = pathlib.Path(args.dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    date_str = args.date or dt.date.today().isoformat()
    safe_ticker = args.ticker.upper().replace("/", "-")
    file_path = out_dir / f"{safe_ticker}-{date_str}.md"

    assumptions_items = [a.strip() for a in args.assumptions.split(";") if a.strip()]
    kill_items = [k.strip() for k in args.kill_criteria.split(";") if k.strip()]

    lines = [
        "---",
        f'ticker: "{safe_ticker}"',
        f'date: "{date_str}"',
        f"entry_price: {args.price}",
        f'implied_5y_fcf_cagr: "{args.implied_cagr}"',
        'status: "active"',
        "---",
        "",
        f"# ARTi 投研决策留档：{safe_ticker} ({date_str})",
        "",
        "## 1. 决策快照",
        f"- **记录时点价格**: `{args.price}`",
        f"- **逆向 DCF 隐含 5 年 FCF 增速**: `{args.implied_cagr}`",
        f"- **持仓动作与仓位**: {args.action}",
        "",
        "## 2. 承重墙假设（Load-Bearing Assumptions）",
    ]
    for idx, item in enumerate(assumptions_items, 1):
        lines.append(f"- [ ] **假设 {idx}**: {item}")

    lines.extend(
        [
            "",
            "## 3. 反方证伪与认错信号（Kill Criteria — 触发即复盘离场）",
        ]
    )
    for idx, item in enumerate(kill_items, 1):
        lines.append(f"- [ ] **认错阈值 {idx}**: {item}")

    lines.extend(
        [
            "",
            "## 4. 事后复盘记录（Review Log）",
            "| 复盘日期 | 当时股价 | 原假设状态（维持/证伪） | 是否触发 Kill Criteria | 复盘结论与动作 |",
            "| :--- | :--- | :--- | :--- | :--- |",
            f"| {date_str} | `{args.price}` | 初始建档 | 否 | 初始归档留存 |",
            "",
        ]
    )

    file_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Decision journal saved to: {file_path}")
    return 0
