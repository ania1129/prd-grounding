---
name: prd-grounding
description: >
  帮产品经理在已有代码库上生成"有代码依据"的 PRD。固定十步流水线：需求理解 → 需求分析 →
  目标与提升指标 → 结合历史代码 → 给出解决方案 → 产品经理选择方案 → 给出解决方式 →
  给出所有逆向流程与候选待确认项 → 技能自动决策所有待确认项 → 最终输出完整版 PRD。
  只有"方案选择"是硬门禁；方案选定后，剩余待确认项由技能按规则自动决策并记录，不再二次确认。
  Use when the user (a product manager) wants to write or update a PRD for an existing
  system, needs a code-grounded current-state baseline and blast-radius analysis, wants
  2+ solution options to choose from, or needs an implementation-ready PRD.
license: MIT
# Ecosystem metadata (claude-skills / skill-tester compatible, kept in sync with lowercase fields)
Name: prd-grounding
Description: 有代码依据的 PRD 生成器：十步流水线 + 唯一硬门禁 + 自动决策 + 代码现状与影响面。
Tier: STANDARD
Category: product-management
Dependencies: python3 (standard library only)
Author: prd-grounding contributors
Version: 0.2.0
Last Updated: 2026-11-10
metadata:
  version: 0.2.0
  tier: STANDARD
  author: prd-grounding contributors
  category: product-management
  domain: prd
  platforms: DSH, Claude Code, Codex CLI
  updated: 2026-11-10
compatibility: 通用 SKILL.md；agents/openai.yaml 供 Codex CLI 使用。
---

# PRD Grounding · 有代码依据的 PRD 生成器

面向产品经理的自用技能：把一个模糊需求，按固定十步流水线，结合**历史代码现状**，
逐阶段产出文件、逐阶段与产品经理确认，最终输出一份可评审、可交给 AI 编码的完整 PRD。

核心原则：**代码是"现在是什么样"的证据，不是"应该做成什么样"的依据。**
"应该"永远来自产品经理；代码只负责把现状、差距、影响面和约束摆到台面上。

## Name

`prd-grounding` — 有代码依据的 PRD 生成器。

## Description

`prd-grounding` 把一个需求按十步流水线落到 PRD：需求理解、需求分析、目标与指标、
结合历史代码、方案候选、PM 选型、详细设计、逆向流程与候选待确认、自动决策、最终 PRD。
代码只提供"现状证据"（必须引用 `path:line`），业务意图由产品经理决定；
**只有方案选择是硬门禁**——方案选定后，剩余待确认项由技能按规则自动决策并记录，
不会反复打断产品经理，直接产出最终 PRD。

## Installation

```bash
# DSH / 通用（项目级）
mkdir -p .agents/skills && cp -r prd-grounding .agents/skills/

# DSH / Claude Code（用户级）
cp -r prd-grounding ~/.agents/skills/      # 或 ~/.claude/skills/

# Codex CLI
cp -r prd-grounding ~/.codex/skills/
```

依赖：Python 3（仅标准库）。无需安装第三方包。

## 什么时候用

- 存量系统上加功能 / 改流程 / 加字段 / 加权限 / 新增接口。
- 需求评审前，需要一份能对着代码逐条核对的 PRD。
- 需要先做影响面 / 爆炸半径分析，再决定做不做、怎么做。
- 需要给 AI 编码准备"AI 实现版"需求文档，要求贴合现有架构。

## 什么时候不用

- 0→1 全新业务，仓库里没有可对照的代码——用普通 PRD 模板即可。
- 纯商业决策、优先级排序、市场判断——代码回答不了。
- 代替产品经理拍板：本技能只提供选项、证据和建议，**不替 PM 做业务决定**。

## 输入

| 输入 | 是否必需 | 说明 |
| --- | --- | --- |
| 需求描述 | 必需 | 一句话做什么 + 给谁 + 解决什么问题；越具体越好。 |
| 代码库路径 | 强烈建议 | 本地绝对路径或仓库 URL。没有代码则阶段 4 降级为"待确认"。 |
| 需求文档 / BRD / 原型 / 历史 PRD | 可选 | 用于理解意图，不作为现状事实来源。 |
| 目标与业务背景 | 可选 | 上级目标、考核口径、已有数据基线。 |
| 约束 | 可选 | 时间、兼容性、合规、人力、灰度要求。 |
| 工作区目录 | 可选 | 默认 `<当前目录>/prd-workspace/<slug>/`，可指定。 |

阻断性缺失（连"要做什么"都不知道）才追问；非阻断项先推进，缺口写入待确认。

