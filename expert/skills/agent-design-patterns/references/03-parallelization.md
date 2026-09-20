# 03 · 并行化（Parallelization）

> 溯源：《智能体设计模式》第 3 章 并行化 · 板块：核心执行与任务分解
> 证据基准：本节内容除特别标注外，均为书中原文确认 [F]。

## 1. 模式定义

并行化（Parallelization）指同时执行多个互不依赖的组件——LLM 调用、工具使用乃至整个子智能体——而非一个接一个地串行处理 [F]。其核心思想是识别流程中彼此无依赖的部分并发执行，待全部完成后再进入汇聚整合步骤，从而大幅缩短可拆分任务的整体执行时间 [F]。

## 2. 工作机制

并行化的运转分三步 [F]：

1. **依赖分析**：识别流程中彼此无依赖的子任务——这是模式成立的前提。
2. **并发执行**：独立任务同时运行；涉及外部服务（API、数据库）有延迟时，同时发起多个请求收益最明显。
3. **汇聚整合**：综合步骤通常是串行的，需等待全部并行步骤完成后进行。

流程骨架（框架无关，以双来源研究为例）：

- 串行版：搜索来源 A → 总结 A → 搜索来源 B → 总结 B → 综合（总耗时为各步之和）
- 并行版：搜索 A ‖ 搜索 B（同时）→ 总结 A ‖ 总结 B（同时）→ 综合汇总（等待全部完成）

实现上通常需要支持异步执行或多线程/多进程的框架 [F]。注意 asyncio 提供的是**并发而非真正并行**：事件循环在任务等待 I/O 时切换，多个任务「同时」推进，但实际仍在单线程下受 GIL 限制——对 I/O 密集的 LLM/API 调用有效，对 CPU 密集计算无效 [F]。

框架机制 [F]：LangChain LCEL 中将多个 runnable 组合为结构化集合（RunnableParallel）即可并发执行；LangGraph 通过图拓扑让多个无依赖节点由同一节点并发扇出、结果在汇聚节点整合；Google ADK 原生支持 ParallelAgent 并发运行子智能体，再由 SequentialAgent 串行收口。

## 3. 适用场景与不适用场景

| 适用 ✅ | 不适用 ❌ |
|---|---|
| 信息收集与调研：同时搜索新闻、拉取股票数据、查社交媒体与公司库 [F] | 步骤间存在严格数据依赖（后步需前步结果）：改用提示链(01) |
| 数据处理与分析：情感分析 ‖ 关键词提取 ‖ 分类 ‖ 紧急问题识别 [F] | 需先分类再选路径的任务：改用路由(02) |
| 多 API / 工具交互：旅行规划同时查机票、酒店、活动、餐厅 [F] | [E] 子任务需共享可变状态：竞态风险，先串行或做状态隔离 |
| 多组件内容生成：营销邮件的主题 ‖ 正文 ‖ 图片 ‖ CTA 文案 [F] | [E] 下游有严格速率限制或预算约束：并发反触发限流 |
| 验证与校验：邮箱格式 ‖ 手机号 ‖ 地址库 ‖ 敏感词检测 [F] | |
| 多模态处理：文本情感与关键词 ‖ 图片物体与场景 [F] | |
| A/B 多方案生成：不同 prompt 或模型并行产出多版文案再选优 [F] | |

## 4. 选型决策要点

1. **经验法则** [F]：当流程包含多个可独立运行的操作（如多 API 拉取、数据分块处理、多内容生成）时，采用并行化。
2. **依赖分析先行** [F]：核心是识别无依赖部分；综合/汇总步骤通常保持串行，作为汇聚点等待全部并行分支完成。
3. **正视复杂度代价** [F]：并发/并行架构会增加设计、调试和日志等开发复杂度与成本——并行不是免费优化，收益要能覆盖额外复杂度。
4. **汇聚点策略** [E]：预先明确「全部成功才汇总」还是「容忍部分失败」，失败分支用占位值或重试，避免空结果流入汇总提示。
5. **并发度与限流** [E]：对外部 API 并发需考虑速率限制与成本峰值；分支数应设上限，必要时分批扇出。

