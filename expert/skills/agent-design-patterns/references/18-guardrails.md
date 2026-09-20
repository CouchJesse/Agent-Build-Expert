# 18 · 护栏与安全（Guardrails）

> 溯源：《智能体设计模式》第 18 章 护栏与安全模式 · 板块：可靠性与工程化
> 证据基准：本节内容除特别标注外，均为书中原文确认 [F]。

## 1. 模式定义

护栏（Guardrails），也称安全模式，是确保智能体安全、合规、按预期运行的关键机制，在智能体日益自主并集成到关键系统的背景下不可或缺。它作为保护层，引导智能体的行为和输出，防止有害、偏见、无关或其他不良响应——主要目标不是限制智能体能力，而是确保其运行稳健、可信且有益。没有护栏，AI 系统可能变得不可控、不可预测，甚至带来危险。

## 2. 工作机制

护栏是**多层防御**：书中明确「多种护栏技术组合最为稳健」。

```
用户输入
  ↓
[输入验证/清洗] 外部内容审核 API 检测不当提示；越狱（Jailbreak）指令识别；
               Pydantic 校验结构化输入
  ↓
[行为约束] 提示级约束与智能体配置：角色/目标/背景故事引导行为，
           专用智能体聚焦范围，限制敏感话题
  ↓
[工具使用限制] 工具调用前回调校验参数与权限（最小权限原则）
  ↓
主智能体执行
  ↓
[输出过滤/后处理] 分析生成结果是否有毒或偏见；展示前清洗，防恶意代码执行
  ↓
[人类介入（HITL）] 护栏触发或关键决策时，人工审核输出或干预流程
```

三个关键设计点：

1. **轻量模型作快筛防线** [F]：用计算资源消耗低的快速模型（如 Flash 级）对主模型的输入或输出预筛查政策违规，兼顾成本与延迟。
2. **政策护栏 + 技术护栏双层** [F]：政策护栏由 LLM 按提示词逐条评估合规性（覆盖越狱、禁止内容、越界话题、品牌与竞争信息）；技术护栏用 Pydantic 校验输出结构，二者缺一不可。
3. **可观测性与弹性是护栏地基** [F]：记录所有行为、工具调用与输入输出，收集延迟、成功率、错误指标满足审计；错误处理（try-except、指数退避重试）保证护栏自身不成为新故障点。

工程化可靠智能体（书中将护栏扩展为工程原则）[F]：检查点与回滚（类似数据库事务的容错核心）；模块化与关注点分离（专用智能体分工、故障隔离）；结构化日志实现可观测性；最小权限原则（只授予完成任务所需的最小权限，压缩错误或攻击的影响范围）。

## 3. 适用场景与不适用场景

| 适用 ✅ | 不适用 ❌ |
|---|---|
| 客服机器人：防冒犯语言、有害建议（医疗/法律）、跑题回复 [F] | 封闭沙箱离线原型：无真实用户与外部影响 [E] |
| 内容生成系统：合规与伦理约束，后处理过滤问题短语 [F] | 确定性代码路径：常规输入校验即可 [E] |
| 教育/法律研究/招聘 HR：防错误答案、越界建议、歧视性语言 [F] | 低风险高吞吐批处理：护栏延迟代价大于收益 [E] |
| 社交媒体内容审核、科研助手（防伪造数据）[F] | 一次性演示 Demo [E] |

## 4. 选型决策要点

1. **经验法则** [F]：只要输出可能影响用户、系统或业务声誉就应实施护栏；面向用户的自主智能体、内容生成平台、金融/医疗/法律系统必须部署。
2. **风险评估前置** [F]：实施前针对功能、领域和部署环境做风险评估（Vertex AI 实践），再定布防层次。
3. **多层组合** [F]：允许/拒绝列表、提示词护栏、工具回调校验、外部审核 API 与 HITL 组合布防，而非单点防御。
4. **护栏执行者也是智能体** [F]：LLM 可被指令为安全护栏，有效防越狱；用快速低成本模型、温度 0 保证判定一致。
5. **与 HITL（15）的分工** [F]：常规违规护栏自动拦截；关键决策或护栏触发问题时转人工——护栏是自动防线，人类是最终裁决。