## 需求分级（决定 PRD 深度）

生成 PRD 前先判级，写进 `01-requirement.md` 与 PRD 开头；**模块固定不变，按级别决定详略**：

| 级别 | 判断标准 | 写法 |
| --- | --- | --- |
| **L1 一句话需求 / 小改动** | 权限放开、开关、文案、入口/字段微调，一句话能说清 | 只写主流程 + 受影响处的逻辑；详细描述聚焦改动点；未涉及模块写【本次需求不涉及】；控制在 1–2 页 |
| **L2 简单功能迭代** | 单个功能新增/改造，涉及少量模块 | 功能点 2–5 条；详细描述覆盖入口/流程/权限/文案；主流程 + 相关逆向；按需数据验证 |
| **L3 大流程需求** | 跨角色 / 跨系统 / 跨阶段的流程重构 | 逐模块详细描述；主流程 + 逆向 + 状态机 + 权限 + 数据验证；每个模块的输入输出、上下游衔接、异常兜底必须**前后闭环**，不能有断点 |

判不准时按**低一级**写，宁短不长；研发需要更多细节再补。

## 产物与目录

每次 PRD 在独立工作区落盘，便于断点续跑和评审：

```text
prd-workspace/<slug>/
├── state.json                    # 阶段状态、门禁、元信息（脚本维护）
├── 01-requirement.md             # 阶段 1 需求理解
├── 02-analysis.md                # 阶段 2 需求分析
├── 03-goals-metrics.md           # 阶段 3 目标与提升指标
├── 04-code-baseline.md           # 阶段 4 代码现状与影响面
├── 05-solution-options.md        # 阶段 5 方案候选（2–4 个）
├── 06-solution-decision.md       # 门禁 A：PM 选中的方案与理由
├── 07-approach.md                # 阶段 6 解决方式（详细设计）
├── 08-flows-open-questions.md    # 阶段 7 逆向流程与候选待确认清单
├── 09-decision-log.md            # 阶段 9 自动决策记录（技能决定，无需 PM 确认）
└── PRD.md                        # 阶段 10 完整版 PRD
```

**每个阶段必须先写文件，再在对话里汇报**，不允许只说不写。

## 十步流水线

### 阶段 1 · 需求理解

- **目标**：把需求翻译成一份"无歧义、可核对"的理解。
- **动作**：提炼一句话需求、业务背景、目标用户、当前痛点、触发场景、期望结果、
  初版范围（做什么 / 不做什么）、关键约束、术语初稿。
- **产物**：`01-requirement.md`。
- **退出标准**：产品经理能用一句话复述且不觉得跑偏；缺失项已进入待确认。
- **注意**：不臆造业务背景；不把"实现方式"写进理解。

### 阶段 2 · 需求分析

- **目标**：把需求拆成可设计、可估算、可验收的结构。
- **动作**：角色与场景（用户故事）、主流程拆解、功能点清单（编号 `F1…Fn`）、
  边界与非功能、依赖与假设、风险、范围 In/Out、必要性论证。
- **产物**：`02-analysis.md`。
- **退出标准**：功能点 MECE、可编号、可对应到后续影响面；"待代码验证"的假设单独列出。

### 阶段 3 · 目标与提升指标

- **目标**：把"做了有什么用"变成可度量、可归因的指标。
- **动作**：
  - 业务目标 / 用户目标 / 上级目标对齐。
  - 北极星或核心指标：定义、计算公式、当前基线、目标值、口径、数据来源。
  - 护栏指标（不能变差的）。
  - 过程指标与埋点需求初稿。
  - 可达性判断：本次改动能否影响该指标。
- **产物**：`03-goals-metrics.md`。
- **退出标准**：每个指标都有"公式 + 数据来源 + 基线"；无基线的明确标"待确认"。
- **注意**：不要编造数字；没有基线就写"待确认"，并说明如何取数。

### ⛳ 检查点 1 · 需求理解对齐（软门禁）

向产品经理输出一页纸摘要（阶段 1–3 的浓缩版），**请其确认或纠正**，确认后继续。
若 PM 明确说"继续"，视为通过；不要跳过这一步直接读代码。

### 阶段 4 · 结合历史代码

- **目标**：建立事实基线、差距清单和影响面，让后面所有设计都有据可查。
- **动作**：
  1. 运行 `python3 scripts/scan_codebase.py --root <repo> --out <workspace>/04-code-baseline.raw.md`。
  2. 按 `references/code-scan-checklist.md` 定向阅读：入口/路由、数据模型、状态机、
     权限、配置、定时任务、外部集成、测试、历史 PRD、git 历史（`git log --follow`、废弃模块）。
  3. 产出 `04-code-baseline.md`，包含：系统现状、与需求相关的现有实现、能力差距
     （逐条对应 `F*`）、影响面/爆炸半径、技术约束与历史包袱、可复用点。
