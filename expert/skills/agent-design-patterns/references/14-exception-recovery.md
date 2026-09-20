# 14 · 异常处理与恢复（Exception Handling and Recovery）

> 溯源：《智能体设计模式》第 12 章 异常处理与恢复 · 板块：可靠性与工程化
> 证据基准：本节内容除特别标注外，均为书中原文确认 [F]。

## 1. 模式定义

异常处理与恢复模式让智能体在多样化的真实世界环境中可靠运行：具备应对突发状况、错误和故障的能力，能检测问题、启动恢复流程，或至少确保受控失败 [F]。正如人类会适应意外障碍，智能体也需要健全的系统来应对异常——这是其在复杂、不可预测环境中成功运行，并提升整体效能与可信度的基础。

该模式专注于打造坚韧而有弹性的智能体，强调**主动预防与被动应对策略并重**，使其在遇到挑战时仍能保持不间断的功能与运行完整性 [F]。实施该模式可将智能体从脆弱不可靠的系统转变为坚实可靠的组件，保证功能持续、最大限度减少停机时间，并在遇到意外问题时为用户提供流畅可靠的体验 [F]。

## 2. 工作机制

三阶段闭环：**错误检测 → 错误处理 → 恢复** [F]。

```text
[错误检测] 工具输出无效/格式错误 · API 404/500 等特定错误码 · 响应时间异常延长
           · 响应内容不符预期格式 · 其他智能体或专用监控系统的主动异常检测
    ↓
[错误处理] 日志记录（供调试分析）→ 重试（参数略调整，应对临时性错误）
           → 备用方案（替代策略/方法，维持部分功能）→ 优雅降级（无法立即恢复时
           保持部分功能，为用户提供一定价值）→ 通知（向人工操作员或其他智能体告警）
    ↓
[恢复]     状态回滚（撤销最近更改/事务）→ 诊断（调查根因，防止再发）
           → 自我修正/重新规划（调整计划、逻辑或参数）→ 升级处理（转人工或更高层系统）
    ↓
回到稳定运行状态
```

两个要点：

- **受控失败优先** [F]：无法立即恢复时保持部分功能、至少为用户提供一定价值，而非彻底崩溃。
- **与反思结合** [F]：初次尝试失败并抛出异常后，可通过反思过程分析失败原因，并以改进的方式（如优化提示词）重新尝试——与反思模式（07）天然互补。

## 3. 适用场景与不适用场景

| 适用 ✅ | 不适用 ❌ |
|---|---|
| 客服聊天机器人：数据库暂不可用时检测 API 错误、告知用户、升级人工 [F] | [E] 封闭可控环境（离线演示/一次性脚本）：故障源少，实现成本大于收益 |
| 自动化金融交易：资金不足/市场关闭时记日志、不重复无效交易、通知调整 [F] | [E] 简单确定性流水线：传统 try/except 已足够，无需智能体级恢复 |
| 智能家居自动化：设备故障时重试→仍失败则通知并建议手动操作 [F] | [E] 失败无代价且可整体重跑的批处理：直接重跑更简单 |
| 数据处理智能体：批任务遇损坏文件跳过并记录，最终报告跳过清单 [F] | |
| 网页爬虫：验证码/结构变化/404/503 优雅处理，报告失败的具体 URL [F] | |
| 机器人与制造业：传感器反馈检测拾取失败→调整重试→升级人工 [F] | |

书中经验法则 [F]：**只要智能体部署在动态真实环境，存在系统故障、工具错误、网络异常或不可预测输入，且运行可靠性是关键要求时，都应采用该模式。**

## 4. 选型决策要点

1. **可靠性是否为关键要求** [F]：动态真实环境 + 存在故障源 + 可靠性关键 → 必用本模式（书中经验法则）。
2. **处理策略的优先级链** [F]：检测到错误后——日志记录（必做，供后续调试分析）→ 重试（仅临时性错误，参数略作调整）→ 备用方案（替代策略或方法）→ 优雅降级（保持部分功能）→ 通知（人工操作员或其他智能体）。
3. **恢复手段按严重度升级** [F]：轻则自我修正/重新规划（调整计划、逻辑或参数），重则状态回滚（撤销最近更改或事务），最严重时升级至人工操作员或更高层系统。
4. **与反思（07）的边界** [F]：异常处理负责检测与恢复运行状态；反思负责分析失败原因并改进重试方式。书中明确二者结合使用——失败→反思归因→优化提示词重试。
5. **与 HITL（15）的衔接** [E]：升级处理本质是转向人工的受控通道；高风险操作的失败应默认升级，而非让智能体反复自主重试。

