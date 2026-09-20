# 05 · 工具使用（Tool Use / 函数调用）

> 溯源：《智能体设计模式》第 5 章 工具使用（函数调用）· 板块：环境交互与知识
> 证据基准：本节内容除特别标注外，均为书中原文确认 [F]。

## 1. 模式定义

工具使用模式通常通过「函数调用」（Function Calling）机制实现，使智能体能够与外部 API、数据库、服务甚至执行代码进行交互。它允许智能体核心的 LLM 根据用户请求或任务当前状态，决定何时以及如何调用特定的外部函数。

该模式至关重要，因为它突破了 LLM 训练数据的限制——访问最新信息、执行内部无法完成的计算、操作用户专属数据或触发现实世界动作。**函数调用是连接 LLM 推理能力与丰富外部功能的技术桥梁** [F]。

概念辨析 [F]：「函数调用」准确描述了调用预定义代码函数的过程，但「工具调用」更具包容性——工具可以是复杂 API 接口、数据库请求，甚至面向其他智能体的指令。

## 2. 工作机制

典型流程六步 [F]：

```
1. 工具定义    向 LLM 描述外部函数：用途、名称、参数类型及说明
2. LLM 决策    LLM 接收请求 + 工具定义，判断是否需要调用（一个或多个）工具
3. 调用生成    LLM 输出结构化请求（通常 JSON）：工具名 + 从用户请求提取的参数
4. 工具执行    框架/编排层拦截结构化输出，用给定参数实际执行外部函数
5. 观察/结果   工具执行输出返回给智能体
6. LLM 处理    工具输出作为上下文，生成最终回复或决定下一步
              （可能再次调用工具、反思或直接答复）
```

LangChain、LangGraph、Google ADK 等框架均支持工具定义与集成，通常利用现代 LLM（Gemini、OpenAI 系列）的原生函数调用能力 [F]。

## 3. 适用场景与不适用场景

| 适用 ✅ | 不适用 ❌ |
|---|---|
| 外部信息检索：实时天气、新闻等训练数据之外的数据 | 纯文本生成任务：写作、总结、翻译 |
| 数据库/API 交互：查询库存、订单状态、支付 | 通用知识问答：LLM 训练数据已覆盖 |
| 计算与数据分析：计算器、统计工具、金融数据 | [E] 每次请求都恒定调用同一工具：直接硬编码调用更简单 |
| 发送通讯：邮件、消息服务 API | |
| 执行代码：沙箱中的代码解释器 | |
| 控制系统/设备：智能家居、物联网 | |

书中经验法则 [F]：只要智能体需要突破 LLM 内部知识、与外部世界交互（实时数据、私有信息、精确计算、代码执行、系统控制），就应采用工具使用模式。

## 4. 选型决策要点

1. **动态性判据**：需要的信息或操作是否随时间变化/超出训练数据？是 → 工具使用 [F]。
2. **与 RAG（06）的边界**：RAG 是工具使用的特化——检索知识库片段融入提示；通用工具调用覆盖更广的「动作」类操作 [E]。
3. **工具描述质量决定调用质量** [F]：需定义工具并清晰描述参数，docstring 即是给 LLM 的使用说明。
4. **执行主体区分** [F]：LLM 只「决定并生成调用请求」，实际执行者是智能体框架——安全控制点在执行层。
5. **与 MCP（11）的边界**：函数调用需用户/客户端手动执行；Vertex 扩展类 MCP 工具的优势是自动执行和企业集成 [F]。

## 5. 多框架代码模板

### 5.1 框架无关伪代码

```text
tools = define(
    search_information(query: str) -> str   # docstring: "检索外部信息"
    # SAFETY: 发送类工具须内置人工确认挂点
)
agent = Agent(llm, tools, instructions="按需选择工具，参数从用户请求提取")
loop:
    decision = llm(request, tool_descriptions)   # 结构化调用请求或直接答复
    if decision.is_tool_call:
        result = framework.execute(decision.tool, decision.args)  # 框架执行
        context.append(result)                   # 观察回填，进入下一轮
    else:
        return decision.answer
```

### 5.2 LangChain（源自书中第 5 章实码 [F]，改写为骨架）

