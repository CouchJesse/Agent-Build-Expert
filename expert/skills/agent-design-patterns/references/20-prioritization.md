# 20 · 优先级排序（Prioritization）

> 溯源：《智能体设计模式》第 20 章 优先级排序 · 板块：可靠性与工程化
> 证据基准：本节内容除特别标注外，均为书中原文确认 [F]。

## 1. 模式定义

在复杂且动态的环境中，智能体常面临大量潜在行动、目标冲突和资源有限的问题；若没有明确的后续行动决策流程，智能体可能效率低下、操作延迟，甚至无法实现关键目标 [F]。优先级排序模式通过让智能体根据任务的重要性、紧急性、依赖关系和既定标准进行评估和排序来解决这一问题，确保智能体将精力集中在最关键的任务上，提升整体效能和目标达成度 [F]。

## 2. 工作机制

模式包含四个核心要素 [F]：

```
输入: 待办任务集合 + 环境状态
  ↓
[标准定义] 建立评估规则：紧急性 / 重要性 / 依赖关系 /
           资源可用性 / 成本收益分析 / 用户偏好
  ↓
[任务评估] 按标准分析每个潜在任务——
           方法从简单规则到评分体系或 LLM 推理
  ↓
[调度选择] 依评估结果选出最佳下一步行动或任务顺序
           （队列或高级规划组件）
  ↓
[动态调整] 环境变化（新关键事件出现 / 截止时间临近）→
           修改任务优先级，保持适应性与响应能力
  ↓
输出: 有序的执行队列 / 下一步行动决策
```

优先级排序发生在多个层级 [F]：**选择总体目标**（高层级目标排序）、**规划步骤排序**（子任务排序）、**从可选项中选择下一步行动**（行动选择）。这类似人类团队管理者根据成员意见对任务排序——智能体据此在多目标环境下表现得更智能、高效、稳健。

## 3. 适用场景与不适用场景

| 适用 ✅ | 不适用 ❌ |
|---|---|
| 自动化客户支持：系统故障等紧急请求优先，密码重置等常规延后；高价值客户优先响应 [F] | 任务单一固定的线性流程：无多任务竞争，直接顺序执行（提示链 01） [E] |
| 云计算资源调度：高峰时段优先分配资源给关键应用，低优先级批处理移至非峰期优化成本 [F] | 无资源约束与时间压力的场景：排序无收益 [E] |
| 自动驾驶：安全优先——避撞制动优先于保持车道或优化油耗 [F] | 优先级已由固定安全规则硬编码的强确定性控制 [E] |
| 金融交易：按市场状况、风险容忍度、利润率与实时新闻优先执行高优先级交易 [F] | |
| 网络安全：按威胁严重性、潜在影响与资产关键性处理告警 [F] | |
| 项目管理 / 个人助理：按截止日期、依赖关系、团队可用性、用户偏好排程 [F] | |

## 4. 选型决策要点

1. **书中经验法则** [F]：智能体系统需在资源受限、任务或目标冲突的动态环境下自主管理多项任务时，应采用优先级排序模式。
2. **标准必须显式定义** [F]：紧急性、重要性、依赖关系、资源可用性、成本收益分析、用户偏好是六类基础标准；标准缺失时「排序」退化为任意顺序。
3. **评估方法按复杂度选型** [F]：从简单规则到评分体系再到 LLM 推理——语义模糊的请求（如「很紧急」）需要 LLM 推理映射为优先级。
4. **与规划（04）的边界** [E]：规划决定「步骤怎么拆」，优先级排序决定「先做哪个」；两者在「规划步骤排序」层级交汇——规划产出子任务后由本模式定序。
5. **动态调整是必备能力** [F]：新关键事件出现或临近截止时间时必须能重排，静态优先级在动态环境下必然失效；信息缺失时按合理默认分配（如书中示例默认 P1）并显式说明，避免排序悬空。

## 5. 多框架代码模板

### 5.1 框架无关伪代码

