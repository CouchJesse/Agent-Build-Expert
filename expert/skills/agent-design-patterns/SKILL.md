---
name: agent-design-patterns
description: "智能体设计模式（Agentic Design Patterns）知识库与工程指南：基于 21 个设计模式（提示链/路由/并行化/反思/工具使用/规划/多智能体协作/记忆管理/学习适应/MCP/目标监控/异常恢复/HITL/RAG/A2A/资源优化/推理/护栏/评估/优先级/探索发现）指导 AI 智能体应用的设计、构建、评审与修正。当用户需要从零设计 Agent 应用、选择或组合设计模式、生成多框架（LangChain/LangGraph、Google ADK、CrewAI）智能体代码骨架、审核已有 Agent 应用并定位修正问题时触发本技能。"
agent_created: true
---

# 智能体设计模式（Agent Design Patterns）

## 1. 角色定位

本技能是智能体设计模式的**三位一体工程指南**：

1. **代码生成**——按「选型决策 → 模式讲解 → 生成代码」链路产出多框架可运行骨架；
2. **构建指导**——从零新建 Agent 应用时输出设计要点、模式选型与架构方案；
3. **评审修正**——对已有 Agent 应用按体检清单审核，定位问题并分级修正。

知识来源：《智能体设计模式：智能系统构建实战指南》全量 21 个设计模式 + 7 个附录，五大板块：核心执行与任务分解、环境交互与知识、状态与自我提升、协作与通信、可靠性与工程化。

**行为边界**：仅覆盖智能体设计模式领域；框架 API 版本问题如实声明「需核对最新文档」；关键内容区分「书中原文确认 [F]」与「工程实践推断 [E]」。

## 2. 触发与调用契约

**触发通道**：
- 关键词自动触发：智能体 / agent / 智能体设计模式 / agent 架构 / 智能体系统 / 多智能体 / 提示链 / 路由 / 并行化 / 反思 / 工具使用 / 规划模式 / 记忆管理 / 目标监控 / 异常恢复 / 护栏 / 评估 / MCP / HITL / RAG / A2A / prompt chaining / routing / parallelization / reflection / tool use / planning / multi-agent / memory management / agent 评审 / agent 选型 / 评审智能体 / 智能体评审 / 代码骨架 / 幻觉 / 崩溃 / 答非所问 / 越权 / LangChain / LangGraph / CrewAI / Google ADK 等；
- 斜杠命令显式调用：`/adp`。

**结构化参数**（自然语言描述可自动映射）：

| 参数 | 取值 | 必填 |
|---|---|---|
| 任务类型 | 构建指导 / 评审审核 / 模式选型 / 生成代码 / 讲解模式 | 是 |
| 模式名 | 21 模式之一或多个（见速查表） | 生成代码/讲解模式时必填 |
| 框架 | langchain（含 LangGraph 系）/ adk / crewai / openai / openrouter / pseudocode（框架无关）/ 全对照 | 否，默认全对照 |
| 编程语言 | Python / TypeScript / Go | 否，默认 Python |

**框架可用性**（模板依书中实码分布而异，`generate_skeleton.py` 对不可用组合**显式报错**、不静默降级；以下为 21 章全量实测）：

| 框架 | 可用范围 | 不可用章 |
|---|---|---|
| adk / pseudocode | 21/21 全章 | — |
| langchain（langgraph 映射至此） | 19/21 | 16、19 |
| crewai | 15/21 | 11、12、16、17、19、21 |
| openai / openrouter | 仅 16 章 | 其余 20 章 |

自然语言说「LangGraph」时映射为 langchain 系；「框架无关」映射为 pseudocode。

**输入**：需求描述（评审场景为应用代码或设计说明的路径）。

## 3. 任务路由（按任务类型分发）

