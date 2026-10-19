# Invest Workflow (`invest-workflow`) — ARTi 7-in-1 投研与决策留档 Skill

面向 Claude Code、OpenAI Codex、Cursor 与 Antigravity 的模块化投研工作流 Skill。将**查行情、翻财报、拆业绩会、逆向 DCF 估值标尺、持仓底层因子体检、反方证伪（Pre-mortem & Kill Criteria）、决策日志归档（ARTi Decision Journal）**收敛为 1 个统一入口与 1 个零第三方依赖的 Python 确定性计算脚本。

> **核心理念：它是流程工具，不是拍板工具。确定性归代码与数据，语义归大模型，拍板归人。**

---

## 1. 模块路由（7-in-1 架构）

支持按需单点触发，或在要求“完整分析 / 跑一遍 ARTi / 建档留存”时串联执行：

| 模块编号 | 对应原模块 | 触发场景 | 核心动作与人机边界 |
| :--- | :--- | :--- | :--- |
| **1. `quote`** | **Stock Market Pro**<br>（查行情） | 查报价、区间涨跌、K 线分位、异动归因 | 核对市场与代码后缀（`.SS`/`.SZ`/`.HK`/美股），标注价格时间戳与复权口径，给出 52 周分位、关键放量异动及对应催化剂事件。**省切换时间，不看图编故事。** |
| **2. `fundamentals`** | **Longbridge Fundamentals**<br>（翻财报） | 提炼三大表核心指标、初筛基本面 | 提取营收、经营利润、自由现金流（FCF）、ROE、净负债；强制执行**附注排雷检查**（应收/存货背离、非经常性损益、SBC 股权激励占比）。**管筛选，不管判断；圈出异常点供回查原表。** |
| **3. `earnings`** | **Earnings Analysis**<br>（拆业绩会） | 拆解业绩会纪要、高管表态与指引 | 将管理层官话与财务数据对齐，强制执行：① **跨期指引 Redline Diff**（上季承诺 vs 本季兑现）；② **Q&A 答非所问检测（Evasion Matrix）**。 |
| **4. `dcf`** | **DCF Valuation**<br>（算估值） | 算现金流折现、看当前股价隐含预期 | 调用 [`scripts/invest_tool.py dcf`](scripts/invest_tool.py) 同时运行**正向 DCF** 与**逆向 DCF（Reverse DCF）**：反推当前股价隐含的未来 5 年 FCF 复合增速，并输出 `5×5`（WACC × 增速）敏感性标尺矩阵。**当尺子用，别当目标价用。** |
| **5. `diversification`** | **Diversification**<br>（看持仓结构） | 组合体检、查行业与风格集中度 | 调用 [`scripts/invest_tool.py portfolio`](scripts/invest_tool.py) 计算持仓 HHI、有效持仓数（$N_{\text{eff}}$）、表面行业权重，以及**底层风险因子重叠度**（识别跨行业但同押单一宏观叙事的“伪分散”）。 |
| **6. `stress-test`** | **Audit Investment Thesis**<br>（唱反调 / 证伪） | 下单前泼冷水、持仓逻辑压力测试 | 拆出 2~3 个承重墙假设，执行**事前验尸（Pre-mortem：假设 12 个月后亏损 30%）**，从报表质量、同行交叉证伪、估值杀跌三个维度挑刺，并给出 **3 条可观测、可量化的认错信号（Kill Criteria）**。 |
| **7. `arti`** | **ARTi**<br>（串流程与留档） | 全流程投研组装、写入/复盘决策日志 | 在估值与证伪后设置**人工确认点**，调用 [`scripts/invest_tool.py journal`](scripts/invest_tool.py) 将“核心假设 + 逆向 DCF 隐含预期 + Kill Criteria”归档至本地 Markdown，防止事后“逻辑漂移（Thesis Creep）”。 |

---

## 2. 执行铁律

1. **先报数据口径**：每次输出顶部用单行注明：`标的 | 市场与币种 | 数据截止日 | 财报期 | 复权/会计口径（GAAP/Non-GAAP 或 IFRS/Non-IFRS）`。
2. **严禁伪造数据**：股价、市值、财报数字、业绩会原文必须来自实时检索、API/MCP 工具或用户提供的材料；缺失字段一律标 `N/A` 并说明原因。
3. **计算走脚本，不靠心算**：涉及 DCF 折现、逆向 DCF 隐含增速、敏感性矩阵、持仓 HHI 与风险因子集中度时，强制调用 [`scripts/invest_tool.py`](scripts/invest_tool.py)。
4. **强制反方视角**：凡是跑全流程（`arti`）或估值分析（`dcf`），结尾必须附带模块 6 的 **3 条可量化 Kill Criteria**，不留无条件看多的尾巴。

