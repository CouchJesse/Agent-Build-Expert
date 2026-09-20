# 21 · 探索与发现（Exploration and Discovery）

> 溯源：《智能体设计模式》第 21 章 探索与发现 · 板块：可靠性与工程化
> 证据基准：本节内容除特别标注外，均为书中原文确认 [F]。

## 1. 模式定义

探索与发现模式让智能体主动寻找新信息、发现新可能性并识别「未知的未知」。它不同于反应式行为或在预定义解空间内的优化：核心是主动进入陌生领域、尝试新方法，生成新的知识或理解。在开放式、复杂或快速变化的领域，静态知识与预编程方案已不够用——本模式强调智能体扩展自身认知与能力的元能力。

## 2. 工作机制

标志性架构是**「生成—辩论—进化」迭代循环**（Google Co-Scientist 案例：基于 Gemini LLM 的科学协作系统，辅助假设生成、方案完善与实验设计）[F]：

```
人类科学家输入科学问题（研究目标先经安全审查）
  ↓
[生成]  生成智能体：文献探索 + 模拟科学辩论 → 提出初步假设
  ↓
[辩论]  反思智能体：同行评审（正确性 / 新颖性 / 质量）
        排序智能体：Elo 锦标赛式排名，比较与优先假设
        邻近智能体：邻近图聚类相似观点，辅助探索假设空间
  ↓
[进化]  进化智能体：优化高排名假设——简化概念、综合观点、非常规推理
  ↓
[元评审] 元评审智能体：综合评审与辩论结果，识别共性并反馈 → 进入下一轮
  ↓
[测试时计算扩展] 动态分配更多计算资源，迭代优化输出
  ↓
输出：经锦标赛式系统审查的假设（交由端到端实验验证）
```

系统级要点 [F]：主管智能体管理协调各专职智能体；异步任务执行框架支持算力弹性扩展；可综合学术文献、网络、数据库等多源信息。

验证效果（书中报告）[F]：GPQA「钻石集」top-1 准确率 78.4%，内部 Elo 评分与准确率高度一致；200+ 研究目标中测试时计算扩展可持续提升假设质量；15 个挑战性问题优于其他先进模型与人类专家「最佳猜测」。端到端验证：药物再利用（白血病候选药经体外实验证实）、新靶点发现（肝纤维化表观遗传靶点经类器官实验验证）、抗菌耐药性复现（两天内提出与独立团队十余年后验证一致的结论）。

配套工程形态是多智能体科研工作流框架（Agent Laboratory 类项目）[F]：分文献综述、实验（设计/准备/执行/分析，可调用代码执行与模型库工具）、报告撰写（LaTeX）、知识共享（自主研究成果库）四阶段；教授/博士后/评审/ML 工程/软件工程智能体模拟学术团队层级；三智能体评审用不同视角提示词模拟人类多元评判。定位是**增强而非取代人类研究**——「科学家在环」。

## 3. 适用场景与不适用场景

| 适用 ✅ | 不适用 ❌ |
|---|---|
| 科研自动化：设计实验、提出新假设、发现新材料/药物候选 [F] | 解空间已完全定义的优化问题：改用规划（04）+ 工具执行 [F] |
| 游戏策略生成：探索状态空间发现新策略（如 AlphaGo）[F] | 高吞吐确定性任务：用提示链（01）固定流程 [E] |
| 市场调研与趋势发现：扫描非结构化数据识别机会 [F] | 强一致性可预测性场景：探索的不确定性不可接受 [E] |
| 漏洞发现、创意内容生成、个性化教育路径 [F] | 无算力/成本预算的探索：迭代无终止条件，成本失控 [E] |

## 4. 选型决策要点

