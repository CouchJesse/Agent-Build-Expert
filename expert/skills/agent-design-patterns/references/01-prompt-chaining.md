# 01 · 提示链（Prompt Chaining）

> 溯源：《智能体设计模式》第 1 章 提示链（Prompt Chaining） · 板块：核心执行与任务分解
> 证据基准：本节内容除特别标注外，均为书中原文确认 [F]。

## 1. 模式定义

提示链（Prompt Chaining），又称流水线（Pipeline）模式，采用分而治之策略：将复杂任务拆解为一系列更小、更易管理的子问题，每个子问题由专门设计的提示单独处理，前一步的输出作为下一步的输入，形成链式依赖 [F]。它让 LLM 每次只专注单一操作，显著提升复杂多步交互的可靠性与可控性，是构建具备多步推理、工具集成与状态管理能力的智能体的基础技术 [F]。

## 2. 工作机制

提示链的实质是**顺序流水线 + 结构化信息传递**，运转过程如下：

1. **拆解**：开发者预先将任务拆为固定步骤序列，每步包含一次 LLM 调用或一段确定性处理逻辑（验证、格式转换、条件分支）[F]。
2. **传递**：每步输出作为下一步输入，前序上下文与结果引导后续处理，使模型在前一步基础上不断完善理解、逐步逼近目标解 [F]。
3. **集成**：任意步骤可指示 LLM 与外部系统、API 或数据库交互，使其不仅是孤立模型，更是智能系统的核心组件 [F]。

流程骨架（框架无关）：

- 输入：原始文本 / 用户请求
- 步骤 1（摘要）：聚焦提示，产出结构化中间结果
- 步骤 2（趋势识别）：建立在已验证结果之上，提取数据点（JSON）
- 步骤 3（邮件撰写）：基于前步结构化数据生成最终输出

步骤间数据完整性是可靠性关键：若某步输出模糊或格式不规范，后续提示会因输入错误而失败。书中建议为每步指定结构化输出格式（JSON / XML），使数据可被机器精确解析后传递，减少自然语言理解带来的错误 [F]。

书中还提出**上下文工程**视角：模型输出质量更多取决于为其构建的完整信息环境（系统提示、检索文档、工具输出、用户身份与历史交互），而非模型架构本身 [F]。提示链的每一步，本质上都是一次「为该步构建最小完备上下文」的机会——各步可分配不同角色（如市场分析师、文档专家）以聚焦职责 [F]。

## 3. 适用场景与不适用场景

| 适用 ✅ | 不适用 ❌ |
|---|---|
| 信息处理流程：提取 → 摘要 → 实体抽取 → 查知识库 → 生成报告 [F] | 单步即可完成的简单请求：直接单次调用 |
| 复杂问答：多步推理、多源信息整合（先拆子问题再综合）[F] | 需按输入动态选择执行路径：改用路由(02) |
| 数据提取与转换：发票/表单字段提取 + 校验 + 条件重试循环 [F] | 子任务彼此独立、无依赖：改用并行化(03) |
| 内容生成流程：构思 → 大纲 → 分段撰写 → 审阅修订 [F] | 步骤序列需智能体运行期探索：改用规划(04) |
| 有状态对话智能体：每轮构建新提示并整合累积状态 [F] | [E] 两步以内的轻量任务：拆链收益小于成本 |
| 代码生成与优化：伪代码 → 初稿 → 查错 → 重写 → 补测试 [F] | |
| 多模态多步推理：图片文本提取 → 关联标签 → 结合表格解释 [F] | |

## 4. 选型决策要点

1. **经验法则** [F]：当任务过于复杂、包含多阶段处理、需在步骤间调用外部工具，或需构建多步推理与状态管理的智能体时，采用本模式。
2. **单一提示的天花板** [F]：多约束任务中，单一复杂提示易忽略部分指令、丢失上下文、错误累积甚至幻觉；拆解为聚焦步骤可降低模型认知负担（如「分析报告 + 总结 + 提取 + 写邮件」四合一提示常漏做环节）。
3. **与路由(02)的边界**：提示链是开发者预定义的固定线性路径；一旦需要按输入在多条路径间仲裁，就升级为路由。
4. **与并行化(03)、规划(04)的边界**：子任务相互独立 → 并行化；步骤需智能体动态生成而非预先写死 → 规划。
5. **结构化输出先行** [F]：设计链时先为每步约定输出 schema（JSON/XML），这是多步 LLM 系统可靠运转的关键工程约定。

## 5. 多框架代码模板

### 5.1 框架无关伪代码

```text
# 提示链 = 顺序步骤 + 结构化传递
chain = Sequence(
    Step(name="extract",   prompt="从输入文本提取技术规格", output_format="text"),
    Step(name="transform", prompt="将规格转为 JSON（cpu/memory/storage）", output_format="json"),
    # 可继续追加：validate（确定性校验）/ review（审阅）等步骤
)
result = chain.run(input_text)
# 约定：每步输入 = 前一步的结构化输出；步间可插入验证与条件重试
```

### 5.2 LangChain / LangGraph（源自书中第 1 章实码 [F]，改写为骨架）