## 5. 多框架代码模板

### 5.1 框架无关伪代码

```text
try:
    result = primary_tool.call(args)          # 主路径：精确工具
    validate(result)                          # 检测：输出格式 / 错误码 / 超时校验
except ToolError as e:
    log(e)                                    # 处理 1：日志记录
    if e.is_transient and retry_count < MAX:
        result = primary_tool.call(adjust(args))   # 处理 2：参数微调后重试
    else:
        result = fallback_tool.call(coarse(args))  # 处理 3：备用方案（粗粒度替代）
        state.mark("primary_failed")               # 状态标记，供后续环节判断
finally:
    if not result:
        notify_human_or_agent(failure_detail) # 处理 4：通知；必要时回滚/升级（恢复）
```

### 5.2 LangGraph（书中第 12 章未提供，以下为工程实践推断 [E]）

```python
# LangGraph（示例性质，需核对最新文档）
# 1. 组件定义：主节点 + 备用节点 + 汇总节点
from langgraph.graph import StateGraph, END

def primary(state):    # 主路径：精确工具调用，异常时置失败标记
    ...                # TODO(user): try/except 包裹工具调用并写结构化日志
def fallback(state):   # 备用路径：仅当 primary_failed 时执行粗粒度查询
    ...
def respond(state):    # 汇总：有结果则展示，无结果则致歉说明
    ...

# 2. 模式接线：主节点失败 → 备用节点 → 汇总；成功 → 直接汇总
graph = StateGraph(dict)
graph.add_node("primary", primary)
graph.add_node("fallback", fallback)
graph.add_node("respond", respond)
graph.set_entry_point("primary")
graph.add_conditional_edges(
    "primary", lambda s: "fallback" if s.get("primary_failed") else "respond")
graph.add_edge("fallback", "respond")
graph.add_edge("respond", END)

# 3. 执行入口
app = graph.compile()
result = app.invoke({"query": "某地址的位置信息"})  # TODO(user): 替换实际查询

# 4. 观测与护栏：重试次数上限防死循环；失败沿状态字段如实传递
```

### 5.3 Google ADK（源自书中第 12 章实码 [F]，改写为骨架）

```python
# google-adk（示例性质，需核对最新文档）
# 1. 组件定义：三个子智能体——主处理器 / 备用处理器 / 结果输出
from google.adk.agents import Agent, SequentialAgent

primary_handler = Agent(
    name="primary_handler", model="gemini-2.0-flash-exp",  # TODO(user): 按需换模型
    instruction="""你的任务是获取精确的位置信息。
    请使用 get_precise_location_info 工具，并传入用户提供的地址。""",
    tools=[get_precise_location_info],   # TODO(user): 替换为实际工具
)

fallback_handler = Agent(
    name="fallback_handler", model="gemini-2.0-flash-exp",
    instruction="""检查 state["primary_location_failed"] 是否为 True。
    - 若为 True，从用户原始查询中提取城市，并使用 get_general_area_info 工具。
    - 若为 False，无需操作。""",
    tools=[get_general_area_info],
)

response_agent = Agent(
    name="response_agent", model="gemini-2.0-flash-exp",
    instruction="""查看 state["location_result"] 中的位置信息并清晰简明地展示。
    若不存在或为空，请向用户致歉，说明无法获取位置信息。""",
    tools=[],
)

# 2. 模式接线：SequentialAgent 保证「主→备用→输出」顺序执行，实现分层降级
robust_location_agent = SequentialAgent(
    name="robust_location_agent",
    sub_agents=[primary_handler, fallback_handler, response_agent],
)
# 3. 执行入口：经 Runner/会话调用 robust_location_agent
# 4. 观测与护栏：失败状态经 session state 传递；无结果时诚实致歉而非编造
```