```python
# LangChain（书中示例基于 gemini-2.0-flash；版本需核对最新文档）
# 1. 组件定义：@tool 装饰器，docstring 即工具说明
from langchain_core.tools import tool

@tool
def search_information(query: str) -> str:
    """根据查询检索外部信息，返回相关结果。"""  # LLM 依据此描述决策
    # TODO(user): 接真实检索源；书中用 simulated_results 字典模拟
    ...

# 2. 模式接线
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是信息助手，按需调用工具。"),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),  # 工具调用轨迹占位，必需
])
agent = create_tool_calling_agent(llm, [search_information], prompt)

# 3. 执行入口
executor = AgentExecutor(agent=agent, tools=[search_information], verbose=True)
result = await executor.ainvoke({"input": "某主题的最新进展"})

# 4. 观测与护栏：verbose=True 输出轨迹；发送类工具在函数内部加人工确认
```

### 5.3 Google ADK（源自书中第 5 章实码 [F]，改写为骨架）

```python
# Google ADK（书中示例：内置工具三例）
from google.adk.agents import LlmAgent, Agent
from google.adk.code_executors import BuiltInCodeExecutor

# 1. 组件定义 + 2. 模式接线：内置工具直接挂载
# a. Google 搜索
root_agent = Agent(name="search_assistant",
                   model="gemini-2.0-flash-exp",  # TODO(user): 按需换模型
                   instruction="回答问题前先用搜索核实。",
                   tools=[google_search])
# b. 代码执行（精确计算）
calculator = LlmAgent(name="calculator_agent",
                      code_executor=BuiltInCodeExecutor(),
                      instruction="收到数学表达式时编写并执行 Python 代码计算。")
# c. Vertex AI Search（企业知识，带 grounding_metadata 来源归因）
#    vsearch_agent = agents.VSearchAgent(name=..., datastore_id=DATASTORE_ID)

# 3. 执行入口：SessionService + Runner，遍历 events 取 is_final_response()
# 4. 观测与护栏：事件流区分 executable_code 与 code_execution_result，全程可审计
```

### 5.4 CrewAI（源自书中第 5 章实码 [F]，改写为骨架）

```python
# CrewAI（书中示例：金融分析师股票查询）
from crewai import Agent, Task, Crew
from crewai.tools import tool

# 1. 组件定义
@tool("股票价格查询工具")
def get_stock_price(ticker: str) -> float:
    """按股票代码查询当前价格。"""
    # TODO(user): 接真实行情 API；书中返回模拟价格
    ...

analyst = Agent(role='高级金融分析师',
                goal='基于最新行情提供分析。',
                backstory='资深金融专家，严谨核实数据。',
                tools=[get_stock_price],
                allow_delegation=False)

# 2. 模式接线：工具绑定在 Agent 上，任务描述触发调用
task = Task(description="查询指定股票价格并给出分析。",
            expected_output="价格数据与分析结论。", agent=analyst)

# 3. 执行入口
result = Crew(agents=[analyst], tasks=[task]).kickoff()
```

## 6. 反模式与坑点

1. **工具描述含糊** [F]：docstring 不写用途与参数含义，LLM 无法正确决策。工具定义质量直接决定调用质量。
2. **让 LLM 直接执行** [F]：LLM 只生成调用请求；误以为 LLM「执行」了工具而把安全控制放在提示层。执行层的框架拦截才是权限控制点。
3. **无错误处理的工具** [F]：工具可能失败、返回异常数据或超时，智能体需能识别错误并决定重试、换工具或求助（见第 14 章异常处理）。
4. **漏掉 agent_scratchpad** [E]：LangChain 工具智能体的提示模板缺 `("placeholder", "{agent_scratchpad}")` 会导致多轮工具调用失效。
5. **工具过多一锅端** [E]：可用工具全部塞给单个 LLM，选择准确率下降；书中层级结构做法是每个智能体管理相关工具组（见第 10 章）。

## 7. 与其他模式的组合

- **工具使用 + 规划（04）**：计划的每一步按需调用工具——Deep Research 核心形态 [F]。
- **工具使用 + RAG（06）**：RAG 是知识检索特化工具，语义搜索替代关键词匹配 [F]。
- **工具使用 + MCP（11）**：MCP 标准化工具/数据源连接，扩展类工具自动执行、企业集成 [F]。
- **工具使用 + HITL（15）+ 护栏（18）**：有现实影响或付费的工具使用前须人类确认 [F]。
- **工具使用 + 多智能体（10）**：层级结构中管理者按工具能力分配任务给工作智能体 [F]。

## 8. 评估指标

- **结果导向**：工具调用正确率（工具选择与参数提取是否正确）；任务完成率（借助工具达成目标的比率）。
- **过程导向**：调用轮次效率（达成目标所需的最少调用数 vs 实际）；错误调用后的恢复率（重试/换工具是否成功）。
- **轨迹审查**：检查调用参数是否忠实来自用户请求、有无编造参数（幻觉式调用）[E]。
