# 13 · 目标设定与监控（Goal Setting and Monitoring）

> 溯源：《智能体设计模式》第 11 章 目标设定与监控 · 板块：可靠性与工程化
> 证据基准：本节内容除特别标注外，均为书中原文确认 [F]。

## 1. 模式定义

目标设定与监控模式为智能体设定具体目标，并赋予其追踪进度、判断目标是否达成的能力，核心是给智能体嵌入「目标感」和自我评估机制。它要求目标明确、可衡量（SMART：具体/可衡量/可达成/相关/有时限），并建立持续监控机制，实时追踪智能体及环境状态，形成关键反馈回路，使智能体能够自我评估、纠偏和适应——将简单响应式智能体升级为主动、可靠的自主系统。

## 2. 工作机制

模式在「规划」之上补齐方向感与验收感 [F]：规划（04）解决从初始状态到目标状态的「怎么走」，目标监控提供「去哪里」的终点与「是否到达」的判定。

```
输入: 高层目标 + 约束（风险容忍度、截止日期等）
  ↓
[目标化] 将目标 SMART 化，明确指标与成功标准（质量检查表）
  ↓
[执行]   智能体执行任务（可结合规划/工具使用/多智能体协作）
  ↓
[监控]   持续观察三类对象：智能体行为、环境状态、工具输出
  ↓
[判定]   对照指标自评：达标 → 结束；未达标 → 纠偏、修订或
         调整策略；无法解决 → 升级人工处理
  ↓
输出: 可靠达成的结果 + 全程可审计的监控轨迹
```

书中实战形态为「生成-评估-达标判定」循环 [F]：AI 程序员接收用例与目标清单（如「简单易懂」「功能正确」「处理边界情况」），生成代码初稿后不立即提交，而是由评审者对照目标清单逐项批判；判定环节 LLM 仅返回 True/False 以便于决定停止迭代；False 则携带反馈进入修正，直到 True 或达到最大迭代次数。ADK 形态：目标通常通过智能体指令传递，监控则通过状态管理和工具交互实现。更健壮的形态是职责分离的多智能体团队（编程助手、代码评审员、文档员、测试编写员、提示优化师各自专职）。

## 3. 适用场景与不适用场景

| 适用 ✅ | 不适用 ❌ |
|---|---|
| 客户支持自动化：目标「解决账单问题」，监控对话与数据，未解决自动升级 [F] | 单步请求：一次行动或工具调用即可解决 [E] |
| 个性化学习系统：目标「提升学生理解」，跟踪准确率与完成时间，遇困调整策略 [F] | 无状态纯问答：无需进度追踪与达标判定 [E] |
| 项目管理助手：目标「里程碑按期完成」，监控任务与资源，延误主动预警 [F] | 无法定义可衡量成功标准的模糊任务：先人工澄清目标再上模式 [E] |
| 自动化交易：目标「风险容忍内最大化收益」，持续监控市场与风险指标 [F] | 路径与结果完全确定的流程：直接硬编码步骤链（01）[E] |
| 机器人与自动驾驶：目标「安全抵达」，实时监控环境与自身状态 [F] | |
| 内容审核：目标「识别有害内容」，跟踪误判率，疑难升级人工 [F] | |

## 4. 选型决策要点

1. **经验法则** [F]：当智能体需要自主执行多步任务、适应动态环境、并可靠达成高层目标且无需持续人工干预时，采用本模式。
2. **目标必须 SMART 化** [F]：具体、可衡量、可达成、相关且有时限；明确指标和成功标准是有效监控的关键——目标清单就是智能体的验收检查表。
3. **监控三对象齐全** [F]：监控包括观察智能体行为、环境状态和工具输出，缺一则判定失真。
4. **执行者与评审者分离** [F]：书中明确警示——当同一个 LLM 既负责写代码又负责评审时，发现自身偏离目标的能力有限；重要场景按角色拆分多智能体。
5. **循环必须有硬上限** [F]：书中示例自评「监控较基础，存在无限循环风险」，故设 `max_iterations=5`；上限之外还需升级路径（转人工），而非静默失败。

## 5. 多框架代码模板

### 5.1 框架无关伪代码

```text
goal = SMARTify(high_level_objective)     # 具体化指标与成功标准
loop until goal.achieved or deadline or max_iterations:
    action  = agent.step(goal, current_state)
    metrics = monitor.observe(agent_behavior, environment, tool_outputs)
    if metrics meets success_criteria:
        break                             # 达标判定成功
    else:
        adjust_plan(action.feedback)      # 纠偏、修订
        if not recoverable: escalate_to_human()   # 升级处理
```

### 5.2 LangChain / LangGraph（源自书中第 11 章实码 [F]，改写为骨架）

```python
# LangChain + OpenAI（书中第 11 章示例改写为骨架，需核对最新文档）
import os
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

_ = load_dotenv()
llm = ChatOpenAI(model="gpt-4o", temperature=0.3,
                 openai_api_key=os.getenv("OPENAI_API_KEY"))  # 密钥从环境变量读取

# 1. 组件定义：目标清单 + 评审者（get_code_feedback）+ 达标判定（goals_met）
def get_code_feedback(code, goals):     # 对照目标清单逐项批判给改进意见
    ...                                 # TODO(user): 按 review_prompt 实现

def goals_met(feedback_text, goals) -> bool:
    ...  # 监控核心：要求 LLM 仅回答 True/False，便于停止迭代
    ...  # TODO(user): 解析 llm.invoke(review_prompt).content

# 2. 模式接线：生成 → 评估 → 达标判定 → 修订 的监控循环
def run_code_agent(use_case, goals, max_iterations=5):
    for i in range(max_iterations):          # 硬上限防无限循环
        code = llm.invoke(generate_prompt(use_case, goals,
                                          previous_code, feedback))
        feedback = get_code_feedback(code, goals)
        if goals_met(feedback, goals):
            break                            # 目标达成，退出循环
        previous_code = code                 # 携反馈进入下一轮修订

# 3. 执行入口：run_code_agent(use_case, goals_input)
# 4. 观测与护栏：同 LLM 既写又评存在认知偏差，
#    生产场景改用独立评审智能体（书中多智能体团队建议）
```