```text
priority_agent = Agent(
    tools = [create_task, assign_priority, assign_worker, list_tasks],
    instructions = """
      收到任务请求后：
      1. CREATE     创建任务并获取 task_id
      2. EVALUATE   按标准评估：紧急性 / 重要性 / 依赖关系 /
                    资源可用性 / 成本收益 / 用户偏好
      3. PRIORITIZE 映射为 P0（最高）/ P1（中）/ P2（最低）；
                    信息缺失时按默认值分配（如 P1）并显式说明
      4. SCHEDULE   形成执行队列；环境变化（新关键事件 /
                    截止时间临近）时重新评估并调整排序
    """
)
```

### 5.2 LangChain（书中第 20 章实码 [F]，改写为骨架）

```python
# LangChain（版本需核对最新文档）— 项目经理智能体示例
import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_react_agent

load_dotenv()  # ChatOpenAI 自动读取环境变量中的 API key
llm = ChatOpenAI(temperature=0.5, model="gpt-4o-mini")  # TODO(user): 按需更换模型

# 1. 组件定义：任务模型 + 内存任务管理器（字典实现 O(1) 查找）
class Task(BaseModel):
    id: str
    description: str
    priority: str | None = None      # P0 / P1 / P2
    assigned_to: str | None = None

class SimpleTaskManager:
    def create_task(self, description: str) -> Task: ...
    def update_task(self, task_id: str, **kwargs) -> Task | None: ...
    def list_all_tasks(self) -> str: ...
    # TODO(user): 生产环境替换为持久化存储

task_manager = SimpleTaskManager()

# 2. 模式接线：工具封装任务操作，参数用 Pydantic 模型校验
class CreateTaskArgs(BaseModel):
    description: str = Field(description="任务的详细描述。")
class PriorityArgs(BaseModel):
    task_id: str = Field(description="任务 ID，如 'TASK-001'。")
    priority: str = Field(description="优先级：'P0'、'P1' 或 'P2'。")
class AssignWorkerArgs(BaseModel):
    task_id: str = Field(description="任务 ID，如 'TASK-001'。")
    worker_name: str = Field(description="分配的工作人员姓名。")

def assign_priority_tool(task_id: str, priority: str) -> str:
    if priority not in ["P0", "P1", "P2"]:
        return "优先级无效，必须为 P0、P1 或 P2。"
    task = task_manager.update_task(task_id, priority=priority)
    return f"已为任务 {task.id} 分配优先级 {priority}。"

tools = [
    Tool(name="create_new_task", func=task_manager.create_task,
         description="创建新任务并获取任务 ID", args_schema=CreateTaskArgs),
    Tool(name="assign_priority_to_task", func=assign_priority_tool,
         description="任务创建后分配优先级", args_schema=PriorityArgs),
    Tool(name="assign_task_to_worker", func=...,  # TODO(user): 同上模式封装分配逻辑
         description="任务创建后分配给人员", args_schema=AssignWorkerArgs),
    Tool(name="list_all_tasks", func=task_manager.list_all_tasks,
         description="列出所有当前任务及状态"),
]

prompt = ChatPromptTemplate.from_messages([
    ("system", """你是一名项目经理智能体。收到任务请求时：
      1. 先用 create_new_task 创建任务获取 task_id；
      2. 请求含「紧急 / ASAP / 关键」等信号 → 映射为 P0，
         用 assign_priority_to_task 分配；
      3. 信息（优先级 / 人员）缺失时按合理默认分配（优先级 P1）
         并显式说明；提及人员则用 assign_task_to_worker；
      4. 处理完毕后用 list_all_tasks 展示最终状态。"""),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

# 3. 执行入口
executor = AgentExecutor(
    agent=create_react_agent(llm, tools, prompt),
    tools=tools, verbose=True, handle_parsing_errors=True)

# 4. 观测与护栏：verbose=True 输出决策轨迹，
#    审计优先级判定是否与请求中的紧急信号一致
```

### 5.3 Google ADK（本书未提供该框架示例，以下为工程实践推断 [E]）