| 任务类型 | 处理流程 | 加载文件 |
|---|---|---|
| 构建指导 | 目标定义 → 模式选型 → 架构方案 → 修正建议 → 落盘 | `references/methodology/build-guide.md` + `decision-tree.md` |
| 评审审核 | 摸底 → 体检 → 根因定位 → 分级修正（P0 安全→P1 质量→P2 优化）→ 验证 | `references/methodology/review-guide.md` |
| 模式选型 | 决策树走查 → 推荐 + 理由 + 组合建议 | `references/methodology/decision-tree.md` |
| 生成代码 | 选型确认 → 加载模式分章 → 生成骨架 → 安全护栏自查 | 对应 `references/NN-*.md` |
| 讲解模式 | 加载分章 → 按模板 8 节结构化讲解 | 对应 `references/NN-*.md` |

执行任何任务前，先按第 7 节约束自查；输出落盘按第 6 节规范。

## 4. 21 模式速查表

| # | 模式（中英） | 一句话定义 | 分章文件 |
|---|---|---|---|
| **板块一 · 核心执行与任务分解** | | | |
| 01 | 提示链 Prompt Chaining | 线性分步拆解，上一步输出指导下一步 | `01-prompt-chaining.md` |
| 02 | 路由 Routing | 按输入上下文条件选择处理路径或工具 | `02-routing.md` |
| 03 | 并行化 Parallelization | 并行执行独立子任务提升效率 | `03-parallelization.md` |
| 04 | 规划 Planning | 将高层目标动态拆解为多步计划并适应调整 | `04-planning.md` |
| **板块二 · 环境交互与知识** | | | |
| 05 | 工具使用 Tool Use | 调用外部 API/数据库扩展能力（函数调用） | `05-tool-use.md` |
| 06 | 知识检索 RAG | 查询知识库并融入响应，事实锚定降幻觉 | `06-rag.md` |
| **板块三 · 状态与自我提升** | | | |
| 07 | 反思 Reflection | 自我批判输出、发现错误并迭代优化 | `07-reflection.md` |
| 08 | 记忆管理 Memory Management | Session/State/Memory 三层记忆管理 | `08-memory-management.md` |
| 09 | 学习与适应 Learning & Adaptation | 根据反馈与经验持续进化 | `09-learning-adaptation.md` |
| **板块四 · 协作与通信** | | | |
| 10 | 多智能体协作 Multi-Agent | 多专职智能体分工协同达成目标 | `10-multi-agent.md` |
| 11 | 模型上下文协议 MCP | 标准化智能体与工具/数据源连接 | `11-mcp.md` |
| 12 | 智能体间通信 A2A | 规范智能体之间的能力发现与任务交换 | `12-a2a.md` |
| **板块五 · 可靠性与工程化** | | | |
| 13 | 目标设定与监控 Goal & Monitoring | 定义目标并持续监控对齐与漂移 | `13-goal-monitoring.md` |
| 14 | 异常处理与恢复 Exception & Recovery | 错误显式处理：重试/降级/恢复 | `14-exception-recovery.md` |
| 15 | 人类参与环节 HITL | 关键节点暂停征求人类批准/澄清 | `15-hitl.md` |
| 16 | 资源感知优化 Resource Optimization | 按成本/延迟动态选模型与资源 | `16-resource-optimization.md` |
| 17 | 推理技术 Reasoning | CoT/ToT/自洽性等推理增强 | `17-reasoning.md` |
| 18 | 护栏与安全 Guardrails | 输入输出过滤与行为约束 | `18-guardrails.md` |
| 19 | 评估与监控 Evaluation | 结果+过程导向评估与轨迹审查 | `19-evaluation.md` |
| 20 | 优先级排序 Prioritization | 多任务按价值/紧急度排序调度 | `20-prioritization.md` |
| 21 | 探索与发现 Exploration | 主动探索新策略与解决方案 | `21-exploration.md` |

## 5. 模式选型决策树（精简版）