## 5. 多框架代码模板

### 5.1 框架无关伪代码

```text
guard_agent = Agent(          # 轻量快筛模型，temperature=0
    role   = "内容政策执行者",
    policy = "越狱 / 禁止内容 / 越界话题 / 品牌与竞争信息，逐条评估",
    output = {compliance_status, evaluation_summary, triggered_policies}
)
technical_guard = pydantic_validate(output)    # 技术护栏：结构校验兜底

on_input(user_msg):
    ok, verdict = guard_agent(user_msg)
    if not ok: return refuse(verdict)          # 阻断，不进主智能体
    reply = main_agent(user_msg)
    return postprocess(reply)                  # 输出侧过滤与清洗
# SAFETY: 高风险动作（外发/交易/删除）须在工具层回调校验 + 人工确认后执行
```

### 5.2 CrewAI（源自书中第 18 章实码 [F]，改写为骨架）

```python
# CrewAI（书中第 18 章示例；版本需核对最新文档）
import os
from crewai import Agent, Task, Crew, Process, LLM
from pydantic import BaseModel, Field

# 1. 组件定义：政策护栏的结构化输出模型（技术护栏）
class PolicyEvaluation(BaseModel):
    compliance_status: str = Field(description="'compliant' 或 'non-compliant'")
    evaluation_summary: str = Field(description="合规状态简要说明")
    triggered_policies: list = Field(description="触发的政策指令列表")

def validate_policy_evaluation(output) -> tuple:
    """校验 LLM 原始输出是否符合模型：剥离 markdown 代码块、
    json 解析、Pydantic 校验 + 逻辑检查，失败返回 (False, 错误信息)。"""
    # TODO(user): 兼容 TaskOutput / str / PolicyEvaluation 三种输入；
    #              合规状态枚举检查、空摘要检查、列表类型检查
    ...

# 2. 模式接线：专用政策执行智能体（快速低成本模型，温度 0）
policy_enforcer_agent = Agent(
    role='AI 内容政策执行者',
    goal='严格筛查用户输入，确保符合预设安全与相关性政策。',
    backstory='公正严格，维护主 AI 系统的安全与完整性。',
    allow_delegation=False,
    llm=LLM(model="gemini/gemini-2.0-flash", temperature=0.0,
            api_key=os.environ.get("GOOGLE_API_KEY")),  # 密钥环境变量读取
)
evaluate_input_task = Task(
    description="<安全政策提示词>（覆盖四类政策）+ 待审核输入 {{user_input}}",
    expected_output="符合 PolicyEvaluation 模型的 JSON 对象",
    agent=policy_enforcer_agent,
    guardrail=validate_policy_evaluation,   # CrewAI 原生护栏挂点
    output_pydantic=PolicyEvaluation,
)

# 3. 执行入口
crew = Crew(agents=[policy_enforcer_agent], tasks=[evaluate_input_task],
            process=Process.sequential)
result = crew.kickoff(inputs={'user_input': user_input})
evaluation = result.tasks_output[-1].pydantic   # 最终校验后的结构化结果

# 4. 观测与护栏：non-compliant 即阻断主 AI 处理；
#   全程 logging 留痕（输入/判定/触发政策），满足可追溯性审计
```

### 5.3 Google ADK / Vertex AI（源自书中第 18 章实码 [F]，改写为骨架）

