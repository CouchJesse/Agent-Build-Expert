# 07 · 反思（Reflection）

> 溯源：《智能体设计模式》第 4 章 反思 · 板块：状态与自我提升
> 证据基准：本节内容除特别标注外，均为书中原文确认 [F]。

## 1. 模式定义

反思模式指智能体对自身的工作、输出或内部状态进行评估，并利用评估结果来提升性能或优化响应。这是一种**自我纠错或自我改进机制**，使智能体能够根据反馈、内部批判或与目标标准的对比，反复优化输出或调整策略。反思也可以由专门负责分析初始智能体输出的独立智能体实现。

与简单的链式传递或路径选择不同，反思引入了**反馈循环**：智能体不仅生成输出，还会审视该输出（或生成过程），识别潜在问题或改进空间，并据此生成更优版本。

## 2. 工作机制

典型流程四步 [F]：

```
1. 执行        智能体完成任务或生成初始输出
2. 评估/批判   （另一次 LLM 调用或规则集）检查事实准确性、连贯性、
             风格、完整性、是否遵循指令
3. 反思/优化   据批判结果改进：优化输出、调整参数、甚至修改整体计划
4. 迭代（可选） 重复 1–3，直到满意或满足终止条件
```

**生产者-批评者双角色模型** [F]：生产者智能体负责任务初步执行与内容生成；批评者智能体以不同角色设定（如「资深软件工程师」「严谨的事实核查员」）按特定标准给出结构化反馈。**这种分工能有效避免智能体自我评审时的「认知偏差」**——批评者以全新视角专注于发现错误和改进空间。

实现要求 [F]：需在工作流中引入反馈循环——单步评估优化可在 LangChain（LCEL）实现；**真正的迭代反思需要支持状态管理和条件跳转的框架**（如 LangGraph 的循环图、ADK 的 LoopAgent）。

与记忆的关系 [F]：「没有记忆时，每次反思都是独立事件；有记忆时，反思成为累积过程，每轮迭代都在前一轮基础上进步。」（见第 08 章）

## 3. 适用场景与不适用场景

| 适用 ✅ | 不适用 ❌ |
|---|---|
| 创意写作与内容生成：初稿→批判→重写循环 | 实时/低延迟场景：反思增加轮次与时延 |
| 代码生成与调试：测试/静态分析发现问题后修改 | 简单确定性任务：输出质量不依赖迭代 |
| 复杂问题求解：评估中间步骤，有问题则回溯 | [E] 成本敏感的高频调用：每轮反思翻倍 Token 成本 |
| 摘要与信息整合：初步摘要对照原文关键点优化 | |
| 规划与策略制定：模拟执行/约束评估后修订 | |
| 对话智能体：回顾对话历史纠正误解 | |

书中经验法则 [F]：**当最终输出的质量、准确性和细节比速度和成本更重要时，优先采用反思模式。**

## 4. 选型决策要点

1. **质量 vs 速度权衡** [F]：反思以延迟和计算成本为代价换取质量；需权衡上下文窗口溢出与 API 限流风险。
2. **自我反思 vs 独立批评者** [F]：简单错误捕捉用「检查你的工作」式自我反思；严格标准评审用独立批评者智能体（避免认知偏差）。
3. **终止条件必备** [E]：必须设置最大迭代次数与「完美即停」信号（如书中 `CODE_IS_PERFECT` 哨兵），否则循环失控烧 Token。
4. **与记忆联动** [F]：跨轮任务配备记忆（08）后，反思从独立事件变为累积改进。
5. **与目标监控（13）联动** [F]：目标提供自我评估的最终标准，监控跟踪改进进展。

## 5. 多框架代码模板

### 5.1 框架无关伪代码

```text
producer = Agent(role="执行者", goal="生成初始输出")
critic   = Agent(role="批评者", goal="按标准评估输出",
                 stop_signal="OUTPUT_IS_PERFECT")
for i in range(max_iterations):
    output = i == 0 ? producer.execute(task)
                    : producer.revise(task, output, critique)
    critique = critic.evaluate(output)     # 结构化改进意见（项目符号列表）
    if stop_signal in critique: break
return output
```

### 5.2 LangChain（源自书中第 4 章实码 [F]，改写为骨架）

