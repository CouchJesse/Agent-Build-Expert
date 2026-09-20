# 06 · 知识检索（RAG，Retrieval-Augmented Generation）

> 溯源：《智能体设计模式》第 14 章 知识检索（RAG）· 板块：环境交互与知识
> 证据基准：本节内容除特别标注外，均为书中原文确认 [F]。

## 1. 模式定义

RAG 让 LLM 能够访问并集成外部、最新、特定场景的信息，从而提升输出的准确性、相关性和事实基础。与仅依赖内部预训练知识不同，RAG 允许 LLM「查找」信息——类似人类查阅书籍或搜索互联网，提供更准确、最新、可验证的答案。

**核心价值** [F]：此过程让 LLM 从「闭卷」推理者变为「开卷」推理者，显著提升实用性和可信度。

## 2. 工作机制

核心流程：用户查询**不直接发给 LLM**，而是先在外部知识库（文档库、数据库、网页）中做语义搜索 → 提取最相关片段（chunk）→ 将片段「增强」到原始提示中 → 增强后的提示送入 LLM 生成有事实依据的响应 [F]。

关键概念 [F]：

| 概念 | 要点 |
|---|---|
| 嵌入 Embeddings | 文本的数值向量表示；语义相近的文本在向量空间距离更近 |
| 语义相似度与距离 | 寻找与查询语义距离最小的文档；措辞不同也能匹配 |
| 文档分块 Chunking | 大文档拆为小片段；分块策略对保留上下文和意义至关重要 |
| 检索技术 | 向量搜索为主；BM25 关键词频率；混合检索 = BM25 精确匹配 + 语义搜索 |
| 向量数据库 | 专为存储查询嵌入设计（HNSW 最近邻算法）；Pinecone/Weaviate/ChromaDB/Milvus/Qdrant，Redis/Elasticsearch/pgvector 亦可 |

两个进阶形态 [F]：

- **GraphRAG**：用知识图谱替代向量库，遍历实体（节点）间显式关系（边），能整合分散在多文档的信息、回答复杂关联问题（金融分析、基因与疾病关系）；代价是图谱构建维护复杂、成本高、灵活性低。
- **智能体 RAG（Agentic RAG）**：引入推理与决策层，智能体作为「把关者和知识精炼者」主动参与，四种能力：①反思与来源验证（识别权威来源、丢弃过时文档）；②调和知识冲突（优先最可靠数据）；③多步推理（拆分子查询分别检索再综合）；④识别知识空缺并调用外部工具（如实时 Web 搜索）。从被动数据管道转变为主动问题解决框架；代价是复杂性、成本、延迟显著上升。

## 3. 适用场景与不适用场景

| 适用 ✅ | 不适用 ❌ |
|---|---|
| 企业搜索与问答：HR 政策、技术手册、产品规格等内部文档 | 通用常识问答：训练数据已覆盖且不涉时效 |
| 客户支持/服务台：基于产品手册、FAQ、工单精准答复 | 实时性要求极高且无固定知识库：直接用搜索工具（05） |
| 个性化推荐：按用户偏好/历史语义检索内容 | [E] 小规模静态 FAQ：直接塞入提示更简单 |
| 新闻/时事摘要：集成实时新闻源 | |
| 多源关联分析（GraphRAG）：金融、科研实体关系 | |

书中经验法则 [F]：当需要 LLM 基于最新、专有或训练数据之外的信息回答问题或生成内容时，采用此模式。

## 4. 选型决策要点

1. **知识边界判据**：答案所需知识是否在训练数据之外（企业内部/实时/高度专业）？是 → RAG [F]。
2. **幻觉严重时优先考虑** [F]：RAG 帮助克服训练数据过时、减少幻觉，且支持可归因答案（响应基于检索来源）。
3. **普通 RAG vs GraphRAG** [F]：需跨多文档整合关系 → GraphRAG；单点事实查询 → 向量 RAG。
4. **被动 vs 主动** [F]：固定语料简单问答 → 标准 RAG 流水线；需验证来源、调和冲突、多步检索 → 智能体 RAG。
5. **成本意识** [F]：RAG 增加延迟、运维成本和 Token 数量；知识库预处理与定期同步是持续工程投入。

## 5. 多框架代码模板

### 5.1 框架无关伪代码

```text
# 离线索引
for doc in corpus:
    chunks = split(doc, chunk_size=500, overlap=50)   # 分块策略至关重要
    for c in chunks: vector_db.store(embed(c), metadata=c)
# 在线检索
query_vec = embed(user_question)
chunks = vector_db.search(query_vec, top_k)            # 或混合检索 BM25+向量
prompt = template(question, chunks)                    # 增强：片段融入提示
answer = llm(prompt)                                   # 带来源归因输出
```

### 5.2 LangChain + LangGraph（源自书中第 14 章实码 [F]，改写为骨架）