1. **经验法则** [F]：任务处于开放式/复杂/快变领域、解空间未完全定义时优先采用；目标是发现「未知的未知」，而非优化已知流程。
2. **探索与优化的边界** [F]：预定义解空间内找最优（参数/路径）不是本模式——那是规划（04）/路由（02）；需生成新假设、策略或洞察才是探索。
3. **多智能体框架是主流载体** [F]：专用智能体分工（生成/评审/进化/排序）模拟科学方法，结构化协作导航信息空间并生成新知识。
4. **人类角色必须保留** [F]：定位是增强人类——科学家以自然语言反馈、贡献观点、引导探索（「科学家在环」）；局限：仅依赖开放文献、负面结果获取有限、受 LLM 幻觉限制。
5. **安全与算力预算前置** [F]：研究目标与生成假设均须安全审查（1200 个对抗性目标测试显示可有效拒绝危险输入）；测试时计算扩展须设终止条件与预算。

## 5. 多框架代码模板

### 5.1 框架无关伪代码

```text
supervisor = Agent(role="研究主管")               # 协调各专职智能体
hypotheses = []
loop until (budget_exhausted or quality_converged):   # 扩展须有预算上限
    hypotheses += generate_agent(literature, debate)   # 生成：文献 + 辩论出假设
    reviews      = reflect_agent(hypotheses)           # 反思：同行评审
    ranked       = rank_agent(hypotheses, reviews)     # 排序：Elo 锦标赛
    hypotheses   = evolve_agent(ranked.top)            # 进化：优化高排名假设
    feedback     = meta_review_agent(reviews)          # 元评审：共性反馈入下轮
report = human_review(hypotheses)               # 科学家在环：人类最终裁决
```

### 5.2 多智能体评审机制（源自书中第 21 章实码 [F]，改写为骨架）

```python
# 纯 Python + OpenAI 兼容 API（书中 Agent Laboratory 类项目示例；密钥环境变量读取）
import os

# 1. 组件定义：三评审智能体——不同视角提示词模拟人类多元评判
class ReviewersAgent:
    def __init__(self, model="gpt-4o-mini", notes=None):
        self.notes = notes or []
        self.model = model
        self.api_key = os.environ.get("OPENAI_API_KEY")

    def inference(self, plan, report):
        reviewer_1 = "你是严苛但公正的评审，关注实验是否带来研究洞察。"
        reviewer_2 = "你是严苛、批判但公正的评审，关注研究对领域的影响。"
        reviewer_3 = "你是严苛、公正且开放的评审，关注是否有前所未有的新观点。"
        review_1 = get_score(plan, report, self.model, reviewer_1, self.api_key)
        review_2 = get_score(plan, report, self.model, reviewer_2, self.api_key)
        review_3 = get_score(plan, report, self.model, reviewer_3, self.api_key)
        return f"评审 #1:\n{review_1}\n评审 #2:\n{review_2}\n评审 #3:\n{review_3}"

def get_score(outlined_plan, latex, reward_model_llm, reviewer_type=None,
              attempts=3, api_key=None):
    """按学术评审 rubric 输出 JSON：Summary/Strengths/Weaknesses、
    Originality/Quality/Clarity/Significance（各1-4）、Overall（1-10）、
    Confidence（1-5）、Decision（仅 Accept 或 Reject）等字段。"""
    # TODO(user): 组装 rubric 提示词 → query_model(...) 调用评审模型
    #              → 解析 JSON（含重试 attempts 次）并返回
    ...

# 2. 模式接线：评审结果反馈给生成/进化智能体进入下一轮迭代
# 3. 执行入口：ReviewersAgent().inference(plan=研究方案, report=研究报告)
# 4. 观测与护栏：rubric 含 Ethical Concerns 布尔字段——标记后须人工复审
```

### 5.3 LangGraph（书中未提供该框架示例，工程实践推断 [E]）