### 5.4 CrewAI（书中第 12 章未提供，以下为工程实践推断 [E]）

```python
# CrewAI（示例性质，需核对最新文档）
# 1. 组件定义：主任务智能体 + 备用任务智能体
from crewai import Agent, Task, Crew, Process

primary_agent = Agent(role="主查询员", goal="用精确工具获取目标信息",
                      backstory="工具失败时如实上报，绝不编造结果。",
                      llm=my_llm)                       # TODO(user): 指定模型
fallback_agent = Agent(role="备用查询员", goal="以粗粒度方式获取可用的近似信息",
                       backstory="仅在主路径失败时介入。", llm=my_llm)

# 2. 模式接线：任务描述中显式内建「失败→备用」处理路径（激发手法同 04 规划）
primary_task = Task(description="调用精确工具查询目标信息；若失败，在输出中标记 FAILED。",
                    expected_output="查询结果或 FAILED 标记", agent=primary_agent)
fallback_task = Task(description="若上一任务输出含 FAILED，改用备用数据源获取近似结果。",
                     expected_output="近似结果或明确的失败报告", agent=fallback_agent)

# 3. 执行入口：顺序流程，失败沿任务链传递
crew = Crew(agents=[primary_agent, fallback_agent],
            tasks=[primary_task, fallback_task], process=Process.sequential)
result = crew.kickoff()

# 4. 观测与护栏：检查执行轨迹中失败是否被如实记录与传递
```

## 6. 反模式与坑点

1. **重复尝试已知无效的操作** [F]：交易机器人遇「资金不足/市场关闭」应记日志、停止重试并及时通知，而非反复撞墙。
2. **一处失败中断全局** [F]：批处理遇损坏文件应跳过并记录、继续处理其余文件、最后统一报告跳过清单，而不是中断整个流程。
3. **闭环缺环** [F]：完整闭环是检测→处理（日志/重试/备用/降级/通知）→恢复（回滚/诊断/自我修正/升级）；只检测不处理、或只处理不恢复都会留下脆弱点。
4. **[E] 吞错误不留痕**：捕获异常却不记日志，后续无法调试与根因分析——日志记录是书中处理策略的第一项，必做。
5. **[E] 失败时编造结果**：获取不到信息时应诚实致歉说明（书中 response_agent 的做法），不能让模型脑补填补空缺，否则会悄然破坏系统可信度。
6. **[E] 降级无边界**：优雅降级须明确「降级后仍保证什么」，并向用户说明结果精度下降，避免用户误信粗粒度输出。

## 7. 与其他模式的组合

- **异常恢复 + 反思（07）**：失败后经反思分析原因、以改进方式（如优化提示词）重试——书中明确给出的组合 [F]。
- **异常恢复 + 工具使用（05）**：工具调用失败是最常见故障源；ADK 实战示例即「主工具失败→备用工具」的分层降级 [F]。
- **异常恢复 + HITL（15）**：升级处理把复杂或严重问题转交人工操作员，构成人机协作安全网 [F]。
- **异常恢复 + 多智能体（10）**：通知机制可向其他智能体发出警报，便于人工干预或协作接手 [F]。
- **异常恢复 + 目标监控（13）**：专用监控系统主动异常检测，提前捕捉潜在问题、防止事态扩大 [E]。
- **异常恢复 + 规划（04）**：恢复中的自我修正常以「重新规划」形式落地 [F]。
- **异常恢复 + 学习适应（09）** [E]：诊断结果沉淀为经验（记忆/策略更新），避免同类错误重复发生。

## 8. 评估指标

- **结果导向**：任务最终成功率（含经重试/备用方案后恢复成功的比例）；停机时间；用户可见失败率 [E]。
- **过程导向**：错误检出率与误报率；重试成功率（重试后恢复的比例）；恢复耗时（从检出到回到稳定状态）；升级率（升级人工占比——过高说明自主恢复能力不足）[E]。
- **韧性审查** [E]：故障注入演练下系统是否保持运行完整性；轨迹检查失败是否被如实记录与传递，而非被掩盖。
- **书中口径** [F]：评估应围绕三个承诺展开——功能持续、停机时间最小化、意外问题时用户体验流畅可靠。