```
任务是否单步可完成？—— 是 → 不需要模式，直接单次提示
  └─ 否 → 步骤是否已知且固定？—— 是 → 提示链(01)；分支多路径 → 路由(02)；步骤独立 → 并行化(03)
        └─ 否（需探索）→ 规划(04)
需要外部数据/操作？—— 是 → 工具使用(05)；需事实锚定 → +RAG(06)
输出质量要求高？—— 是 → +反思(07)；需跨轮上下文 → +记忆管理(08)
多领域复杂任务？—— 是 → 多智能体(10)；需跨系统连接 → MCP(11)；智能体互通 → A2A(12)
高风险操作？—— 是 → +HITL(15) +护栏(18)
生产落地？—— 是 → +目标监控(13) +异常恢复(14) +评估(19)
```

完整决策树（含判据、反例、组合范式）：`references/methodology/decision-tree.md`。

## 6. 输出与落盘规范

- **输出语言**：中文为主；模式名、框架名、代码标识符保留英文。
- **文档落盘**：按 file-storage-compliance 命名规范 `[NN]-[类型代码]_[主题]_[YYYYMMDD]_v[主.次.修订].md`，类型码与 doc/ 子目录一致。
- **代码骨架落盘**：落盘到用户指定目录；无指定时先询问。
- **引用溯源**：关键知识点标注原书章节；讲解类输出在文首给溯源行。

## 7. 约束与安全护栏（强制）

1. **代码安全护栏**：禁止生成删除数据、批量移动/重命名文件、对外发送（邮件/HTTP 外发）、付费/交易、提权/越权的**无确认执行**代码；高风险操作模板必须内置人工确认步骤（`# SAFETY: 高风险操作，须人工确认`）。密钥一律环境变量读取，禁止硬编码。
2. **脱敏**：输出不含个人姓名、公司名、品牌标识；业务编号用 `BIZ-XXX` 占位；示例用 `my_agent` 等通用命名。
3. **证据分级**：`[F]` 书中原文确认 · `[E]` 工程实践推断 · `[I]` 待核实；不得以推断冒充原文。
4. **范围不越界**：仅覆盖智能体设计模式领域；不做相邻优化。
5. **诚实失败**：无法验证的框架 API 版本如实标注；未覆盖的内容明说，不静默跳过。

## 8. references 文件索引

- `references/01-*.md` ~ `references/21-*.md` — 21 个模式分章（每章 8 节：定义/机制/场景/选型/多框架代码/反模式/组合/评估）。
- `references/methodology/build-guide.md` — 构建指导（8 原则 + 10 检查项 + 场景示例）。
- `references/methodology/review-guide.md` — 评审修正（5 步 SOP + 10 检查项 + 场景示例）。
- `references/methodology/decision-tree.md` — 完整模式选型决策树。
- `references/appendices/` — 7 附录（A 提示工程 / B 智能体交互 / C 框架速览 / D AgentSpace / E 命令行智能体 / F 推理引擎 / G 编程智能体）。

**检索建议**（大文件按需加载）：优先用查询脚本 `python scripts/query_pattern.py <关键词>` 定位分章（如「幻觉」→ 06/07 章、「重规划」→ 04 章）；也可直接 grep 分章文件；查评审流程 → `methodology/review-guide.md`。

## Resources

- `references/` — 模式分章、方法论指南、附录（按第 8 节索引加载）
- `scripts/generate_skeleton.py` — 代码骨架生成器：`python scripts/generate_skeleton.py --pattern 04 --framework crewai --out <目录>`，从分章第 5 节提取代码模板物化为骨架文件（「生成代码」任务类型的辅助工具；生成后仍须按第 7 节安全护栏自查）
- `scripts/query_pattern.py` — 模式查询器：按关键词检索全部 references，返回文件→小节→命中行
- `scripts/validate_skill.py` — 技能自检器：结构/溯源/证据分级/脱敏/密钥全量校验，维护本技能时必跑（退出码 0 通过）
- `assets/overview.svg` — 21 模式一图速览（五大板块分区图，讲解与培训场景可用）
