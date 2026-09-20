# 02 · 路由（Routing）

> 溯源：《智能体设计模式》第 2 章 路由 · 板块：核心执行与任务分解
> 证据基准：本节内容除特别标注外，均为书中原文确认 [F]。

## 1. 模式定义

路由（Routing）是为智能体引入条件逻辑的控制机制：根据环境状态、用户输入或前序操作结果，在多个潜在动作之间进行仲裁，将控制流动态导向最合适的专用函数、工具或子流程 [F]。它使智能体从固定执行路径的静态执行者，转变为能够动态评估标准、自适应选择动作的上下文感知系统 [F]。

## 2. 工作机制

路由由**决策组件**与**分发结构**两部分构成 [F]。

决策组件（路由器）的四种实现方式 [F]：

1. **基于 LLM 的路由**：提示模型分析输入并输出指示下一步的标识符（如「仅输出类别：订单状态 / 产品信息 / 技术支持 / 其他」），系统读取输出引导工作流。
2. **基于嵌入的路由**：将输入转为向量嵌入，与各路由目标的嵌入比对相似度，按语义而非关键词分发。
3. **基于规则的路由**：if-else / switch 等预定义逻辑，按关键词、模式或结构化数据分发——比 LLM 更快、更确定，但处理复杂或新颖输入的灵活性低。
4. **基于机器学习模型的路由**：在小规模标注数据上微调的分类器等判别模型，路由逻辑编码进模型权重，推理时不经生成式提示。

流程骨架（框架无关）：

- 输入：用户请求 / 中间状态
- 路由器：LLM 提示 / 规则匹配 / 嵌入相似度 / 分类器 → 产出决策标签
- 分支表：按标签分发到专用处理器（子智能体 / 工具链 / 澄清链）
- 兜底：标签不明确或未命中 → 澄清意图的子智能体或提示链

路由可在智能体操作周期的多个阶段挂载：初始任务分类、处理链中间决定后续动作、或子流程中选择最合适的工具 [F]。框架形态上，LangGraph 以显式状态图定义节点转换，适合需基于累积状态决策的复杂路由；Google ADK 通过定义智能体能力（工具/子智能体），由框架内部自动完成路由（Auto-Flow）[F]。

## 3. 适用场景与不适用场景

| 适用 ✅ | 不适用 ❌ |
|---|---|
| 人机交互意图解析：虚拟助手/AI 教师按意图选检索、升级人工或下一课程模块 [F] | 固定线性流程、路径已知：改用提示链(01) |
| 自动化数据与文档分发：邮件/工单/API 数据按内容导向销售导入、格式转换或紧急升级 [F] | 所有输入同质、单一路径即可处理：无需路由开销 |
| 多工具/多智能体调度：研究系统按目标分配任务给检索/摘要/分析智能体 [F] | 后续动作需运行期多步探索：改用规划(04) |
| 客服机器人分流：区分销售、技术支持、账户管理等问题 [F] | [E] 类目极多且边界模糊：先做层级路由或嵌入聚类降维 |
| 编程助手：先识别语言与意图（调试/解释/翻译）再选工具 [F] | |

## 4. 选型决策要点

1. **经验法则** [F]：当智能体需根据用户输入或当前状态，在多个不同工作流、工具或子智能体间做选择时采用；典型如需对请求分流或分类的应用（客服机器人区分销售、技术支持、账户管理）。
2. **决策器选型** [F]：规则最快最确定，但难处理新颖输入；嵌入适合语义路由（按含义而非关键词）；LLM 最灵活但有延迟与成本；ML 分类器需标注数据，决策编码进权重、推理时不再调用生成模型。
3. **必须设兜底分支** [F]：意图不明确时路由到澄清意图的子智能体或提示链，避免误分发到错误处理器。
4. **显式图 vs 框架自动路由的权衡** [F]：LangGraph 显式图适合复杂多步流程的状态与转换定义；ADK 侧重能力定义、框架自动委托，适合动作明确的智能体。
5. **约束路由器输出** [E]：要求 LLM 只输出类别词并做白名单校验，防止自由文本破坏分发逻辑；路由决策应记录日志便于审计。

