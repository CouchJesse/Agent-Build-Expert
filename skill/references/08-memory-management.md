# 08 · 记忆管理（Memory Management）

> 溯源：《智能体设计模式》第 8 章 记忆管理 · 板块：状态与自我提升
> 证据基准：本节内容除特别标注外，均为书中原文确认 [F]。

## 1. 模式定义

记忆管理指智能体保留并利用过去交互、观察和学习经验的信息能力，是智能体超越基础问答能力、实现连贯对话、多步任务与个性化响应的前提。标准解决方案是**双组件记忆系统**：短期记忆（上下文记忆）保存最近交互于 LLM 上下文窗口，维持对话流畅；长期记忆（持久记忆）将需持久的信息存入外部存储（常为向量库），通过语义相似度实现高效检索，两者融合形成完整的知识体系。

## 2. 工作机制

记忆分两层协同运作 [F]：

```
输入: 用户消息
  ↓
[短期] 上下文窗口承载最近消息、回复、工具结果与当前反思
       （容量有限；旧片段需摘要压缩，长上下文模型只是扩容，
        内容仍临时、会话后丢失且成本高）
  ↓
[长期] 需跨会话保留的信息写入外部存储（数据库/知识图谱/向量库）
       检索时查询外部存储，取回相关数据融合进短期上下文
  ↓
输出: 带历史上下文的响应 + 新沉淀的长期记忆
```

各框架的具体映射 [F]：

- **ADK 三件套**：`Session`（单条聊天线程，含 events 与 state）、`State`（会话临时数据字典，前缀 `user:`/`app:`/`temp:` 标明归属与持久性）、`Memory`（可检索的长期知识仓库）。`SessionService` 管理会话生命周期（InMemory 适合测试 / Database 持久化 / VertexAI 云端扩展），`MemoryService` 负责长期知识的存取（`add_session_to_memory` 沉淀、`search_memory` 检索）。每轮消息经 Runner 获取 Session → 处理 → `append_event` 记录并更新 state。
- **LangChain / LangGraph**：短期记忆为线程级对话历史，LangGraph 将其作为智能体状态经 checkpointer 持久化；长期记忆存于自定义命名空间（Store），分语义（事实）、情景（经历，常以 few-shot 复用）、程序性（规则指令，经反思更新）三类。
- **Vertex Memory Bank**：托管服务，用 LLM 异步分析对话历史自动提取关键事实与用户偏好，按作用域持久存储并智能合并新数据、解决矛盾。

## 3. 适用场景与不适用场景

| 适用 ✅ | 不适用 ❌ |
|---|---|
| 对话式 AI：短期记忆保持连贯，长期记忆回忆偏好实现个性化 [F] | 无状态单轮问答：不涉及历史与偏好 [E] |
| 任务型智能体：短期跟踪前序步骤与进度，长期访问用户相关数据 [F] | 强一致确定性任务：记忆注入引入输出不可重复 [E] |
| 个性化体验：存储检索用户偏好、历史行为，调整响应与建议 [F] | 一次性批处理任务：会话间无复用价值 [E] |
| 学习与提升：将成功策略、错误与新知识存入长期记忆供未来适应 [F] | |
| RAG 问答：知识库即长期记忆，检索增强生成（见 06）[F] | |
| 自主系统（机器人/自动驾驶）：即时环境 + 通用环境知识分层记忆 [F] | |

## 4. 选型决策要点

1. **经验法则** [F]：只要智能体需要做的不仅仅是回答单个问题，就应采用本模式——需在对话中保持上下文、跟踪多步任务进度、通过回忆用户偏好实现个性化、或根据过往成败学习适应，记忆管理均为必需。
2. **短/长记忆边界** [F]：信息只需本轮会话内可见 → 上下文窗口/State；需跨会话、跨任务回溯 → 外部存储 + 语义检索。长上下文模型只扩大短期容量，不能替代长期记忆。
3. **存储实现选型** [F]：内存实现（InMemorySessionService / InMemoryStore）仅用于测试；生产选数据库或云端服务（DatabaseSessionService / VertexAiRagMemoryService），按持久性与扩展性需求决定。
4. **State 设计纪律** [F]：键用字符串 + 可序列化基本类型，清晰命名、正确前缀、避免深层嵌套；更新只走 `output_key` 或 `append_event` 时的 `state_delta`。
5. **记忆粒度** [E]：沉淀什么进长期记忆需筛选（关键事实、偏好、成功策略），全量转储会污染检索并推高成本。

## 5. 多框架代码模板

### 5.1 框架无关伪代码

```text
short_term = ContextWindow()              # 短期：会话内临时上下文
long_term  = VectorStore(namespace)     # 长期：跨会话持久 + 语义检索

on_message(user_input):
    hits = long_term.semantic_search(user_input)   # 语义相似度检索
    short_term.inject(hits)                        # 融合进当前上下文
    response = agent.process(short_term.context)
    short_term.summarize_if_full()                  # 窗口将满时摘要旧片段
    long_term.upsert(extract_facts(response))       # 关键事实沉淀归档
```

### 5.2 LangChain / LangGraph（源自书中第 8 章实码 [F]，改写为骨架）

