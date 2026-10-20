---
name: invest-workflow
description: "Evidence-first ARTi research workflow with deterministic Reverse-DCF, portfolio-concentration and decision-journal scripts. Use only when the user explicitly invokes invest-workflow or ARTi, or asks to archive or review an investment decision journal (建档留存 / 复盘留档), stress-test a thesis with pre-mortem Kill Criteria (唱反调证伪), or audit a portfolio for hidden single-factor concentration (伪分散 / 底层驱动因子穿透). General stock research, valuation, earnings, and price-zone questions belong to stock-analysis."
---

# Invest Workflow（ARTi 投研工作流）

这是流程工具，不是决策工具：**数据归工具，计算归脚本，语义归你，拍板归用户。**

## 核心原则（附原因）

1. **每个数字都有出处。** 股价、市值、财报数字、业绩会原文只取自本会话的检索结果、API/MCP 工具或用户材料，并在数字旁标注来源（如 `[披露易 2026 中报 p.45]`、`[用户提供]`）。原因：你的训练记忆中的财务数据已过时且可能混淆，投资判断建在错误数字上代价极高。查不到的字段写 `N/A（原因）`；训练记忆里的数字只能作为"待核验线索"出现，不进入脚本和结论。
2. **给尺子，不下指令。** 输出结构化事实、隐含假设、条件式价格标尺（"若隐含增速 ≤ X%，对应价格区间 Y"）和 Kill Criteria。买卖动作留给用户。原因：你不知道用户的仓位、成本、风险承受力，而决策责任在用户。
3. **计算交给脚本。** DCF、逆向 DCF、敏感性矩阵、HHI、因子集中度一律调用 [`scripts/invest_tool.py`](scripts/invest_tool.py)。原因：多步复利与二分求解靠心算容易出错，且结果无法复现。
4. **反证与正证同等用力。** 用户的看多语气越确定，越要认真找反证。用户反驳某条 Kill Criteria 时，只有新证据才能让你修改它。

## 模块路由

**与 `stock-analysis` 的边界**：普通的估值、财报解读、买入区间与目标价请求由 `stock-analysis` 处理。本 Skill 只在用户点名 `invest-workflow` / ARTi，或要求决策留档与复盘、Kill Criteria 证伪、持仓伪分散体检时触发，避免两个 Skill 同时加载。

执行任一模块前，先读 [`references/playbooks.md`](references/playbooks.md) 的对应章节，按其清单完成。单点请求只跑对应模块；用户要求"完整分析 / 跑一遍 ARTi / 建档"时，按下方 ARTi 流程串联。

| 模块 | 触发场景 | 脚本 |
| :--- | :--- | :--- |
| 1 `quote` 查行情 | 报价、区间涨跌、K 线位置、异动归因 | — |
| 2 `fundamentals` 翻财报 | 三大表核心指标、附注排雷 | — |
| 3 `earnings` 拆业绩会 | 管理层表态、指引兑现、Q&A 回避 | — |
| 4 `dcf` 算估值 | 正向 / 逆向 DCF、股价隐含预期 | `dcf` |
| 5 `diversification` 看持仓 | 行业集中度、底层因子伪分散 | `portfolio` |
| 6 `stress-test` 证伪 | 承重墙假设、事前验尸、Kill Criteria | — |
| 7 `arti` 串流程与留档 | 全流程建档、历史留档复盘 | `journal` |

## ARTi 全流程

复制以下清单到回复中，并逐项勾选：

```text
ARTi 进度：
- [ ] 1 quote：价格、52 周分位、异动事件（带时间戳）
- [ ] 2 fundamentals：核心指标 + 附注疑点及回查位置
- [ ] 3 earnings：原文摘录 → 指引 Diff → 回避矩阵（无纪要则标 N/A）
- [ ] 4 dcf：脚本输出 + 输出检查通过
- [ ] 5 diversification：仅当用户提供了持仓
- [ ] 6 stress-test：2~3 条承重墙假设 + 3 条 Kill Criteria
- [ ] 人工确认点：等待用户确认假设与 Kill Criteria
- [ ] 7 journal：脚本写入成功，回报文件路径
```