- **产物**：`04-code-baseline.md`（+ 原始盘点 `04-code-baseline.raw.md`）。
- **退出标准**：每条现状结论标 `事实 / 推断 / 待确认`；`事实` 必须带 `path/to/file.ext:LINE`。
- **没有代码时**：写明"代码不可用"，全部标"待确认"，并列出需要 PM 提供的系统信息清单。

### 阶段 5 · 给出解决方案（方案级）

- **目标**：给出 2–4 个真正不同的可行方案，供 PM 选择。
- **动作**：每个方案包含：一句话方案、核心思路、改动范围、优缺点、风险、成本粗估、
  对目标指标的预期贡献、兼容/迁移/回滚、不适用场景。附对比表与推荐意见。
- **产物**：`05-solution-options.md`。
- **退出标准**：方案数量 ≥2；方案之间是"路线差异"而非措辞差异；每个方案都能落地。
- **禁止**：只给一个方案、或用"推荐方案 + 备选一句话"凑数。

### ⛔ 检查点 2 · 产品经理选择方案（硬门禁）

- 停止执行，等 PM 明确选择（或提出修改/新增方案）。
- 记录到 `06-solution-decision.md`：选中方案、PM 理由、放弃方案及原因、补充约束。
- 运行 `python3 scripts/prd_state.py gate --root <workspace> --gate solution-choice --result passed --note "<选择>"`。
- **未通过此门禁，禁止进入阶段 6，禁止输出最终 PRD。**

### 阶段 6 · 给出解决方式（详细设计）

- **目标**：把选中方案展开成可直接评审、可交给研发/AI 实现的详细设计。
- **动作**：模块/接口/数据/状态/权限/任务/配置拆解；主流程时序；数据模型变更
  （表/字段/索引/迁移/兼容）；接口变更（请求/响应/错误码/版本）；权限与安全；
  非功能（性能/容量/可用性/合规）；埋点与观测；灰度与回滚；实施步骤/里程碑；测试要点。
- **产物**：`07-approach.md`。
- **退出标准**：每个关键设计标清"事实依据（引用 04）"还是"新增设计"；改动点可落到模块/文件级。

### 阶段 7 · 给出所有逆向流程与候选待确认项

- **目标**：把"正常路径"之外的世界补齐，并把所有不确定点显式化。
- **动作**：
  - 逆向流程：撤销/失败/回退/超时/并发/重复提交/退款/删除/补偿。
  - 异常分支：权限不足、依赖失败、数据不一致、限流、幂等。
  - 边界与极端情况；状态机全量（状态 × 事件 × 迁移）。
  - 候选待确认清单：编号 `Q1…Qn`，每条含 问题、重要性、影响范围（对应 `F*`/流程）、
    候选答案（A/B/C）、默认建议。
- **产物**：`08-flows-open-questions.md`。
- **退出标准**：每个主流程都有逆向/异常分支；每个 Q 都有可执行的默认建议。

### 阶段 9 · 自动决策所有待确认项（无需 PM 确认）

方案选定之后，**剩余待确认项由技能自行决策**，不再逐条询问产品经理。

- **决策依据（按优先级）**：
  1. 与现有代码语义一致（例如 `ownerUid || currentHandlerUid`）；
  2. 最小改动、可回滚，不扩大影响面；
  3. 不改变数据可见权限，不影响其他角色；
  4. 采用阶段 7 给出的默认建议；
  5. 风险最低、可灰度验证。
- **动作**：对 `Q1…Qn` 逐条给出结论，写入 `09-decision-log.md`：
  问题、决策、依据、影响、风险、是否需要上线后复盘。
- **真正无法判断时**：不停下来等 PM，写成"假设 + 风险 + 验证方式"，
  在 PRD 中保留为残留风险，并在最终汇报时单独列出。
- **产物**：`09-decision-log.md`。
- **退出标准**：每个 Q 都有明确决策或"假设 + 风险"；无悬空项。
- 运行 `python3 scripts/prd_state.py set --root <workspace> --stage 09-decision-log --status done`。

### 阶段 10 · 最终输出完整版 PRD