```python
# LangChain / LCEL（书中示例：GPT-4o, temperature=0.1，迭代优化 Python 函数）
from langchain_core.messages import SystemMessage, HumanMessage

def run_reflection_loop(task_prompt, max_iterations=3):
    history = [SystemMessage("你是代码生成专家"),
               HumanMessage(task_prompt)]
    for i in range(max_iterations):
        # 执行：首轮生成，后续轮按批判意见优化
        output = llm.invoke(history)
        history.append(AssistantMessage(output))

        # 评估：批评者以独立提示审查（角色隔离避免认知偏差）
        critique = llm.invoke([
            SystemMessage("你是一名资深软件工程师。审查代码的"
                "正确性与健壮性。若代码完美且满足所有要求，"
                "仅回复 'CODE_IS_PERFECT'；否则以项目符号列表给出批判意见。"),
            HumanMessage(f"{task_prompt}\n\n待审查代码：\n{output}")])

        # 终止条件：哨兵信号
        if "CODE_IS_PERFECT" in critique.content:
            break
        history.append(HumanMessage("请根据批判意见优化代码。"))
    return output
# 观测与护栏：全程维护对话历史（verbose），迭代轮次受 max_iterations 硬约束
```

### 5.3 Google ADK（源自书中第 4 章实码 [F]，改写为骨架）

```python
# Google ADK（书中示例：生成者-批评者顺序管道）
from google.adk.agents import SequentialAgent, LlmAgent

# 1. 组件定义：双角色，经 session state 传递数据
generator = LlmAgent(
    name="DraftWriter",
    instruction="写一段简短、信息丰富的主题段落。",
    output_key="draft_text")          # 输出写入 state['draft_text']

reviewer = LlmAgent(
    name="FactChecker",
    instruction=("阅读 state['draft_text']，核查事实。输出含两键的字典："
                 "status: ACCURATE/INACCURATE, reasoning: 理由。"),
    output_key="review_output")       # 评审结果写入 state['review_output']

# 2. 模式接线：SequentialAgent 顺序执行 generator → reviewer
pipeline = SequentialAgent(name="WriteAndReview_Pipeline",
                           sub_agents=[generator, reviewer])
# 3. 执行入口：Runner 驱动；4. 观测：state 中全程留痕
# 进阶：LoopAgent 可实现多轮迭代反思（直至达标）
```

### 5.4 CrewAI（书中未提供该框架专码）

> 本书第 4 章未提供 CrewAI 反思专码。CrewAI 可用「批评-审查者」双 Agent 顺序任务（作者 Agent 产初稿、审查 Agent 评审、作者 Agent 再修订）实现，为工程实践推断 [E]，需核对最新文档。

```python
# CrewAI（工程实践推断 [E]）
writer  = Agent(role='写作者', goal='按计划产出初稿', ...)
critic  = Agent(role='事实核查员', goal='核查草稿并给出改进清单', ...)
draft = Task(description="撰写初稿", agent=writer)
review = Task(description="审查初稿，列出问题", agent=critic,
              context=[draft])       # 评审任务依赖初稿输出
revise = Task(description="按评审意见修订终稿", agent=writer,
              context=[draft, review])
Crew(agents=[writer, critic], tasks=[draft, review, revise]).kickoff()
```

## 6. 反模式与坑点

1. **无终止条件的死循环** [E]：批评者永远能挑出毛病，缺哨兵信号或最大迭代数会导致循环失控。
2. **自我反思的认知偏差** [F]：同一智能体既当运动员又当裁判，自我评审有系统性偏差；重要场景用独立批评者（不同角色设定与提示）。
3. **批判意见无结构** [F]：批评者输出散文式泛泛而谈，执行者无从下手改进；应要求项目符号列表式的结构化反馈（书中做法）。
4. **为反思而反思** [E]：低价值任务套反思循环，延迟与成本翻倍无收益；遵循「质量优先于速度时才用」的经验法则。
5. **反思不接记忆** [F]：无记忆时每轮反思都是独立事件，无法累积进步。

## 7. 与其他模式的组合

- **反思 + 规划（04）**：执行结果经反思审查，反馈触发重规划——Deep Research 具备反思、规划和执行能力 [F]。
- **反思 + RAG（06）**：智能体 RAG 的来源验证与冲突调和，降幻觉 [F]。
- **反思 + 多智能体（10）**：「批评-审查者」本身就是多智能体协作形式之一 [F]。
- **反思 + 记忆管理（08）**：反思成为累积改进过程 [F]。
- **反思 + 评估（19）**：反思的批评者结构可直接复用为评估器 [E]。

## 8. 评估指标

- **结果导向**：迭代前后质量差（同一任务初稿 vs 终稿按标准打分）；错误率下降幅度。
- **过程导向**：平均迭代轮次（过多说明初稿质量差或批评过苛）；终止原因分布（哨兵停止 vs 达到上限——后者占比高需警惕）。
- **轨迹审查**：批判意见是否具体可执行；修订是否真实回应了批判点（而非重写一遍）[E]。