---

## 3. 安装方式

克隆仓库并复制到对应 Agent 的 `skills` 目录：

```bash
git clone https://github.com/Arthur19940725/invest-workflow-skill.git
```

### PowerShell（Windows）

```powershell
# Claude Code
Copy-Item -Recurse -Force .\invest-workflow-skill "$HOME\.claude\skills\invest-workflow"

# OpenAI Codex
Copy-Item -Recurse -Force .\invest-workflow-skill "$HOME\.codex\skills\invest-workflow"

# Cursor
Copy-Item -Recurse -Force .\invest-workflow-skill "$HOME\.cursor\skills\invest-workflow"

# 通用 .agents 目录
Copy-Item -Recurse -Force .\invest-workflow-skill "$HOME\.agents\skills\invest-workflow"
```

### Bash（macOS / Linux）

```bash
cp -R ./invest-workflow-skill ~/.claude/skills/invest-workflow
cp -R ./invest-workflow-skill ~/.codex/skills/invest-workflow
cp -R ./invest-workflow-skill ~/.cursor/skills/invest-workflow
cp -R ./invest-workflow-skill ~/.agents/skills/invest-workflow
```

---

## 4. 确定性计算脚本 (`scripts/invest_tool.py`)

仅依赖 Python 3 标准库，无任何第三方依赖。

### 4.1 正向 DCF + 逆向 DCF + 5×5 敏感性矩阵 (`dcf`)

```bash
python scripts/invest_tool.py dcf \
  --price 182.10 \
  --shares 3.52 \
  --fcf 12.48 \
  --net-debt -163.13 \
  --wacc 0.115 \
  --term-growth 0.03 \
  --growth-rate 0.30 \
  --years 5
```

### 4.2 持仓结构与底层驱动因子穿透体检 (`portfolio`)

```bash
python scripts/invest_tool.py portfolio \
  --holdings "NVDA:25:半导体:AI资本开支,CEG:15:公用事业:AI资本开支,VRT:15:工业设备:AI资本开支,AAPL:25:消费电子:终端换机,BRK.B:20:金融保险:美国内需"
```

### 4.3 ARTi 决策日志归档 (`journal`)

```bash
python scripts/invest_tool.py journal \
  --dir "./decision-journal" \
  --ticker "00100.HK" \
  --price 182.10 \
  --implied-cagr "33.21%" \
  --action "第一档（165~182 HKD）分批试错观察" \
  --assumptions "ARR转化率>=70%; 2H26毛利率突破25%; 经调整净亏损率阶梯收窄" \
  --kill-criteria "2H26收入<2.2亿美元; 2H26经调整净亏损>3.2亿美元; 应收账款DSO跳升>25天"
```

---

## 5. 测试验证

运行标准库单元测试套件（覆盖正向/逆向 DCF 闭环精度、参数边界校验、组合伪分散识别与决策日志生成）：

```bash
python -I -B scripts/test_invest_tool.py -v
```

---

## 6. 仓库目录结构

```text
.
├── .gitignore
├── README.md
├── SKILL.md                      # Skill 主入口、铁律与模块路由表
├── evals/
│   └── evals.json                # 静态行为评估用例规范
├── references/
│   └── playbooks.md              # 7 个子模块的标准化检查清单与实战手册
└── scripts/
    ├── invest_tool.py            # 确定性计算与决策日志脚本（DCF / Portfolio / Journal）
    └── test_invest_tool.py       # 标准库单元测试套件
```

---

## 7. 免责声明 (Investment Disclaimer)

本仓库及 Skill 仅为投研流程组织与确定性计算辅助工具，不构成任何个性化投资建议、财务顾问服务、适当性评估或收益保证。所有市场行情与财报数据均具有时效性，使用者在做出任何投资决策前应独立核对最新一手监管披露文件（如 SEC EDGAR、港交所披露易、巨潮资讯网）并自行承担投资风险。