- 依据 `assets/prd-template.md` 汇总阶段 1–9 的所有产物，生成 `PRD.md`。
- 必须包含（术语表前置）：术语表、背景与目标、用户与场景、目标与提升指标、需求内容（`F*` + 主流程 +
  逆向流程 + 异常 + 状态机）、数据验证、权限与安全、术语表。
- **不写入最终 PRD**（保留在工作区阶段文件，供研发追溯）：现状基线、影响面、接口变更、
  非功能需求、埋点与观测、灰度回滚迁移、风险与依赖、决策记录、证据索引、变更记录。
- 运行 `python3 scripts/prd_state.py check --root <workspace> --require-final` 自检。
- 汇报：PRD 路径、功能点概览、影响面概览、残留待确认项、证据覆盖率。

## 状态与断点续跑

1. 会话开始先运行 `python3 scripts/prd_state.py status --root <workspace>`。
2. 从 `current_stage` 继续，不重复已完成阶段；不跳过门禁。
3. 每次阶段完成后运行 `python3 scripts/prd_state.py set --root <workspace> --stage <stage> --status done`。
4. `python3 scripts/prd_state.py next --root <workspace>` 会告诉你下一步该做什么。

## 硬规则

1. **事实引用**：现状陈述必须带 `path/to/file.ext:LINE`；否则标 `推断` 或 `待确认`。
2. **先编号，后自动决策**：缺口、矛盾、边界先编号为 `Q*`；方案选定后由技能按规则自动决策并记录；
   只有真正无法判断的才写成"假设 + 风险"，不要臆造成事实。
3. **代码 ≠ 应该**：需求意图来自 PM；代码只提供现状与约束。
4. **阶段产物落盘**：每阶段先写文件，再汇报。
5. **指标可度量**：有公式、有来源、有基线；没有就标待确认。
6. **方案 ≥2 个**：真正的路线差异，不是换措辞。
7. **候选待确认可决策、编号、闭环**：每个 Q 必须有默认建议；阶段 9 必须逐条给结论或假设。
8. **敏感信息**：不粘贴密钥、令牌、个人隐私；引用位置并描述行为即可。
9. **默认无灰度**：所有需求默认不包含灰度流程。只有产品在需求描述中明确要求灰度时，才单独分析灰度方案并写入 PRD；否则不写灰度、也不设计灰度开关。
10. **语言跟随用户**：用户用中文就全程中文，术语保留英文原名。

## 脚本

```bash
# 代码现状盘点（第 4 步）
python3 scripts/scan_codebase.py --root <repo> --out 04-code-baseline.raw.md
python3 scripts/scan_codebase.py --root <repo> --focus "order,refund" --format json

# 阶段状态与门禁（贯穿全程）
python3 scripts/prd_state.py init   --root prd-workspace/<slug> --slug <slug> --title "<title>"
python3 scripts/prd_state.py status --root prd-workspace/<slug>
python3 scripts/prd_state.py next   --root prd-workspace/<slug>
python3 scripts/prd_state.py set    --root prd-workspace/<slug> --stage 04-code-baseline --status done
python3 scripts/prd_state.py gate   --root prd-workspace/<slug> --gate solution-choice --result passed --note "方案B"
python3 scripts/prd_state.py check  --root prd-workspace/<slug> --require-final
```

脚本仅依赖 Python 3 标准库，无需安装第三方包。

## 质量门禁（输出前逐条检查）

- [ ] 10 个阶段产物齐全，唯一硬门禁（方案选择）已通过。
- [ ] 所有"现状"结论带引用或被标注为推断/待确认。
- [ ] 影响面（阶段 4 内部文件）覆盖：路由/页面、数据、任务、配置、权限、测试、监控。
- [ ] 功能点 `F*` 与阶段 2、4、6、8、10 中的编号一致。
- [ ] 每个指标有公式、来源、基线（或标注待确认）。
- [ ] 每个主流程都有逆向/异常/回滚分支。
- [ ] 待确认项全部有编号，且都有自动决策（或"假设 + 风险"）。
- [ ] 阶段文件（04/06/09）内部可追溯；最终 PRD 不写代码证据章节。

## Features

- **十步流水线**：需求理解 → 分析 → 目标指标 → 代码现状 → 方案 → 选型 → 详细设计 →
  逆向/候选待确认 → 自动决策 → 完整 PRD，每步产物落盘。
- **唯一硬门禁 + 自动决策**：方案选择必须由 PM 拍板；选定后剩余待确认项由技能自动决策并记录，
  不再二次确认，直接产出 PRD。
