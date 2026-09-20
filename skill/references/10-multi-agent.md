# 10 · 多智能体协作（Multi-Agent Collaboration）

> 溯源：《智能体设计模式》第 7 章 多智能体协作 · 板块：协作与通信
> 证据基准：本节内容除特别标注外，均为书中原文确认 [F]。

## 1. 模式定义

多智能体协作模式将系统结构化为多个独立且专用的智能体协作团队。该模式基于任务分解原则，将高层目标拆分为若干子问题，分配给具备相应工具、数据访问或推理能力的智能体。每个智能体有明确角色、目标，并可能访问不同工具或知识库；**模式的核心在于智能体间的互动与协同**。

系统的高效不仅源于分工，更依赖于智能体间的**通信机制**——需要标准化的通信协议和共享本体，使智能体能够交换数据、委派子任务并协调行动。**单一智能体故障不会导致系统整体失效；协作带来的协同效应，使多智能体系统的整体性能远超任何单一智能体** [F]。

## 2. 工作机制

核心链路：任务分解 → 分配给具备相应工具/数据/推理能力的智能体 → 通信协议与共享本体协调 → 综合输出 [F]。

**六种协作形式**（书中完整列表）[F]：

| 形式 | 机制 |
|---|---|
| 顺序交接 | 一智能体完成后输出传递给下一个（类似规划，但明确涉及不同智能体） |
| 并行处理 | 多智能体同时处理问题不同部分，结果后续合并 |
| 辩论与共识 | 基于不同视角和信息源讨论，达成共识或更优决策 |
| 层级结构 | 管理者智能体按工具/插件能力动态分配任务给工作智能体并综合结果 |
| 专家团队 | 不同领域专长智能体（研究员、写作者、编辑）协作完成复杂输出 |
| 批评-审查者 | 生成者产出初步输出，另一组智能体按政策/安全/合规/正确性/质量评审，作者据反馈修订 |

**六种关系与通信结构**（书中图 2）[F]：单智能体 · 网络型（去中心化点对点）· 监督者（有单点故障与瓶颈风险）· **工具型监督者**（提供资源、指导或分析支持，赋能而非强制控制）· 层级型（多层监督者）· 定制型（混合设计）。

## 3. 适用场景与不适用场景

| 适用 ✅ | 不适用 ❌ |
|---|---|
| 复杂研究与分析：检索/总结/趋势发现/综合报告分工 | 明确问题的单领域任务：单智能体更高效 [F] |
| 软件开发：需求分析/代码生成/测试/文档分工 | 低复杂度流程：协作编排开销大于收益 [E] |
| 创意内容生成：调研/文案/设计/排期协作 | |
| 金融分析：数据抓取/情绪分析/技术分析/建议 | |
| 客户支持升级：前线智能体→专家智能体（技术/账单） | |
| 供应链优化：各节点（供应商/制造/分销）智能体协作 | |

书中经验法则 [F]：**当任务过于复杂、需拆分为需专长或工具的子任务时，适合采用该模式。**

## 4. 选型决策要点

1. **复杂度门槛** [F]：单一 LLM 智能体缺乏多样化专长或工具、成为系统瓶颈时，才升级为多智能体。
2. **先选协作形式** [F]：流程线性 → 顺序交接；子任务独立 → 并行处理；需多视角 → 辩论；需调度多种工具 → 层级结构；多领域产出 → 专家团队；质量把关 → 批评-审查者。
3. **监督者结构的单点风险** [F]：监督者型通信结构有单点故障与瓶颈风险；工具型监督者（赋能而非强制控制）更灵活。
4. **通信机制先行设计** [F]：需标准化通信协议与共享本体，否则交换数据、委派子任务会失控。
5. **与规划（04）的边界** [E]：规划解决「步骤怎么拆」，多智能体解决「谁来执行」；计划步骤单一智能体可执行时不要引入多智能体。

## 5. 多框架代码模板

### 5.1 框架无关伪代码

```text
# 专家团队 · 顺序交接形态
researcher = Agent(role="研究员", tools=[search])
writer     = Agent(role="写作者")
editor     = Agent(role="编辑", standards=[质量标准])
crew = Crew(agents=[researcher, writer, editor],   # 共享本体：任务上下文
            flow=sequential, communication=task_context)
result = crew.execute(objective)
# 层级形态则定义 coordinator 动态分派：任务 → 按能力匹配 worker → 综合结果
```

### 5.2 CrewAI（源自书中第 7 章实码 [F]，改写为骨架）

