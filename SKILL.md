---
name: invest-workflow
description: "Use when the user asks to check stock quotes/K-lines (Stock Market Pro / 查行情), screen financial statements (Longbridge Fundamentals / 翻财报), dissect earnings calls (Earnings Analysis / 拆业绩会), run DCF or Reverse-DCF valuation (DCF Valuation / 算估值), audit portfolio concentration and factor overlap (Diversification / 看持仓结构), stress-test an investment thesis with pre-mortem Kill Criteria (Audit Investment Thesis / 唱反调证伪), or run the end-to-end ARTi research workflow and decision journal (ARTi / 投研流程与复盘留档)."
---

# Invest Workflow (ARTi 7-in-1 投研工作流)

## 核心铁律（人机边界）

> **它是流程工具，不是决策工具。确定性归代码与数据，语义归大模型，拍板归人。**

1. **严禁伪造数据**：股价、市值、财报数字、业绩会原文必须来自实时检索、API/MCP 工具或用户提供的材料；缺失字段一律标 `N/A` 并说明原因。
2. **严禁越界替用户拍板**：不输出空洞的“强烈推荐买入/卖出”。只输出：**结构化事实、隐含假设、反方证伪条件（Kill Criteria）**。
3. **计算走脚本，不靠心算**：涉及 DCF 折现、逆向 DCF 隐含增速、敏感性矩阵、持仓 HHI 与风险因子集中度时，优先调用确定性脚本 [`scripts/invest_tool.py`](scripts/invest_tool.py)。

---

## 模块路由（按需单点调用 vs 全流程串联）

根据用户指令路由到对应模块；仅当用户要求“完整分析 / 跑一遍 ARTi / 建档留存”时串联执行 **1 → 6 → 7**。详细检查清单与输出模板见 [`references/playbooks.md`](references/playbooks.md)。

| 模块编号 | 对应原 Skill | 触发场景 | 核心动作与边界 |
| :--- | :--- | :--- | :--- |
| **1. `quote`** | **Stock Market Pro**<br>（查行情） | 查报价、区间涨跌、K线位置、异动归因 | 核对市场与代码后缀（`.SS`/`.SZ`/`.HK`/美股），标注价格时间戳与复权口径，给出 52 周分位、关键均线/成交量异动及对应事件。**省切换时间，不看图编故事。** |
| **2. `fundamentals`** | **Longbridge Fundamentals**<br>（翻财报） | 提炼三大表核心指标、初筛基本面 | 提取营收、经营利润、自由现金流（FCF）、ROE、净负债；强制执行**附注排雷检查**（应收/存货背离、非经常性损益、SBC 股权激励占比）。**管筛选，不管判断；圈出异常点供回查原表。** |
| **3. `earnings`** | **Earnings Analysis**<br>（拆业绩会） | 拆解业绩会纪要、高管表态与指引 | 将管理层官话与财务数据对齐，强制执行两项动作：① **跨期指引 Diff**（上季承诺 vs 本季兑现，风险提示删改对比）；② **Q&A 答非所问检测**（列出分析师追问的具体数字与管理层绕开的话术）。 |
| **4. `dcf`** | **DCF Valuation**<br>（算估值） | 算现金流折现、看当前股价贵不贵 | 调用 [`scripts/invest_tool.py dcf`](scripts/invest_tool.py) 同时运行**正向 DCF** 与**逆向 DCF（Reverse DCF）**：反推当前股价隐含的未来 5 年 FCF 复合增速，并输出 5×5（WACC × 增速）敏感性矩阵。**当尺子用，别当价格用。** |
| **5. `diversification`** | **Diversification**<br>（看持仓结构） | 组合体检、查行业与风格集中度 | 调用 [`scripts/invest_tool.py portfolio`](scripts/invest_tool.py) 计算持仓 HHI、有效持仓数（$N_{\text{eff}}$）、表观行业权重，以及**底层风险因子重叠度**（识别跨行业但同押单一宏观叙事的隐形集中）。 |
| **6. `stress-test`** | **Audit Investment Thesis**<br>（唱反调 / 证伪） | 下单前泼冷水、持仓逻辑压力测试 | 拆出 2~3 个承重墙假设，执行**事前验尸（Pre-mortem：假设 12 个月后亏损 30%）**，从报表质量、同行交叉证伪、估值杀跌三个维度挑刺，并给出 **3 条可观测、可量化的认错信号（Kill Criteria）**。 |
| **7. `arti`** | **ARTi**<br>（串流程与留档） | 全流程投研组装、写入/复盘决策日志 | 串联前序模块，在估值（模块 4）与证伪（模块 6）后设置**人工确认点**（请用户确认核心假设），最后调用 [`scripts/invest_tool.py journal`](scripts/invest_tool.py) 将“核心假设 + 逆向 DCF 隐含预期 + Kill Criteria”归档至本地 Markdown，供日后复盘对照。 |

---

## 确定性计算脚本用法 (`scripts/invest_tool.py`)

脚本仅依赖 Python 标准库，跨平台可直接运行（将 `<SKILL_DIR>` 替换为当前 Skill 所在目录）：

### 1. 正向 DCF + 逆向 DCF + 敏感性矩阵
```bash
python "<SKILL_DIR>/scripts/invest_tool.py" dcf \
  --price 135.0 \
  --shares 24.5 \
  --fcf 60.0 \
  --net-debt -25.0 \
  --wacc 0.095 \
  --term-growth 0.03 \
  --growth-rate 0.22 \
  --years 5
```
* 输出：当前市值与企业价值（EV）、当前股价隐含的 5 年 FCF 复合增速（Reverse DCF）、给定增速下的每股内在价值、以及 WACC × 增长率 5×5 估值标尺表。

### 2. 持仓结构与底层风险因子体检
```bash
python "<SKILL_DIR>/scripts/invest_tool.py" portfolio \
  --holdings "NVDA:25:半导体:AI资本开支,CEG:15:公用事业:AI资本开支,VRT:15:工业设备:AI资本开支,AAPL:25:消费电子:终端换机,BRK.B:20:金融保险:美国内需"
```
* 格式：`代码:权重:表面行业:底层驱动因子`（权重自动归一化）。
* 输出：Top 集中度、有效持仓数 $N_{\text{eff}}$、表面行业分布 vs 底层驱动因子真实暴露对比，自动标红 `>30%` 的单一因子隐形重仓。

### 3. ARTi 决策日志归档与复盘
```bash
python "<SKILL_DIR>/scripts/invest_tool.py" journal \
  --dir "./decision-journal" \
  --ticker "NVDA" \
  --price 135.0 \
  --implied-cagr "24.8%" \
  --assumptions "1. 云厂商CapEx维持20%+增长; 2. 数据中心毛利率守住72%+" \
  --kill-criteria "1. 单季数据中心毛利率跌破70%; 2. 前三大云厂下调明年CapEx指引; 3. 应收账款周转天数连续两季跳升>15天"
```

---

## 执行纪律

1. **先报数据口径**：每次输出顶部用一行注明：`标的 | 市场与币种 | 数据截止日 | 财报期 | 复权/会计口径（GAAP/Non-GAAP）`。
2. **禁止堆砌表格废话**：表格呈现完数字后，正文只写**因果机制、背离点、需要回看原始财报哪一章节（如 Note X）**。
3. **强制反方视角**：凡是跑全流程（`arti`）或估值分析（`dcf`），结尾必须附带模块 6 的 **3 条可量化 Kill Criteria**，不留无条件看多的尾巴。