- **代码现状与影响面**：一键盘点 + 定向深挖，输出现状、差距、爆炸半径，事实带 `path:line`。
- **方案候选与决策留痕**：2–4 个路线不同的方案 + 对比表 + PM 选择记录。
- **逆向流程闭环**：撤销/失败/回滚/超时/并发/重复提交/补偿/状态机全覆盖。
- **指标可度量**：公式 + 口径 + 数据来源 + 基线，缺一不可。
- **断点续跑**：`state.json` 记录阶段与门禁，换会话也能接着干。
- **双平台**：DSH / Claude Code 用 `SKILL.md`，Codex CLI 用 `agents/openai.yaml`。

## Usage

### 示例 1：从零开始写一份 PRD

```text
用 prd-grounding 给「订单部分退款」写 PRD：
- 代码库：/path/to/order-service
- 背景：客服只能整单退款，客户想退一件要整单退再重下单
- 目标：降低售后客诉率
先出人类评审版，评审通过再出 AI 实现版。
```

agent 会建 `prd-workspace/order-partial-refund/`，逐阶段落盘，在检查点停下等你确认。

### 示例 2：断点续跑

```text
继续 prd-grounding 的 order-partial-refund：
先 status 看进度，从当前阶段继续，门禁没过不要往下走。
```

### 示例 3：只做影响面分析

```text
用 prd-grounding 帮我评估「订单加部分退款」的影响面，
代码库 /path/to/order-service，只要阶段 4 的现状和影响面，不用出完整 PRD。
```

### 示例 4：直接跑脚本

```bash
python3 scripts/scan_codebase.py --root /path/to/repo --focus "refund,order" --out baseline.md
python3 scripts/prd_state.py init --root prd-workspace/demo --slug demo --title "Demo"
```

## Examples

- `examples/example-requirement.md` — 一个完整需求输入示例。
- `examples/example-walkthrough.md` — 十步流水线每一步产出什么（浓缩版）。
- `expected_outputs/` — 各阶段的样例产物与一个通过门禁的 `state.json`。

## Troubleshooting

1. **跳过检查点 1 直接扫代码**：方向错了，代码读得再细也白搭。
2. **阶段 4 只跑脚本不深挖**：脚本只是地图，结论要靠读者一行行核对。
3. **方案只给一个**：等于把"选择"变成了"通知"，PM 会失去决策空间。
4. **待确认写成"再看看"**：必须给候选答案和默认建议，否则无法闭环。
5. **指标没有基线**：目标值无法验证，等于没指标；没有基线就标"待确认"。
6. **把代码当需求**：代码只说明现状，业务规则必须由 PM 确认。
7. **最终 PRD 编号断链**：`F*`/`Q*` 必须全程一致，否则评审时无法追溯。
8. **把敏感信息写进 PRD**：只引用位置、描述行为，不粘贴密钥/隐私。

## Architecture

- **为什么强制每个阶段落盘**：PRD 是协作产物，评审、复盘、换人都需要可追溯的中间态；
  只在对话里聊，等于没留下证据。
- **为什么把"代码事实"和"业务意图"分开**：代码能告诉你现状，但告诉不了你"应该怎样"；
  混在一起是 PRD 跑偏的最大来源。
- **为什么只留一个硬门禁**：方案选错，后面全废，必须由 PM 拍板；而方案确定之后，
  待确认项大多有明确的工程最优解，交给技能自动决策更快，避免反复打断产品经理。
- **为什么方案要 ≥2 个**：给 PM 选择权，而不是替 PM 做决定。
- **为什么脚本只用标准库**：开源分发零依赖，PM 的电脑上 `python3` 就能跑。

## Contributing

欢迎 Issue / PR。提交前请运行 `python3 tests/validate_skill.py`，并确保两个 hard gate 的状态机不被绕过。

## 文件索引

- `references/workflow.md` — 十步流程、门禁、状态机的完整执行细则。
- `references/code-scan-checklist.md` — 第 4 步要看什么、怎么找、记录什么。
- `references/solution-design.md` — 方案候选、详细设计、逆向流程的写法与检查表。
- `references/generation-rules.md` — 引用、标注、不臆造、脱敏、语言与格式规则。
- `assets/prd-template.md` — 最终 PRD 模板（含证据索引）。
- `assets/checkpoint-template.md` — 三个检查点的汇报模板。
- `scripts/scan_codebase.py` — 代码现状盘点（目录/清单/入口/路由/模型/测试）。
- `scripts/prd_state.py` — 阶段状态、门禁、自检。
- `examples/` — 从需求到最终 PRD 的走查示例。
- `tests/validate_skill.py` — 结构、模板与脚本自检。