```python
# CrewAI（书中示例：研究员+写作者顺序流程，gemini-2.0-flash）
from crewai import Agent, Task, Crew, Process

# 1. 组件定义：专职角色
researcher = Agent(role='资深研究员',
                   goal='收集主题的准确信息与数据。',
                   backstory='信息检索专家，只依据可靠来源。',
                   allow_delegation=False)
writer = Agent(role='技术写作者',
              goal='把研究发现转化为清晰的博客文章。',
              backstory='擅长把复杂概念写得通俗有趣。')

# 2. 模式接线：任务链 + context 传递（顺序交接）
research_task = Task(description="研究指定主题，输出要点与来源。",
                     expected_output="要点列表与来源。", agent=researcher)
writing_task = Task(description="基于研究发现撰写博客文章。",
                    expected_output="结构完整的文章。",
                    agent=writer,
                    context=[research_task])   # 写作任务依赖研究输出

# 3. 执行入口
crew = Crew(agents=[researcher, writer],
            tasks=[research_task, writing_task],
            process=Process.sequential,
            llm=ChatGoogleGenerativeAI(model="gemini-2.0-flash"))
result = crew.kickoff()
# 4. 观测与护栏：verbose 输出各角色交接轨迹
```

### 5.3 Google ADK（源自书中第 7 章实码 [F]，改写为骨架）

```python
# Google ADK（书中示例：层级 / 循环 / 顺序 / 并行 / 智能体即工具，五形态）
from google.adk.agents import LlmAgent, SequentialAgent, ParallelAgent, LoopAgent
from google.adk.tools import agent_tool

# 1. 组件定义
step1 = Agent(name="step1", output_key="data")     # 输出写入 session.state
step2 = LlmAgent(name="step2",
                 instruction="处理 state['data']")

# 2. 模式接线（四形态选一）：
pipeline = SequentialAgent(name="pipeline", sub_agents=[step1, step2])
# parallel = ParallelAgent(sub_agents=[weather_fetcher, news_fetcher])
# loop     = LoopAgent(max_iterations=10, sub_agents=[...])  # ConditionChecker
#                                                       用 escalate=True 终止
# 层级形态：coordinator 通过 sub_agents=[greeter, task_doer] 建父子关系
# 智能体即工具：AgentTool(agent=image_generator) 供父智能体调用

# 3. 执行入口：Runner 驱动；4. 观测：state 留痕各环节输出
```

### 5.4 LangChain / LangGraph（书中第 7 章未提供专码）

> 本书第 7 章未提供 LangChain 系的多智能体专码。LangGraph 以 Supervisor 图（节点=智能体、边=路由）实现层级协作，为工程实践推断 [E]，需核对最新文档。

```python
# LangGraph（工程实践推断 [E]）
from langgraph.graph import StateGraph, END
supervisor = node(  # 决定下一步分派给哪个 worker 或结束
    role="根据当前状态选择下一个 worker 或 FINISH")
workers = {"researcher": node(...), "writer": node(...)}
graph = StateGraph(TeamState)            # 共享 state 即共享本体
graph.add_node("supervisor", supervisor)
for w in workers: graph.add_node(w, workers[w])
# supervisor 条件边路由 → worker → 回 supervisor → … → END
```

## 6. 反模式与坑点

1. **为炫技堆智能体** [E]：单一智能体足够的任务强上多智能体，编排复杂度与调试成本陡增；遵循「任务复杂到需专长/工具分工」门槛。
2. **监督者单点故障** [F]：监督者通信结构本身是瓶颈与故障点；考虑工具型监督者或去中心化网络型。
3. **无共享本体的通信** [F]：智能体间交换数据、委派子任务需要标准化协议与共享本体；各说各话导致协同失效。
4. **角色定义含糊** [E]：role/goal/backstory 不清晰，职责重叠互相推诿（或重复劳动）；每个智能体须有明确边界。
5. **交接上下文丢失** [E]：顺序交接时下游智能体拿不到上游完整输出（如 CrewAI 漏配 `context`），输出质量塌方。

## 7. 与其他模式的组合

- **多智能体 + 规划（04）**：Planner 拆解计划后分派给专职智能体——书中结论章「自主 AI 研究助手」范式（研究员→写手→评论员）[F]。
- **多智能体 + 反思（07）**：「批评-审查者」协作形式即反思的多智能体实现 [F]。
- **多智能体 + 并行化（03）**：并行处理形态即并行化在团队维度的应用 [F]。
- **多智能体 + A2A（12）**：跨系统/跨平台的智能体间任务交换用 A2A 协议 [F]。
- **多智能体 + 评估（19）**：各角色交接轨迹是多智能体系统调试的主要依据 [E]。

## 8. 评估指标

- **结果导向**：团队任务完成率与产出质量（对照单智能体基线的提升幅度——协同效应是否真实存在）。
- **过程导向**：交接次数与每次交接的信息保真度；管理者分派准确率（层级形态）；角色间重复劳动率。
- **轨迹审查**：完整交接链日志（谁产出什么、传给谁）；单点故障演练下系统是否仍能降级完成 [E]。