## 5. 多框架代码模板

### 5.1 框架无关伪代码

```text
# 路由 = 分类决策 + 条件分发（+ 兜底）
router = Router(
    classify = LLM(prompt="分析请求，只输出类别词", labels=["booker", "info", "unclear"]),
    # 决策器可替换为：规则匹配 / 嵌入相似度 / 微调分类器
)
routes = {
    "booker":  booking_subagent,   # 专用子流程 / 工具链
    "info":    info_subagent,
    "unclear": clarify_chain,      # 兜底：澄清意图
}
decision = router.classify(user_request)
result = routes.get(decision, routes["unclear"]).run(user_request)
```

### 5.2 LangChain / LangGraph（源自书中第 2 章实码 [F]，改写为骨架）

```python
# LangChain（书中第 2 章示例，版本需核对最新文档）
# 1. 组件定义：LLM 分类链 + 三个子智能体处理器（模拟多智能体委托）
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableBranch

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
# 密钥经环境变量 GOOGLE_API_KEY 读取

def booking_handler(request: str) -> str:
    # SAFETY: 预订属交易类操作，实码中须经人工确认后执行；此处仅模拟
    return f"已模拟处理预订请求：{request}"

def info_handler(request: str) -> str:
    return f"信息检索结果（模拟）：{request}"

def unclear_handler(request: str) -> str:
    return "意图不明确，请补充说明您的需求。"

# 2. 模式接线：分类链产出 decision → RunnableBranch 条件分发（末位为兜底分支）
router_prompt = ChatPromptTemplate.from_messages([
    ("system", "分析用户请求，只输出一个词：'booker'、'info' 或 'unclear'。"),
    ("user", "{request}")])
router_chain = router_prompt | llm | StrOutputParser()

delegation = RunnableBranch(
    (lambda x: x["decision"].strip() == "booker",
     RunnablePassthrough.assign(output=lambda x: booking_handler(x["request"]))),
    (lambda x: x["decision"].strip() == "info",
     RunnablePassthrough.assign(output=lambda x: info_handler(x["request"]))),
    RunnablePassthrough.assign(output=lambda x: unclear_handler(x["request"])),  # 默认分支
)
coordinator_agent = ({"decision": router_chain, "request": RunnablePassthrough()}
                     | delegation | (lambda x: x["output"]))

# 3. 执行入口
result = coordinator_agent.invoke({"request": "帮我预订一家酒店。"})  # TODO(user): 替换请求
print(result)
# 4. 观测与护栏：记录 decision 追踪路由决策；兜底分支触发时应告警
```

### 5.3 Google ADK（源自书中第 2 章实码 [F]，改写为骨架）

```python
# google-adk（书中第 2 章示例，版本需核对最新文档）
# 1. 组件定义：子智能体配 FunctionTool，协调者只委托、不直接作答
from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.adk.tools import FunctionTool

def booking_handler(request: str) -> str:
    # SAFETY: 交易类操作须人工确认；此处仅模拟
    return f"已模拟处理预订请求：{request}"

def info_handler(request: str) -> str:
    return f"信息检索结果（模拟）：{request}"

booking_agent = Agent(name="booking_agent", model="gemini-2.0-flash",
    description="专门处理机票和酒店预订请求。", tools=[FunctionTool(booking_handler)])
info_agent = Agent(name="info_agent", model="gemini-2.0-flash",
    description="专门提供一般信息与答疑。", tools=[FunctionTool(info_handler)])

# 2. 模式接线：sub_agents 声明委托关系，ADK Auto-Flow 按指令自动路由
coordinator = Agent(
    name="coordinator",
    model="gemini-2.0-flash",
    instruction=("你是主协调者，只分析请求并委托：预订类交 booking_agent，"
                 "一般信息交 info_agent。不要直接回答用户。"),
    sub_agents=[booking_agent, info_agent])

# 3. 执行入口：经 InMemoryRunner 会话逐事件提取最终响应
runner = InMemoryRunner(coordinator)
# async for event in runner.run(user_id=..., session_id=...,
#     new_message=types.Content(role="user", parts=[types.Part(text="...")])):
#     ...  # TODO(user): 取 event.is_final_response() 的文本
# 4. 观测与护栏：不明确请求应路由到澄清提示或升级人工（HITL）
```