- **并行取数**：步骤 1~3 所需的行情、财报、纪要互不依赖，同时检索。
- **人工确认点**：完成步骤 6 后结束本轮回复。列出待确认的承重墙假设、逆向 DCF 隐含增速和 Kill Criteria，请用户确认或修改。收到确认后才调用 `journal`。用户在请求中已明确"直接留档"时，可跳过等待。
- **复盘**：用户要求复盘或提供历史留档时，按 playbooks 模块 7 的复盘流程执行。

## 脚本用法

脚本只依赖 Python 3 标准库。命令写成单行，可同时用于 PowerShell 和 Bash。将 `<SKILL_DIR>` 替换为本 Skill 目录。完整参数见 `python "<SKILL_DIR>/scripts/invest_tool.py" <子命令> --help`。

**dcf**：正向 DCF + 逆向 DCF 隐含增速 + 5×5（WACC × 增速）敏感性矩阵。

```bash
python "<SKILL_DIR>/scripts/invest_tool.py" dcf --price 135.0 --shares 24.5 --fcf 60.0 --net-debt -25.0 --wacc 0.095 --term-growth 0.03 --growth-rate 0.22 --years 5
```

- `--price` 与 `--fcf`、`--net-debt` 必须同币种；`--shares` 与 `--fcf` 必须同数量级（如都用"亿"）。
- `--fcf` 必须为正。当期 FCF ≤ 0 时，按 playbooks 模块 4 构造归一化稳态 FCF，并在输出中注明。

**portfolio**：HHI、有效持仓数 N_eff、表面行业 vs 底层因子暴露，单一因子 >30% 时预警。

```bash
python "<SKILL_DIR>/scripts/invest_tool.py" portfolio --holdings "NVDA:25:半导体:AI资本开支,CEG:15:公用事业:AI资本开支,AAPL:25:消费电子:终端换机"
```

- 格式：`代码:权重:表面行业:底层驱动因子`，逗号分隔，权重自动归一化。

**journal**：把核心假设、逆向 DCF 隐含增速、Kill Criteria 写入 `<dir>/<TICKER>-<日期>.md`。`--dir` 默认为 `~/decision-journal`，通常不必传。

```bash
python "<SKILL_DIR>/scripts/invest_tool.py" journal --dir "~/decision-journal" --ticker "NVDA" --price 135.0 --implied-cagr "24.8%" --action "观察 / 建档" --assumptions "云厂商CapEx维持20%+增长; 数据中心毛利率守住72%+" --kill-criteria "单季数据中心毛利率跌破70%; 前三大云厂下调明年CapEx指引; 应收账款周转天数连续两季跳升>15天"
```

- 多条假设或 Kill Criteria 用英文分号 `;` 分隔。同一标的同一天重复写入会覆盖原文件。

**脚本输出检查**（每次运行 `dcf` 后执行）：

1. 脚本报错 `outside the solvable range`（股价超出 -50%~200% 增速对应的价值区间）→ 先查单位和币种，修正后重跑。
2. 终值占 EV 比例 >75% → 在正文提示结论对远期假设高度敏感。
3. 隐含增速与公司近 3 年 FCF 增速相差悬殊 → 先复核输入，再解读为市场预期。

## 输出格式

1. **首行口径**：`标的 | 市场与币种 | 数据截止日 | 财报期 | 复权与会计口径（GAAP/Non-GAAP 或 IFRS/Non-IFRS）`。
2. **表格放数字，正文写机制。** 表格之后用短段落写因果机制、背离点和需回查的原始章节（如 Note X）。
3. **收尾附 Kill Criteria。** `dcf` 和 `arti` 的输出结尾附模块 6 的 3 条 Kill Criteria。