```python
# LangChain / LangGraph（书中示例改写为骨架，需核对最新文档）
from langchain.memory import ConversationBufferMemory
from langgraph.store.memory import InMemoryStore

# 1. 组件定义：短期 = 链内 Buffer 记忆；长期 = Store（命名空间 + 键组织）
memory = ConversationBufferMemory(memory_key="chat_history",
                                   return_messages=True)  # ChatModel 推荐 True

def embed(texts): ...  # TODO(user): 接入真实 embedding 模型
store = InMemoryStore(index={"embed": embed, "dims": 2})
namespace = ("my_user", "chitchat")     # 命名空间类比文件夹，键类比文件名

# 2. 模式接线：长期记忆 put / get / search
store.put(namespace, "a-memory", {"rules": ["用户偏好简短直接的回复"]})
items = store.search(namespace, query="语言偏好",
                     filter={"my-key": "my-value"})  # 语义 + 过滤检索

# 3. 执行入口：LLMChain(llm=..., prompt=..., memory=memory) 链式自动注入历史
# 4. 观测与护栏：程序性记忆经反思更新（update_instructions 模式）；
#    LangGraph 短期记忆经 checkpointer 随线程持久化、可恢复
```

### 5.3 Google ADK（源自书中第 8 章实码 [F]，改写为骨架）

```python
# Google ADK（书中示例改写为骨架，需核对最新文档）
from google.adk.agents import LlmAgent
from google.adk.sessions import InMemorySessionService
from google.adk.memory import InMemoryMemoryService

# 1. 组件定义：Session / State / Memory 三件套
session_service = InMemorySessionService()  # 生产换 DatabaseSessionService
memory_service = InMemoryMemoryService()    # 生产换 VertexAiRagMemoryService
agent = LlmAgent(name="my_agent", model="gemini-2.0-flash",
                 instruction="TODO(user): 任务指令",
                 output_key="last_reply")    # 最终回复自动写入 state

# 2. 模式接线：工具内经 tool_context 更新 state（前缀标作用域）
def record_preference(tool_context) -> dict:
    state = tool_context.state
    state["user:lang"] = "zh"          # user: 跨会话共享；app: 全局；temp: 本轮
    return {"status": "success"}

# 3. 执行入口：Runner 逐事件驱动，append_event 携带 state_delta 落库；
#    会话结束后 await memory_service.add_session_to_memory(session) 沉淀长期记忆
# 4. 观测与护栏：search_memory 检索长期记忆注入上下文
# SAFETY: 禁止直接修改 session.state 字典——绕过事件机制，变更不被记录与持久化
# SAFETY: 记忆含用户个人信息，对外共享/外发前须脱敏并经用户同意
```

### 5.4 CrewAI（本书该章未提供示例）

> 本书第 8 章未提供 CrewAI 记忆管理示例（仅说明 Memory Bank 等托管服务可经 API 接入 CrewAI [F]），以下为工程实践推断 [E]，需核对最新文档。

```python
# CrewAI（工程实践推断 [E]，需核对最新文档）
from crewai import Agent, Task, Crew

# 1. 组件定义
researcher = Agent(role="研究员", goal="完成任务并记住用户偏好",
                   backstory="TODO(user)", llm=my_llm)

# 2. 模式接线：Crew(memory=True) 启用内置短期/长期/实体记忆
crew = Crew(agents=[researcher], tasks=[my_task], memory=True)

# 3. 执行入口
result = crew.kickoff()

# 4. 观测与护栏：跨会话记忆须自行写入外部存储（向量库）并在新 Crew 启动时检索注入
```

## 6. 反模式与坑点

1. **直接改 session.state 字典** [F]：绕过标准事件处理机制——变更不被记录、无法持久化、可能引发并发问题且不更新元数据。应主要用 state 读取数据，更新一律走 `output_key` 或 `EventActions.state_delta`。
2. **把长上下文窗口当长期记忆** [F]：长上下文只扩大短期容量，内容依然临时、会话结束即丢失，且每次处理全量内容成本高。
3. **会话历史无压缩** [F]：完整历史可能超出上下文窗口，导致错误或性能下降；旧片段应及时摘要或突出关键信息。
4. **State 结构深层嵌套** [F]：state 应保持简单——基本类型、清晰命名、正确前缀。
5. **长期记忆不做语义检索** [E]：书中的长期检索靠向量库语义相似度而非关键词精确匹配；只做精确匹配会让「换个说法就查不到」，记忆等于白存。

## 7. 与其他模式的组合

- **记忆管理 + RAG（06）** [F]：面向问答的智能体访问知识库（长期记忆），通常通过 RAG 检索相关文档辅助回答；ADK 的 VertexAiRagMemoryService 即以 RAG 服务承载长期记忆。
- **记忆管理 + 反思（07）** [F]：没有记忆时每次反思是独立事件；有记忆时反思成为累积过程——反思还可反向更新程序性记忆（系统提示中的规则指令）。
- **记忆管理 + 学习与适应（09）** [F]：智能体将成功策略、错误和新知识存入长期记忆，供未来适应复用（基于记忆的学习）。
- **记忆管理 + 规划（04）** [F]：多步任务用短期记忆跟踪前序步骤、当前进度与总体目标。
- **记忆管理 + 目标监控（13）** [E]：监控指标与进度存于 State（`task_status` 类键），为达标判定提供数据基础。

## 8. 评估指标

- **结果导向**：跨会话信息保持率（新会话能否正确回忆关键事实与偏好）；个性化命中率（利用记忆生成的响应是否符合用户偏好）[E]。
- **过程导向**：长期记忆检索命中率与信噪比（`search_memory` 返回结果的利用率）；上下文窗口占用率；状态更新合规率（经 `output_key`/`state_delta` 更新的占比，直改字典应恒为 0）。
- **轨迹审查** [E]：检索到的记忆是否真实被响应引用利用（而非注入后无视）；长期库中的事实是否随新交互得到更新与矛盾消解。