### 5.4 CrewAI（本书该章未提供 CrewAI 示例，以下为工程实践推断 [E]，需核对最新文档）

```python
# CrewAI（版本需核对最新文档）
# 1. 组件定义：分类器智能体 + 专职处理智能体
from crewai import Agent, Task, Crew

classifier = Agent(role="请求分类器",
    goal="将用户请求分类为 booking / info / unclear，只输出类别词",
    backstory="你只做分类，不处理请求内容。", allow_delegation=False)
booking_agent = Agent(role="预订专员", goal="处理预订请求（模拟）",
    backstory="你负责订单类请求。", allow_delegation=False)

classify_task = Task(description="分类以下请求，只输出类别词：{request}",
    expected_output="booking|info|unclear 之一", agent=classifier)

# 2. 模式接线：先分类，再按结果走外部条件分支路由到对应 Crew
decision = Crew(agents=[classifier], tasks=[classify_task]) \
    .kickoff(inputs={"request": "TODO(user): 用户请求"}).raw.strip()

if decision == "booking":
    # SAFETY: 交易类操作须人工确认后执行
    result = Crew(agents=[booking_agent], tasks=[Task(
        description="处理预订请求：{request}", expected_output="处理结果",
        agent=booking_agent)]).kickoff(inputs={"request": "TODO(user): 用户请求"})
else:
    result = "请补充说明您的需求。"  # 兜底分支

# 3. 执行入口见上
# 4. 观测与护栏：记录 decision 日志，便于审计路由准确率
```

## 6. 反模式与坑点

1. **无兜底分支** [F]：书中示例专门设 unclear 处理器处理无法委托的请求；缺少兜底会把不明确输入误分发给错误处理器。
2. **规则路由硬扛新颖输入** [F]：if-else 规则对复杂或新颖输入灵活性低，类目外请求会失效；此类场景应换 LLM 或嵌入路由。
3. **协调者越权直接作答** [F]：书中协调者指令明确「不要直接回答用户」；路由器混入处理职责会让委托结构退化为普通问答。
4. **路由器输出未约束、未校验** [E]：LLM 输出自由文本（如带解释的类别）会破坏分支匹配；应限定「只输出一个词」并对结果做白名单校验。
5. **过度路由** [E]：每个步骤都过一遍 LLM 路由会叠加延迟与成本；确定性强的分支应下沉为规则判断。

## 7. 与其他模式的组合

- **路由 + 提示链(01)** [F]：路由选定路径后进入专用提示链；路由也可挂在链中间决定后续动作，或在子流程中选择最合适的工具。
- **路由 + 多智能体(10)** [F]：协调者—子智能体委托模式（书中两套示例均模拟该架构，ADK 的 Auto-Flow 即其原生形态）。
- **路由 + RAG(06)** [E]：按嵌入相似度把查询语义路由到最相关的知识库或检索策略。
- **路由 + HITL(15)** [F]：复杂问题经路由升级到人工（书中技术支持分支的升级链）。
- **路由 + 异常恢复(14)** [E]：路由分支作为异常或降级路径的选择器，按错误类型分发恢复策略。

## 8. 评估指标

- **结果导向**：路由准确率（决策标签对照人工标注）；端到端任务完成率（请求被正确处理器解决的比例）。
- **过程导向**：误路由率；兜底分支触发率（过高说明类目体系或路由器设计不佳）；路由步骤的额外延迟与成本。
- **轨迹审查** [E]：核对决策标签先于处理器调用出现；兜底触发时是否发生了澄清交互而非直接失败。
