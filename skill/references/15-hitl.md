# 15 · 人类参与环节（Human-in-the-Loop，HITL）

> 溯源：《智能体设计模式》第 13 章 人类参与环节（Human-in-the-Loop）· 板块：可靠性与工程化
> 证据基准：本节内容除特别标注外，均为书中原文确认 [F]。

## 1. 模式定义

HITL 模式有意识地将人类认知的独特优势——判断力、创造力、细致理解——与 AI 的计算能力和高效性相结合。这种战略性集成不仅是可选项，**在 AI 系统日益嵌入关键决策流程的背景下往往还是必需**。

HITL 本质上强调人机协同：**它并不把 AI 视为人类工作的替代者，而是定位为增强和提升人类能力的工具**。目标是打造协作生态系统，让人类与智能体各自发挥优势，实现单独无法达成的成果。HITL 的目标不是取代人类输入，而是通过人类理解确保关键判断和决策的质量。

**变体：Human-on-the-loop** [F]：人类专家制定总体策略，AI 负责即时执行以确保合规——「**AI 负责高速执行，人类负责慢速战略**」。

## 2. 工作机制

HITL 涵盖六个关键方面 [F]：

| 方面 | 机制 |
|---|---|
| 人类监督 | 日志审查或实时仪表盘监控智能体表现，确保遵循规范 |
| 干预与纠正 | 错误或模糊场景下请求人类介入；操作员纠正错误、补充数据或引导 |
| 人类反馈用于学习 | 收集反馈优化模型（典型如 RLHF），偏好直接影响学习轨迹 |
| 决策增强 | 智能体提供分析和建议，人类做最终决策 |
| 人机协作 | 智能体处理常规数据，人类负责创造性问题或复杂谈判 |
| 升级策略 | 超出能力范围时按既定协议升级给人类操作员，防止错误发生 |

核心权衡 [F]：**主要缺点是可扩展性不足**——「操作员无法管理数百万任务，因此常需自动化与 HITL 混合以兼顾规模与准确性」。此外效果高度依赖操作员专业水平；敏感信息须严格匿名化后才能暴露给人类操作员。

## 3. 适用场景与不适用场景

| 适用 ✅ | 不适用 ❌ |
|---|---|
| 内容审核：AI 初筛 + 模糊/边界内容人类终裁 | 海量低风险任务：人工节点无法扩展（书中山谷权衡） |
| 金融欺诈检测：AI 标记可疑交易，人类调查终判 | 完全确定性自动化：无人审需求 |
| 法律文档审查：AI 扫描分类，人类复查法律影响 | 高吞吐实时场景：人工介入破坏时延 |
| 复杂客户支持：常规机器人 + 情绪激烈/同理心场景转人工 | |
| 数据标注：人类标注为 AI 提供真值 | |
| 生成式内容优化：人类编辑确保品牌规范 | |
| 自动化网络管理：高风险告警升级人类分析师 | |

## 4. 选型决策要点

1. **风险分级介入** [F]：高风险（金融交易、官方信息外发）必人类核查；低风险自动化——HITL 在**关键节点**实施而非每一步。
2. **四个干预点** [F]（FAQ 口径）：计划审批（多步计划执行前）· 工具使用确认（有现实影响或付费的工具）· 歧义解决（不确定如何继续时）· 最终输出审核（交付前）。
3. **in-the-loop vs on-the-loop** [F]：需逐案人工裁决 → in-the-loop；只需人类定策略、AI 即时执行 → on-the-loop（如自动交易：人类定「70% 科技股/30% 债券、跌破买入价 10% 自动卖出」类规则）。
4. **升级协议必须显式** [F]：智能体须「知道何时应交由人类处理」——升级策略是设计出来的，不是自然涌现的。
5. **隐私与培训成本** [F]：敏感信息暴露给操作员前须匿名化；标注者需专门培训。

## 5. 多框架代码模板

### 5.1 框架无关伪代码

```text
agent = Agent(
    tools=[troubleshoot, create_ticket,
           escalate_to_human],        # 升级工具是 HITL 设计的核心
    instructions="""
      先 troubleshoot 分析 → 指导基础排查 → 未解决则 create_ticket；
      复杂问题超出基础排查范围 → escalate_to_human 转人工。
    """)
# SAFETY: 高风险操作（外发/交易/删除）执行前必须挂人工审批节点
```

### 5.2 Google ADK（源自书中第 13 章实码 [F]，改写为骨架）