```python
# LangGraph（工程实践推断 [E]，需核对最新文档）
from langgraph.graph import StateGraph, END

# 1. 组件定义：generate / debate / evolve / meta_review 四类节点
def generate(state):    ...   # 生成智能体：文献 + 辩论产出假设
def debate(state):      ...   # 反思 + 排序：评审打分与 Elo 排名
def evolve(state):      ...   # 进化智能体：优化 top 假设
def meta_review(state): ...   # 元评审：共性反馈

# 2. 模式接线：生成—辩论—进化循环，质量收敛或预算耗尽时退出
graph = StateGraph(dict)
graph.add_node("generate", generate)
graph.add_node("debate", debate)
graph.add_node("evolve", evolve)
graph.add_node("meta_review", meta_review)
graph.set_entry_point("generate")
graph.add_conditional_edges("meta_review", route,    # 未收敛→再生成；收敛→END
                            {"loop": "generate", "done": END})

# 3. 执行入口：app.invoke({"research_goal": "...", "budget": 10})
# 4. 观测与护栏：每轮假设与评分入轨迹日志；research_goal 先过安全审查（18 章）
```

### 5.4 Google ADK（书中未提供该框架示例，工程实践推断 [E]）

```python
# google-adk（工程实践推断 [E]，需核对最新文档）
from google.adk.agents import LlmAgent

# 1. 组件定义：专职探索智能体
generator = LlmAgent(
    name="hypothesis_generator",
    instruction="基于文献上下文提出可验证的研究假设，标注新颖性与依据。",
    tools=[literature_search])          # TODO(user): 文献检索工具
reviewer = LlmAgent(
    name="hypothesis_reviewer",
    instruction="以同行评审标准评估假设的正确性、新颖性与质量，输出评分 JSON。")

# 2. 模式接线：主管智能体以 sub_agents 编排 generator → reviewer 循环
supervisor = LlmAgent(
    name="research_supervisor",
    instruction="协调假设生成与评审循环，汇总高排名假设供人类科学家裁决。",
    sub_agents=[generator, reviewer])

# 3. 执行入口：Runner 逐会话推进研究目标
# 4. 观测与护栏：假设池与评审轨迹入 Session；危险研究目标由安全审查拦截
```

## 6. 反模式与坑点

1. **追求完全自动化取代人类** [F]：书中强调增强而非取代——仅开放文献会漏付费墙成果、负面结果获取有限、受 LLM 幻觉限制；人类的构思与批判性分析不可省。
2. **假设不经外部验证直接采信** [F]：系统输出仍是假设——书中以体外实验、类器官实验与专家评审做端到端验证；跳过验证会把幻觉当发现。
3. **探索无预算上限** [E]：测试时计算扩展可持续提升质量，但迭代必须设终止条件与预算——无边界迭代是成本反模式。
4. **生成与评审同源无对抗** [E]：生成与评审同视角会退化为自我确认；三评审机制的价值正在视角多元（洞察/影响力/新颖性各有侧重）[F]。
5. **安全审查缺位** [F]：研究目标与假设均须安全审查，防不安全/不道德研究；未经对抗性测试就上线的探索系统风险不可控。

## 7. 与其他模式的组合

- **探索 + 多智能体（10）**：主载体——生成/反思/排序/进化/邻近/元评审专职智能体 + 主管协调 [F]。
- **探索 + 反思（07）**：反思智能体即同行评审——评估假设的正确性/新颖性/质量 [F]。
- **探索 + RAG（06）**：文献综述阶段多源检索与综合，为假设生成提供知识基础 [F]。
- **探索 + HITL（15）**：「科学家在环」——人类反馈、贡献观点、引导探索方向 [F]。
- **探索 + 护栏（18）**：研究目标与生成假设双层安全审查，拒绝危险输入 [F]。
- **探索 + 评估（19）**：Elo 排名与 GPQA 基准即评估模式的内建应用；三评审即 LLM 评审的具体化 [F]。

## 8. 评估指标

- **结果导向**：假设验证通过率（经实验或专家验证成立的比例——书中端到端案例口径）；基准准确率（GPQA 钻石集 top-1 78.4%）[F]；专家评出的新颖性与影响力 [F]。
- **过程导向**：Elo 排名与质量的收敛一致性；每轮迭代质量提升幅度（扩展的边际收益）；算力消耗与预算达成率 [E]。
- **轨迹审查**：循环是否真实执行（评审先于进化、元评审反馈入下轮）；安全审查触发与拒绝记录 [E]。