## 5. 多框架代码模板

### 5.1 框架无关伪代码

```text
# 并行化 = 独立任务并发 + 汇聚整合（Map-Reduce 骨架）
parallel_block = Parallel(
    task_1 = Step("调研子主题甲"),   # 互不依赖，可同时运行
    task_2 = Step("调研子主题乙"),
    task_3 = Step("调研子主题丙"),
)
pipeline = Sequence(
    parallel_block,                  # 全部完成后才进入下一步
    Step("汇总三路结果为结构化报告")  # 汇聚点通常串行
)
result = pipeline.run(topic)
```

### 5.2 LangChain / LangGraph（源自书中第 3 章实码 [F]，改写为骨架）

```python
# LangChain / LCEL（书中第 3 章示例，版本需核对最新文档）
# 1. 组件定义：三条独立链（摘要 / 问题 / 关键词），互不依赖
import asyncio
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableParallel, RunnablePassthrough

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)  # 密钥经环境变量读取

def make_chain(system: str):
    return (ChatPromptTemplate.from_messages(
                [("system", system), ("user", "{topic}")])
            | llm | StrOutputParser())

summarize_chain = make_chain("请简明总结以下主题：")
questions_chain = make_chain("请针对以下主题生成三个有趣的问题：")
terms_chain = make_chain("请从以下主题提取 5-10 个关键词，逗号分隔：")

# 2. 模式接线：RunnableParallel 并发扇出 + 汇总链串行收口
map_chain = RunnableParallel(
    summary=summarize_chain, questions=questions_chain,
    key_terms=terms_chain, topic=RunnablePassthrough())  # 原始输入透传

synthesis_prompt = ChatPromptTemplate.from_messages([
    ("system", "根据摘要 {summary}、问题 {questions}、关键词 {key_terms} 综合生成完整答案。"),
    ("user", "原始主题：{topic}")])
full_parallel_chain = map_chain | synthesis_prompt | llm | StrOutputParser()

# 3. 执行入口：ainvoke 异步并发执行
topic = "太空探索的历史"  # TODO(user): 替换主题
response = asyncio.run(full_parallel_chain.ainvoke(topic))
# 4. 观测与护栏：并发分支注意 API 速率限制；单分支失败需重试或占位
print(response)
```

### 5.3 Google ADK（源自书中第 3 章实码 [F]，改写为骨架）

```python
# google-adk（书中第 3 章示例，版本需核对最新文档）
# 1. 组件定义：三个调研子智能体，output_key 各自写入会话状态
from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
from google.adk.tools import google_search

def researcher(name: str, topic: str, output_key: str) -> LlmAgent:
    return LlmAgent(
        name=name, model="gemini-2.0-flash",
        instruction=f"调研「{topic}」。请简明总结关键发现（1-2 句），只输出摘要。",
        tools=[google_search], output_key=output_key)

r1 = researcher("researcher_a", "可再生能源最新进展", "result_a")
r2 = researcher("researcher_b", "电动汽车技术最新进展", "result_b")
r3 = researcher("researcher_c", "碳捕集方法现状", "result_c")

# 2. 模式接线：ParallelAgent 并发扇出 → 汇总智能体串行整合
parallel_research = ParallelAgent(name="parallel_research",
    sub_agents=[r1, r2, r3],
    description="并行运行多个调研智能体，收集信息。")

merger = LlmAgent(name="merger", model="gemini-2.0-flash",
    instruction=("将 {result_a}、{result_b}、{result_c} 合成为结构化报告，"
                 "严格基于输入摘要，不得添加任何外部知识。"))

pipeline = SequentialAgent(name="research_pipeline",
    sub_agents=[parallel_research, merger])

# 3. 执行入口
root_agent = pipeline  # TODO(user): 经 Runner 会话调用
# 4. 观测与护栏：merger 指令限定「仅整合输入」，防止汇总阶段幻觉外溢
```