```python
# LangChain（书中第 1 章示例，LCEL，版本需核对最新文档）
# 1. 组件定义：两步提示（提取 → 转 JSON），每步一个聚焦提示
import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

llm = ChatOpenAI(temperature=0)  # 密钥经环境变量 OPENAI_API_KEY 读取

prompt_extract = ChatPromptTemplate.from_template(
    "请从以下文本中提取技术规格：\n\n{text_input}")
prompt_transform = ChatPromptTemplate.from_template(
    "请将以下技术规格转为 JSON，含 'cpu'、'memory'、'storage' 键：\n\n{specifications}")

# 2. 模式接线：LCEL 管道串联，前一步输出注入下一步提示变量
extraction_chain = prompt_extract | llm | StrOutputParser()
full_chain = (
    {"specifications": extraction_chain}
    | prompt_transform | llm | StrOutputParser()
)

# 3. 执行入口
input_text = "新款笔记本配备 3.5GHz 八核处理器、16GB 内存和 1TB NVMe SSD。"  # TODO(user): 替换输入
final_result = full_chain.invoke({"text_input": input_text})

# 4. 观测与护栏：对中间输出做格式校验后再进入下一步，防错误沿链传播
print(final_result)
```

### 5.3 Google ADK（本书该章未提供示例，以下为工程实践推断 [E]，需核对最新文档）

> 书中第 1 章未提供 ADK 实现，以下按模式机制与 ADK 官方原语（SequentialAgent + output_key 状态传递）推断编写。

```python
# google-adk（版本需核对最新文档）
# 1. 组件定义：两个子智能体各司其职，output_key 把结果写入会话状态
from google.adk.agents import LlmAgent, SequentialAgent

extractor = LlmAgent(
    name="extractor",
    instruction="从用户文本中提取技术规格，只输出规格要点。",
    output_key="specifications")
transformer = LlmAgent(
    name="transformer",
    instruction="将 {specifications} 转为 JSON，含 cpu/memory/storage 三键。",
    output_key="final_json")

# 2. 模式接线：SequentialAgent 串行编排，后一步经 {key} 引用前一步输出
pipeline = SequentialAgent(
    name="my_extract_transform_pipeline",
    sub_agents=[extractor, transformer])

# 3. 执行入口：经 Runner 会话调用（TODO(user): 参见第 02 章 runner 用法）
# 4. 观测与护栏：transformer 起点先校验 specifications 非空再转换
```

### 5.4 CrewAI（本书该章未提供 CrewAI 示例，以下为工程实践推断 [E]，需核对最新文档）

```python
# CrewAI（版本需核对最新文档）
# 1. 组件定义：两个专职智能体，职责单一
from crewai import Agent, Task, Crew, Process

extractor = Agent(role="信息抽取专员", goal="从原始文本提取技术规格",
    backstory="你只做提取，不做格式转换。", allow_delegation=False)
transformer = Agent(role="结构化转换专员", goal="把规格转为 JSON（cpu/memory/storage）",
    backstory="你只负责把给定规格转为 JSON。", allow_delegation=False)

# 2. 模式接线：顺序流程 + context 显式声明对前一步输出的依赖
task_extract = Task(description="从以下文本提取技术规格：{text}",
    expected_output="规格要点列表", agent=extractor)
task_transform = Task(description="将规格转为 JSON：{spec}",
    expected_output="JSON 字符串", agent=transformer,
    context=[task_extract])  # 链式依赖：消费前一步输出

# 3. 执行入口
crew = Crew(agents=[extractor, transformer],
            tasks=[task_extract, task_transform], process=Process.sequential)
result = crew.kickoff(inputs={"text": "TODO(user): 输入文本"})

# 4. 观测与护栏：使用前先 json.loads 校验 result 结构
```

## 6. 反模式与坑点

1. **单一巨型提示** [F]：把多阶段任务塞进一个复杂提示，模型易漏做关键环节（如只总结不提取）。应拆为聚焦的顺序步骤。
2. **步骤间传递自由文本** [F]：输出模糊或格式不规范会让后续步骤因输入错误而失败；每步应约定 JSON/XML 等结构化格式。
3. **链过长导致延迟与误差累积** [E]：每步增加一次调用时延，早期偏差会沿链放大；应控制链长，并在关键步骤后加确定性校验门。
4. **无中间验证直通到底** [E]：书中数据提取流程示范了「提取 → 校验 → 条件重试」循环 [F]；跳过校验会让错误静默传播到最终输出。
5. **为简单任务强上链** [E]：两步以内的轻量任务直接单次调用即可，拆链只增加成本与延迟。

## 7. 与其他模式的组合

- **提示链 + 工具使用(05)** [F]：任意步骤可调用外部 API/数据库（LLM 识别计算需求 → 调用工具 → 整合结果），实现单步难以可靠完成的精确操作。
- **提示链 + 路由(02)** [F]：路由可在处理链中间决定后续动作（书中第 2 章：路由机制可用于链中决策或工具选择）。
- **提示链 + 并行化(03)** [F]：书中研究智能体范式——并行采集多源数据后，用链式依赖完成合并、综合与审阅。
- **提示链 + 反思(07)** [F]：内容生成流程末位的「整体审阅优化」步骤，即链尾内嵌一次轻量反思。
- **提示链 + 记忆管理(08)** [E]：有状态对话智能体将累积对话状态注入每轮链首，实现跨轮上下文保持。

## 8. 评估指标

- **结果导向**：最终输出准确率（对照人工标注）；端到端任务完成率（关键环节无遗漏）。
- **过程导向**：各步结构化输出合规率（可解析率）；步间校验失败率与重试次数；链整体延迟（各步耗时之和）与每步成本。
- **轨迹审查** [E]：核对中间产物是否真实经过每一步（而非模型一步直出），早期步骤偏差是否被后续校验拦截。