```python
# Google ADK（书中示例：技术支持智能体，gemini-2.0-flash-exp）
from google.adk.agents import Agent
from google.adk.tools.tool_context import ToolContext
from google.adk.callbacks import CallbackContext

# 1. 组件定义：三工具，escalate 是 HITL 核心
def troubleshoot_issue(issue: str) -> dict:
    """分析技术问题，给出排查建议。"""
def create_ticket(issue_type: str, details: str) -> dict:
    """登记工单。"""
def escalate_to_human(issue_type: str) -> dict:
    """转人工专家——复杂问题的升级通道。"""

# 2. 模式接线：instruction 显式定义升级策略
support_agent = Agent(
    name="technical_support_specialist",
    instruction=("技术问题处理流程：先用 troubleshoot_issue 分析，"
                 "指导用户基础排查；未解决则 create_ticket；"
                 "复杂问题超出基础排查时用 escalate_to_human。"
                 "保持专业且富有同理心的语气。"),
    tools=[troubleshoot_issue, create_ticket, escalate_to_human])

# 3. 个性化回调：联系 LLM 前动态注入客户上下文
def personalization_callback(ctx: CallbackContext, llm_request):
    info = ctx.state.get("customer_info", {})   # 姓名/等级/最近购买
    llm_request.contents.insert(0, system_msg(f"客户信息：{info}"))
    return None

# 4. 执行入口：Runner + 回调挂载；观测：升级事件全程留痕
# 书中注明：其他主流框架（如 LangChain）也提供类似 HITL 能力
```

### 5.3 LangChain / LangGraph（书中未提供专码，工程实践推断 [E]）

> 本书第 13 章仅提供 ADK 示例。LangGraph 用 `interrupt` 断点实现审批流，需核对最新文档。

```python
# LangGraph（工程实践推断 [E]）
from langgraph.types import interrupt, Command

def human_approval_node(state):
    # 计划审批干预点：暂停等待人类裁决
    decision = interrupt({"plan": state["plan"],
                          "question": "是否批准执行该计划？"})
    # SAFETY: 高风险操作，须人工确认
    return Command(resume=decision)   # "approved" / "rejected" / 修订意见
# 图接线：plan → human_approval → execute（rejected 则回 plan 修订）
```

### 5.4 CrewAI（书中未提供该框架示例）

> 本书第 13 章未提供 CrewAI 的 HITL 示例。CrewAI 提供 `human_input=True` 的任务级人工输入开关，为工程实践推断 [E]，需核对最新文档。

```python
# CrewAI（工程实践推断 [E]）
review_task = Task(description="终稿交付前人工审核",
                   agent=editor,
                   human_input=True)   # 任务执行中请求人类输入
```

## 6. 反模式与坑点

1. **每步都人工** [F]：持续人类干预低效；HITL 应在关键节点（计划审批/工具确认/歧义解决/终审）实施，人类提供战略指导。
2. **升级策略缺失** [F]：智能体「不知道何时该求助」，硬扛超出能力范围的任务导致错误；escalate 工具与升级协议必须显式设计。
3. **人工节点不可扩展** [F]：操作员无法管理数百万任务；需自动化与 HITL 混合，按风险分级设定人工覆盖面。
4. **敏感信息直接暴露给操作员** [F]：未匿名化的隐私数据流经人工环节造成合规风险。
5. **依赖操作员水平而无培训** [F]：HITL 效果高度依赖领域专家的有效干预，标注者需专门培训。

## 7. 与其他模式的组合

- **HITL + 规划（04）**：计划生成后先向用户展示并征求批准（协同规划，Deep Research 做法）[F]。
- **HITL + 工具使用（05）+ 护栏（18）**：有现实影响或付费的工具使用前须人类确认——安全与控制的第一道防线 [F]。
- **HITL + 多智能体（10）**：客户支持升级场景——前线智能体→专家智能体→人类专家的三级升级链 [F]。
- **HITL + 学习适应（09）**：人类反馈（RLHF）直接驱动智能体学习轨迹 [F]。
- **HITL + 目标监控（13）**：监督仪表盘即目标监控的人类接口 [E]。

## 8. 评估指标

- **结果导向**：高危操作事故率（有人审 vs 无人审对照）；升级准确率（升级给人类的案件中真需人工的比率）。
- **过程导向**：人工节点平均响应时长（瓶颈定位）；人工干预率（过高说明自动化不足，过低说明覆盖面缺失）。
- **轨迹审查**：升级触发是否遵守协议（该升未升/不该升乱升）；审批记录完整性（谁、何时、批了什么）[E]。
