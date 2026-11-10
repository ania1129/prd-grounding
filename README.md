# prd-grounding

> 给产品经理用的 **有代码依据的 PRD 生成器**。
> 固定十步流水线，唯一硬门禁（方案选择）+ 自动决策，产出可评审、可交给 AI 编码的完整 PRD。

[English summary](#english-summary) · [快速开始](#快速开始) · [十步流水线](#十步流水线) · [核心原则](#核心原则)

**GitHub**: <https://github.com/ania1129/prd-grounding> · **License**: MIT

## 为什么做这个

市面上写 PRD 的 skill 很多，但几乎都只吃「文字输入」：BRD、会议纪要、原型。
**没有一个会去读代码。** 结果就是 PRD 里的"现状"靠猜、"影响面"靠拍脑袋、
"能不能做"到研发评审时才被推翻。

`prd-grounding` 补的就是这一段：先扫代码拿到事实，再让产品经理做决定，最后才写 PRD。
代码负责"现在是什么样"，产品经理负责"应该是什么样"。

## 十步流水线

```text
① 需求理解 → ② 需求分析 → ③ 目标与提升指标
        ⛳ 检查点 1：需求理解对齐（软）
④ 结合历史代码（扫仓库 / 影响面 / 差距）
⑤ 给出解决方案（2–4 个候选，含对比与推荐）
        ⛔ 检查点 2：产品经理选择方案（硬门禁）
⑥ 给出解决方式（详细设计）
⑦ 给出所有逆向流程与候选待确认项（Q1…Qn）
⑨ 技能自动决策所有待确认项（不再询问产品经理）
⑩ 最终输出完整版 PRD
```

只有「方案选择」是硬门禁；方案选定后，剩余待确认项由技能按规则自动决策并记录，
不会反复打断产品经理。每个阶段都落盘，可断点续跑。

## 快速开始

### 1. 安装（三选一）

```bash
# DSH / 通用：项目级
mkdir -p .agents/skills && cp -r prd-grounding .agents/skills/

# DSH / Claude Code：用户级
cp -r prd-grounding ~/.agents/skills/        # 或 ~/.claude/skills/

# Codex CLI
cp -r prd-grounding ~/.codex/skills/
```

### 2. 使用

对 agent 说：

```text
用 prd-grounding 给「订单部分退款」写一份 PRD，
代码库在 /path/to/order-service，需求背景是……
```

agent 会：

1. 建工作区 `prd-workspace/<slug>/`，初始化状态；
2. 逐阶段产出文件，在检查点停下来等你确认；
3. 门禁通过后输出 `PRD.md`。

### 3. 只跑脚本（不依赖任何 agent）

```bash
python3 scripts/scan_codebase.py --root /path/to/repo --out baseline.md
python3 scripts/prd_state.py init --root prd-workspace/demo --slug demo --title "Demo"
python3 scripts/prd_state.py status --root prd-workspace/demo
```

脚本只依赖 Python 3 标准库。

## 产物

```text
prd-workspace/<slug>/
├── 01-requirement.md
├── 02-analysis.md
├── 03-goals-metrics.md
├── 04-code-baseline.md
├── 05-solution-options.md
├── 06-solution-decision.md      # 门禁 A 记录
├── 07-approach.md
├── 08-flows-open-questions.md
├── 09-decision-log.md           # 自动决策记录（技能决定）
├── PRD.md
└── state.json
```

## 核心原则

1. **事实必须带引用**：`path/to/file.ext:LINE`，否则标 `推断` / `待确认`。
2. **代码 ≠ 应该**：代码只给现状和约束，需求意图永远来自产品经理。
3. **不臆造业务决策**：缺口和矛盾进待确认，由 PM 拍板。
4. **方案 ≥2 个**：路线差异，不是换措辞。
5. **指标可度量**：公式 + 数据来源 + 基线，缺一不可。
6. **逆向流程必须全覆盖**：失败、回滚、超时、并发、幂等、补偿。
7. **待确认点闭环**：编号、候选答案、默认建议；方案选定后由技能自动决策并记录。

## 仓库结构

```text
prd-grounding/
├── SKILL.md                       # 技能入口
├── README.md
├── LICENSE                        # MIT
├── agents/openai.yaml             # Codex CLI 配置
├── assets/
│   ├── prd-template.md            # 最终 PRD 模板
│   └── checkpoint-template.md     # 三个检查点汇报模板
├── references/
│   ├── workflow.md                # 十步细则与门禁
│   ├── code-scan-checklist.md     # 代码要看什么
│   ├── solution-design.md         # 方案/设计/逆向写法
│   └── generation-rules.md        # 引用与生成规则
├── scripts/
│   ├── scan_codebase.py           # 代码现状盘点
│   └── prd_state.py               # 阶段状态与门禁
├── examples/                      # 需求示例 + 全流程走查
└── tests/validate_skill.py        # 结构与功能自检
```

## 常见问题

**Q：没有代码库能用吗？**
能，但阶段 4 会降级为"待确认"，方案与设计全部标注"待代码验证"，价值大打折扣。

**Q：会不会把公司代码传出去？**
不会。所有扫描和读写都在本地完成；PRD 里只写 `path:line` 和结论，不粘贴大段专有代码。

**Q：和普通 PRD skill 的区别？**
普通 skill 只产出文档；这里的工作区里还保有代码现状、影响面、方案对比与决策记录，最终 PRD 保持精简。

**Q：能改成别的团队流程吗？**
可以。流水线、门禁和产物都在 `scripts/prd_state.py` 与 `references/workflow.md` 里，改配置即可。

## Roadmap

- [ ] `dshmarket` 插件包发布
- [ ] 支持从 git 历史自动生成"该功能演进简史"
- [ ] 支持把 PRD 直接发布到飞书 / Notion
- [ ] 多语言 PRD 模板

## 贡献

欢迎 Issue / PR。提交前请跑：

```bash
python3 tests/validate_skill.py
```

## License

MIT，见 [LICENSE](LICENSE)。

---

## English summary

`prd-grounding` is a skill for product managers that generates PRDs **grounded in
an existing codebase**. It runs a fixed ten-stage pipeline — requirement
understanding, analysis, goals & metrics, code grounding, solution options, PM
solution choice (hard gate), detailed approach, reverse flows & open questions,
PM confirmation (hard gate), final PRD — and refuses to emit the final PRD until
both hard gates pass. Facts about the current system must cite `path:line`.
Python scripts are standard-library only.