```python
# google-adk（书中 Vertex AI 示例；版本需核对最新文档）
from google.adk.agents import Agent
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from typing import Optional, Dict, Any

# 1. 组件定义：工具调用前参数校验回调
def validate_tool_params(tool: BaseTool, args: Dict[str, Any],
                         tool_context: ToolContext) -> Optional[Dict]:
    """工具执行前校验：参数身份必须与会话状态一致（防越权）。"""
    expected_user_id = tool_context.state.get("session_user_id")
    actual_user_id = args.get("user_id_param")
    if actual_user_id and actual_user_id != expected_user_id:
        # SAFETY: 身份不匹配 → 返回 dict 阻止工具执行；返回 None 才放行
        return {"status": "error",
                "error_message": "工具调用被阻止：用户 ID 校验未通过。"}
    return None   # 校验通过，允许工具继续执行

# 2. 模式接线：回调挂到根智能体，所有工具调用都经过安全校验
root_agent = Agent(
    model='gemini-2.0-flash-exp',   # TODO(user): 按需更换模型
    name='root_agent',
    instruction="你是负责校验工具调用的根智能体。",
    before_tool_callback=validate_tool_params,
    tools=[],  # TODO(user): 工具函数列表
)
# 3. 执行入口：Runner 逐会话推进
# 4. 观测与护栏（书中配套实践）：隔离代码执行环境；
#   限制活动在安全网络边界（如 VPC Service Controls）；输出展示前清洗
```

### 5.4 LangChain / LangGraph（书中未提供该框架示例，工程实践推断 [E]）

```python
# LangGraph（工程实践推断 [E]，需核对最新文档）
# 1. 组件定义：输入护栏节点（快筛模型）+ 主智能体节点 + 输出过滤节点
def input_guard(state):
    verdict = guard_llm.invoke(state["user_input"])  # TODO(user): 政策提示词评估
    return {"blocked": verdict.non_compliant, "reason": verdict.summary}

# 2. 模式接线：input_guard →(合规) main_agent → output_guard
#                          └→(不合规) 拒绝并说明触发政策
# 3. 执行入口：graph.add_conditional_edges("input_guard", route,
#             {"blocked": END, "ok": "main_agent"})
# 4. 观测与护栏：guard 判定写入结构化日志，供评估模式（19）统计拦截率
```

## 6. 反模式与坑点

1. **单点防御** [F]：只靠一层（如仅提示词或仅关键词列表）；应输入、行为、工具、输出、人工分层设防。
2. **用主模型自查** [E]：书中推荐另用低成本快速模型作额外防线；主模型自查既贵又易被同一盲区欺骗。
3. **不确定时的默认口径未显式声明** [F]：书中政策「存疑默认合规」是低风险场景的有意设计；高风险业务应反向收紧——判定口径必须写进政策，而非留给模型临场发挥 [E]。
4. **护栏不可观测** [F]：无日志无指标（延迟/成功率/错误）就无法审计调优；书中将可观测性列为合规必要条件。
5. **只挡输入不挡输出与工具** [F]：输入清洗、输出后处理、工具回调三层都要设防；生成内容展示前应清洗，防恶意代码在浏览器执行。

## 7. 与其他模式的组合

- **护栏 + HITL（15）**：护栏检测到问题或关键决策时集成人工介入，审核输出或干预流程 [F]。
- **护栏 + 工具使用（05）**：工具使用限制与调用前回调校验是工具层的护栏形态 [F]。
- **护栏 + 评估与监控（19）**：护栏拦截率与误拦率是核心观测对象；护栏需持续监控和优化，适应风险变化 [F]。
- **护栏 + 异常恢复（14）**：护栏拦截后不是简单拒绝——错误处理与弹性（重试、退避、清晰报错）把失败转为可恢复流程 [F]。
- **护栏 + 多智能体（10）**：模块化专用智能体（检索/分析/沟通分工）实现故障隔离与最小权限，是工程化可靠智能体的架构基础 [F]。

## 8. 评估指标

（按第 19 章结果导向/过程导向口径）

- **结果导向**：违规输出逃逸率（上线后发现的违规数/总交互数）；攻击拦截率（越狱样本被拦截比例）[E]。
- **过程导向**：拦截率与误拦率（合规输入被误阻比例，过高伤可用性）；护栏延迟增量（快筛的额外时延）；触发政策分布（指导政策调优）[E]。
- **轨迹审查**：每次拦截留痕（输入、判定、触发政策、摘要）满足可追溯性与审计要求 [F]。