### 5.3 Google ADK（本书该章未提供示例）

> 本书第 11 章未提供 ADK 示例；书中要点确认「目标通过智能体指令传递，监控通过状态管理和工具交互实现」[F]，以下代码为工程实践推断 [E]，需核对最新文档。

```python
# Google ADK（工程实践推断 [E]，需核对最新文档）
from google.adk.agents import LlmAgent

# 1. 组件定义：目标写入 instruction，进度指标写入 session state
agent = LlmAgent(
    name="my_agent",
    instruction="""目标：TODO(user): SMART 化的任务目标。
    每步执行后调用 check_goal 核对进度指标，
    指标越界时停止执行并请求人工介入。""")

def check_goal(tool_context) -> dict:   # 2. 模式接线：工具内读 state 判进度
    progress = tool_context.state.get("progress", 0)
    return {"achieved": progress >= 0.9, "progress": progress}

# 3. 执行入口：Runner 驱动；output_key / state_delta 更新监控指标
# 4. 观测与护栏：state 留存全程监控轨迹（见 08 记忆管理）
# SAFETY: 达标判定连续失败 N 次必须升级人工，不得无限重试
```

### 5.4 CrewAI（本书该章未提供示例）

> 本书第 11 章未提供 CrewAI 示例（仅提及用多智能体团队分工实现更客观的评审），以下为工程实践推断 [E]，需核对最新文档。

```python
# CrewAI（工程实践推断 [E]，需核对最新文档）
# 1. 组件定义：执行者与监控者分角色（缓解同体自评偏差）
executor = Agent(role="执行者", goal="按计划完成任务", ...)
monitor  = Agent(role="监控者", goal="对照目标清单评估产出，只回答达标/未达标", ...)

# 2. 模式接线：执行 → 监控 → 反馈修订循环
work   = Task(description="执行任务并输出结果", agent=executor)
check  = Task(description="对照目标清单逐项评估", agent=monitor, context=[work])
revise = Task(description="按监控反馈修订", agent=executor, context=[check])

# 3. 执行入口
Crew(agents=[executor, monitor], tasks=[work, check, revise]).kickoff()
# 4. 观测与护栏：check 任务输出即为达标判定记录，留档可审计
```

## 6. 反模式与坑点

1. **模糊目标直接上线** [F]：无可衡量成功标准，智能体无法判断是否达成，只能被动响应；必须先 SMART 化并给出指标。
2. **幻觉式达标判定** [F]：书中注意事项——LLM 可能无法完全理解目标含义、错误判断已达成，即使目标明确也可能幻觉；判定提示应收敛为 True/False 单词输出，并保留人工抽查。
3. **同体自评** [F]：同一 LLM 既写又评，发现自身偏离目标的能力有限；用角色分离的多智能体（评审员与编程助手分开）使评审更客观。
4. **无上限监控循环** [F]：书中自认该示例监控较基础、存在无限循环风险；必须设最大迭代次数，且超限走升级路径而非继续烧 Token。
5. **监控对象缺角** [E]：只监控工具输出而忽略环境状态（如市场变化、用户情绪），或只看行为不看结果指标——三对象（行为/环境/工具输出）缺一即判定失真。

## 7. 与其他模式的组合

- **目标监控 + 规划（04）** [F]：规划生成从初始状态到目标状态的步骤序列，目标监控提供目标状态的定义与「是否抵达」的验收判定——书中旅行类比：确定去哪里（目标）、规划逐步推进（订票/出发/抵达）。
- **目标监控 + 反思（07）** [F]：评审者的逐项批判即反思机制，判定未达标时触发修订，形成生成-评估-改进闭环。
- **目标监控 + 记忆管理（08）** [E]：监控指标与进度存于 State / 长期记忆，支撑跨会话的目标追踪与回溯审计。
- **目标监控 + 多智能体（10）** [F]：编程助手、评审员、文档员、测试编写员、提示优化师分角色的多智能体团队，评审与执行分离更客观。
- **目标监控 + 异常恢复（14）** [E]：纠偏无效且不可恢复时转入异常处理与受控失败流程。
- **目标监控 + HITL（15）** [F]：疑难案例自动升级人工（内容审核、客户支持升级处理），达标判定存疑时转人工复核。

## 8. 评估指标

- **结果导向**：目标达成率（含在迭代上限内达成的比例——纯靠上限截断的「达成」不算）；达标判定准确性（人工复核 LLM True/False 判定的误判率）。
- **过程导向**：平均迭代轮次（趋近上限说明目标过难或评审过苛）；纠偏触发次数与纠偏有效率；升级人工的比例与升级后解决率。
- **轨迹审查** [E]：每轮修订是否真实针对反馈改进（而非整篇重写）；监控数据是否覆盖行为、环境、工具输出三对象；判定依据是否留档可审计。