```python
# google-adk（版本需核对最新文档）
# 1. 组件定义：排序智能体，显式声明评估标准
from google.adk.agents import LlmAgent

priority_agent = LlmAgent(
    name="my_priority_agent",
    instruction="""评估任务时依次考虑：紧急性、重要性、依赖关系、
      资源可用性、成本收益；映射为 P0/P1/P2 并说明理由；
      信息缺失时按默认值（P1）分配并告知用户；
      收到新关键事件时主动重新评估队列中任务的优先级。""",
    # tools=[create_task, assign_priority, ...]  # TODO(user): 按 ADK 工具规范接入
)

# 2. 模式接线：任务队列存入 Session State，供后续动态重排
# 3. 执行入口：runner 逐会话推进
# 4. 观测与护栏：优先级变更记录入 State，形成可审计的调整轨迹
```

### 5.4 CrewAI（本书未提供该框架示例，以下为工程实践推断 [E]）

```python
# CrewAI（版本需核对最新文档）
import os
from crewai import Agent, Task, Crew, Process

# 1. 组件定义：排序协调员（密钥从环境变量读取，模型按需指定）
coordinator = Agent(
    role="任务排序协调员",
    goal="按紧急性/重要性/依赖关系对任务排序并给出执行顺序",
    backstory="你擅长在资源受限时做取舍。",
    llm=llm,  # TODO(user): 指定模型，密钥从环境变量读取
)

# 2. 模式接线：任务描述要求输出带优先级的执行顺序与理由
rank_task = Task(
    description="对以下任务列表评估并排序，输出 P0/P1/P2 与执行顺序：{task_list}",
    expected_output="按优先级排序的任务列表及排序理由",
    agent=coordinator)

# 3. 执行入口
crew = Crew(agents=[coordinator], tasks=[rank_task],
            process=Process.sequential)
# 4. 观测与护栏：排序理由随输出留存，供人工复核标准运用是否恰当
```

## 6. 反模式与坑点

1. **静态优先级** [F]：排序后一成不变。动态环境（新关键事件、截止时间临近）下必须重排——动态调整是本模式的核心要素，不是可选增强。
2. **标准含糊或过载** [E]：评估维度过多且无权重时，LLM 评估结果不稳定；应明确六类标准的优先次序，或先以少量标准起步再逐步扩展。
3. **模糊请求静默处理** [F]：书中示例要求智能体理解模糊请求（「很紧急」→ P0），但信息缺失时的默认分配（如 P1）必须显式说明，避免静默降级引发用户预期错位。
4. **低优先级饥饿** [E]：高优任务持续涌入时 P2 任务可能无限延后；应设最大等待时限或定期复核陈旧任务的优先级。
5. **把优先级当硬编码规则** [F]：固定 if-else 式排序无法适应语义化请求；书中用 LLM + 工具组合而非规则脚本，正是智能体系统与普通自动化脚本的本质区别——智能体能理解模糊请求、自主选择工具、合理安排行动顺序。

## 7. 与其他模式的组合

- **优先级（20）+ 规划（04）**：规划拆解出的子任务经优先级排序决定执行顺序——「规划步骤排序」层级即两者的交汇点 [F]。
- **优先级（20）+ 目标监控（13）**：监控发现目标偏离或新关键事件时触发优先级重排，保持行为与目标对齐 [E]。
- **优先级（20）+ 资源优化（16）**：任务分级是资源分配的输入——关键任务走高阶模型与更多算力，次要任务走经济路径 [E]。
- **优先级（20）+ 异常恢复（14）**：异常事件天然携带高紧急性，恢复流程应插队执行 [E]。
- **优先级（20）+ 并行化（03）**：无依赖关系的高优任务可并行执行；依赖关系本身也是排序标准之一 [E]。
- **优先级（20）+ HITL（15）**：高风险任务的优先级提升（如升至 P0）可挂人工确认挂点，防止误判引发资源挤占 [E]。

## 8. 评估指标

- **结果导向**：关键任务完成率（P0 任务按时完成比例）；目标达成度（资源投向与战略目标的一致性）[E]。
- **过程导向**：优先级判定准确率（请求中的紧急信号与分配级别的一致性）；重排响应时间（新关键事件出现到队列更新的延迟）；饥饿任务占比（超时未执行的低优任务比例）[E]。
- **轨迹审查**：检查排序决策是否依据显式标准（轨迹中可见评估依据而非任意排序）；信息缺失时是否按默认规则处理并向用户说明 [E]。