```python
# LangChain + LangGraph（书中示例：Weaviate + OpenAI；版本需核对最新文档）
# 1. 组件定义：加载 → 分块 → 向量化入库
from langchain_text_splitters import CharacterTextSplitter
splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=50)
documents = splitter.split_documents(TextLoader("kb.md").load())
vectorstore = Weaviate.from_documents(
    client=weaviate_client, documents=documents,
    embedding=OpenAIEmbeddings())          # 密钥从环境变量读取
retriever = vectorstore.as_retriever()

# 2. 模式接线：StateGraph 两节点——retrieve → generate
from langgraph.graph import StateGraph, END
from typing import TypedDict

class RAGState(TypedDict):
    question: str; documents: list; generation: str

def retrieve_node(state):
    return {"documents": retriever.invoke(state["question"])}
def generate_node(state):                   # 增强提示 + 生成
    rag_chain = prompt_template | ChatOpenAI(temperature=0) | StrOutputParser()
    return {"generation": rag_chain.invoke(state)}

# 3. 执行入口
workflow = StateGraph(RAGState)
workflow.add_node("retrieve", retrieve_node)
workflow.add_node("generate", generate_node)
workflow.set_entry_point("retrieve")
workflow.add_edge("retrieve", "generate")
workflow.add_edge("generate", END)
app = workflow.compile()

# 4. 观测与护栏：记录检索到的 chunks 供来源归因审计
```

### 5.3 Google ADK（源自书中第 14 章实码 [F]，改写为骨架）

```python
# Google ADK（书中两例）
from google.adk.tools import google_search
from google.adk.memory import VertexAiRagMemoryService
from google.adk.agents import Agent

# 1. 组件定义：内置搜索工具直接挂载
agent = Agent(name="rag_assistant",
              model="gemini-2.0-flash-exp",
              instruction="回答前先检索核实，标注来源。",
              tools=[google_search])

# 2. 模式接线：企业级持久语义检索——Vertex AI RAG Corpus
memory_service = VertexAiRagMemoryService(
    rag_corpus=corpus_name,
    similarity_top_k=5,                    # 检索结果数量
    vector_distance_threshold=0.7)         # 语义距离阈值
# 挂到 Runner 的 session_service，跨会话长期知识检索

# 3. 执行入口 / 4. 观测与护栏：grounding_metadata 提供来源归因
```

### 5.4 CrewAI（书中未提供该框架示例）

> 本书第 14 章未提供 CrewAI 的 RAG 示例。CrewAI 生态可用 `crewai-tools` 的 PDFSearchTool/KnowledgeSources 实现检索增强，以下为工程实践推断 [E]，需核对最新文档。

```python
# CrewAI（工程实践推断 [E]）
from crewai_tools import PDFSearchTool     # 需核对最新文档
research_tool = PDFSearchTool(pdf="kb.pdf")
researcher = Agent(role='知识检索员',
                   goal='基于知识库检索并核实信息。',
                   backstory='严谨的信息把关者。',
                   tools=[research_tool])
```

## 6. 反模式与坑点

1. **分块不当破坏语义** [F]：chunk_size/overlap 不合理导致上下文不完整；分块策略对保留上下文和意义至关重要。
2. **检索质量 = RAG 上限** [F]：效果高度依赖检索质量，无关块引入噪声；混合检索（BM25+向量）常优于单一方式。
3. **矛盾信息不处理** [F]：多个检索片段相互矛盾时直接生成会输出混乱答案——智能体 RAG 的「调和知识冲突」能力正是为此设计。
4. **忽略知识库同步** [F]：知识库预处理与定期同步是持续工程量；过时文档会污染答案（智能体 RAG 靠来源验证丢弃过时文档）。
5. **无来源归因** [E]：不记录检索到的 chunks，答案无法审计；应输出引用（ADK grounding_metadata / LangChain 记录 documents）。

## 7. 与其他模式的组合

- **RAG + 工具使用（05）**：检索本身即一种工具；智能体 RAG 在知识空缺时调用外部搜索工具 [F]。
- **RAG + 反思（07）**：智能体 RAG 的来源验证与冲突调和本质是反思在检索环节的应用 [F]。
- **RAG + 记忆管理（08）**：VertexAiRagMemoryService 把 RAG 作为长期记忆服务，跨会话知识检索 [F]。
- **RAG + 规划（04）**：研究类计划的信息收集阶段用 RAG 锚定事实 [E]。
- **RAG + MCP（11）**：通过 MCP 连接私有知识库与内部数据，公私融合检索（Deep Research API 用法）[F]。

## 8. 评估指标

- **结果导向**：答案准确率（对照知识库金标准）；幻觉率（无依据陈述占比）；可归因率（答案中带来源引用的陈述占比）。
- **过程导向**：检索命中率（top-k 中含正确片段的比率）；分块-查询相关性；延迟与 Token 成本（RAG 的固有开销）。
- **轨迹审查**：智能体 RAG 场景检查是否真实执行了来源验证、冲突调和、子查询拆解 [E]。