### 5.4 CrewAI（本书该章未提供 CrewAI 示例，以下为工程实践推断 [E]，需核对最新文档）

```python
# CrewAI（版本需核对最新文档）
# 1. 组件定义：多个互不依赖的任务，async_execution=True 允许并发
from crewai import Agent, Task, Crew, Process

researcher = Agent(role="领域调研员", goal="调研分配的子主题并输出摘要",
    backstory="你只负责分配给你的子主题。", allow_delegation=False)

task_a = Task(description="调研子主题甲：{topic}，输出 1-2 句摘要",
    expected_output="摘要文本", agent=researcher, async_execution=True)
task_b = Task(description="调研子主题乙：{topic}，输出 1-2 句摘要",
    expected_output="摘要文本", agent=researcher, async_execution=True)
# TODO(user): 为各分支配置专职 agent 与不同工具

# 2. 模式接线：汇总任务（同步）依赖前述异步任务，框架等待全部完成后执行
task_merge = Task(description="将以下摘要整合为结构化报告：{summaries}",
    expected_output="结构化报告", agent=researcher)  # TODO(user): 指定汇总 agent

# 3. 执行入口：顺序流程中，异步任务并发、同步任务等齐后收口
crew = Crew(agents=[researcher],
            tasks=[task_a, task_b, task_merge], process=Process.sequential)
result = crew.kickoff(inputs={"topic": "TODO(user): 主题"})

# 4. 观测与护栏：汇总前检查各异步分支结果非空，失败分支重试或占位
```

## 6. 反模式与坑点

1. **伪并行** [E]：把存在隐式依赖的任务并发执行，导致结果错乱或分支间相互覆盖；依赖分析必须先于并发改造。
2. **并行分支共享可变状态** [E]：多个分支同时写同一状态会产生竞态；各分支应输出到独立键（如 ADK 的不同 output_key），汇聚点只读。
3. **汇聚点无部分失败处理** [E]：一个分支失败即整体失败，或空值静默流入汇总提示；应显式定义失败分支的占位与重试策略。
4. **为并行而并行** [E]：任务本身轻量、串行开销可忽略时，并发只增加复杂度与调试成本（书中亦警示并发增加设计、调试与日志成本 [F]）。
5. **误把 asyncio 当真并行** [F]：事件循环是并发调度而非真正并行，单线程下仍受 GIL 限制；CPU 密集型子任务并发无收益，需多进程或外部计算。

## 7. 与其他模式的组合

- **并行化 + 提示链(01)** [F]：书中研究智能体范式——并行数据采集完成后，用链式依赖完成合并数据、综合初稿、审阅完善；复杂流程常是「并行采集 + 串行综合」。
- **并行化 + 路由(02)** [E]：路由先分流，各分支内部再并行，形成「先分流、后并发」的两级结构。
- **并行化 + 多智能体(10)** [F]：ADK ParallelAgent 并发运行多个子智能体，是多智能体系统提升效率与可扩展性的原生形态。
- **并行化 + 反思(07)** [E]：A/B 多方案并行生成 + 评估反思选优，对应书中「验证与校验」「多方案生成」场景的延伸闭环。
- **并行化 + 资源优化(16)** [E]：并发度、速率限制与成本峰值管理联动，在延迟与资源消耗间取平衡。

## 8. 评估指标

- **结果导向**：端到端延迟（对比串行基线的加速比）；输出完整率（各分支结果均正确进入汇总）。
- **过程导向**：并行分支失败率与重试次数；汇聚点等待时间（由最长分支耗时决定）；并发请求峰值与总成本。
- **轨迹审查** [E]：核对分支确为并发发起（调用时间戳重叠），而非框架退化为串行；失败分支是否被占位/重试机制接住。
