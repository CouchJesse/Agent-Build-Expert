# 19 · 评估与监控（Evaluation and Monitoring）

> 溯源：《智能体设计模式》第 19 章 评估与监控 · 板块：可靠性与工程化
> 证据基准：本节内容除特别标注外，均为书中原文确认 [F]。

## 1. 模式定义

评估与监控模式对智能体的有效性、效率与合规性做持续（通常是外部）的系统性测量，涵盖指标定义、反馈回路建立和报告系统实现，确保智能体在实际环境中的表现符合预期。核心矛盾在于：智能体行为概率且非确定，传统软件测试只能判通过/失败，无法保障动态环境中的持续可靠性——评估必须超越单次准确率检查，成为持续、多维度的测量体系。

## 2. 工作机制

```
智能体运行（生产 / 测试环境）
  ↓
[指标采集] 准确率 · 延迟 · Token 用量 · 资源消耗 · 轨迹日志
  ↓
[评估分析] 结果导向 / 过程导向 / 人工评估（含 LLM 评审规模化替代）
  ↓
[反馈回路] 评估结果 → 告警 / A-B 决策 / 回滚 / 提示词与策略优化
  ↓
[报告系统] 审计报告 · KPI · 漂移与异常检测
```

三类评估方法（书中口径，FAQ 整理）[F]：

| 方法 | 关注点 | 优劣（书中对照表）[F] |
|---|---|---|
| 结果导向 | 是否成功实现最终目标（如订票是否正确完成），最重要的衡量标准 | 自动化指标可扩展、高效、客观，但难全面覆盖智能体能力 |
| 过程导向 | 流程是否高效合理：工具使用与计划遵循，助定位失败原因 | 轨迹评估能发现错误与低效，但需先定义理想路径 |
| 人工评估 | 人类按有用性、准确性、连贯性打分（1–5 分），面向用户的应用尤为重要 | 能捕捉细微行为，但难规模化、成本高、主观；LLM 评审（LLM-as-a-Judge）一致高效可扩展，但可能忽略中间步骤、受限于评审模型能力 |

**智能体轨迹（Agent Trajectory）** [F]：智能体执行任务的完整日志——所有思考、行动（工具调用）和观察。轨迹评估将实际步骤与理想路径对比，可用精确/顺序/任意顺序匹配、查准率、查全率、单工具使用等指标。多智能体还需评估协作维度：参数传递、计划遵循、选对智能体、新增智能体的整体收益 [F]。

**评估资产两种形态** [F]：测试文件（JSON，单会话多轮交互，含工具轨迹与参考答案，适合开发阶段单元测试，test_config.json 定义标准）；evalset 文件（多个 eval 会话，适合集成测试）。

**进阶形态：从智能体到「承包商」** [F]：高风险任务用正式「合同」（明确交付物、数据源、范围、成本、时限，结果可客观验证）替代简短指令；四支柱：正式合同、动态协商反馈、质量导向迭代执行、分层分解与子合同。

## 3. 适用场景与不适用场景

| 适用 ✅ | 不适用 ❌ |
|---|---|
| 生产环境性能追踪：准确率/延迟/资源消耗 [F] | 一次性离线脚本：无持续运行对象 [E] |
| A/B 测试：并行比较版本或策略选优 [F] | 确定性代码路径：常规单元测试足够 [E] |
| 合规与安全审计：审计报告、KPI、告警 [F] | 早期原型：评估口径未定先人工试用 [E] |
| 漂移检测、异常行为检测、学习进度评估 [F] | |

## 4. 选型决策要点

1. **经验法则** [F]：部署在生产环境、需实时性能与可靠性时采用；需系统比较版本或模型驱动优化时使用；合规/安全/伦理高要求领域适用；可能出现漂移或需评估复杂行为（轨迹、主观输出）时推荐。
2. **从关键用例切入** [F]：评估框架涉及模型性能、用户交互、伦理与社会效应，复杂易失焦；落地时聚焦关键用例。
3. **按可扩展性选方法** [F]：人工评估捕捉细微行为但难规模化；自动化指标客观高效但覆盖有限；主观质量用 LLM-as-a-Judge 按 rubric 自动评审。
4. **严格匹配只做冒烟测试** [F]：字符串严格相等无法识别语义等价；进阶用相似度（Levenshtein/Jaccard）、嵌入余弦、LLM 评审、RAG 指标。
5. **非确定性测试策略** [F]：不逐字断言，测关键要素——最终响应是否含特定信息、是否成功调用工具并传对参数；用模拟工具在专用测试环境实现。

## 5. 多框架代码模板

### 5.1 框架无关伪代码

```text
monitor = {accuracy: [], latency: [], tokens_in: 0, tokens_out: 0, traces: []}

on_interaction(user_input, agent):
    t0 = now()
    reply, trace = agent.run(user_input)
    monitor.latency  += now() - t0
    monitor.tokens   += count_tokens(user_input, reply)   # 成本管理
    monitor.accuracy.push(score(reply, ground_truth))     # 结果导向
    monitor.traces.push(trace)                            # 过程导向：轨迹留痕
    if drift_detected(monitor): alert("概念漂移，需重评或回滚")

judge = LLM(rubric="清晰/中立/相关/完整/适配 各1-5分 + JSON理由")  # 人工评估的规模化替代
```

### 5.2 自动化指标（源自书中第 19 章实码 [F]，改写为骨架）

```python
# 纯 Python（书中第 19 章示例）
# 1. 组件定义：结果导向评分 + 过程导向 Token 监控
def evaluate_response_accuracy(agent_output: str, expected_output: str) -> float:
    """严格匹配准确率——仅冒烟级，无法识别语义等价。"""
    return 1.0 if agent_output.strip().lower() == expected_output.strip().lower() else 0.0
    # 进阶：Levenshtein / Jaccard、嵌入余弦相似度、LLM 评审、RAG 指标

class LLMInteractionMonitor:
    """LLM 交互 Token 用量追踪——服务成本管理与资源优化。"""
    def __init__(self):
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    def record_interaction(self, prompt: str, response: str):
        input_tokens = len(prompt.split())    # TODO(user): 换用 LLM API 的 Token 计数器
        output_tokens = len(response.split())
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens

    def get_total_tokens(self):
        return self.total_input_tokens, self.total_output_tokens

# 2. 模式接线 / 3. 执行入口：每次交互后 record_interaction(...)，按需 get_total_tokens()
# 4. 观测与护栏：延迟与 Token 数据写入持久化存储——结构化 JSON 日志、
#   时序数据库或可观测性平台，支撑趋势分析与成本报表
```

### 5.3 LLM-as-a-Judge（源自书中第 19 章实码 [F]，改写为骨架）

```python
# google-generativeai（书中第 19 章示例：Gemini Flash 级模型做评审）
import os, json, logging
import google.generativeai as genai

genai.configure(api_key=os.environ["GOOGLE_API_KEY"])   # 密钥从环境变量读取

# 1. 组件定义：评审标准（rubric）——预设标准是 LLM 评审可复现的关键
JUDGE_RUBRIC = """
你是严谨的评审专家。针对以下标准分别打分（1-5）并给出理由与具体反馈：
清晰与精确 / 中立与无偏 / 相关性与聚焦 / 完整性 / 受众适配性。
输出 JSON：overall_score、rationale、detailed_feedback、concerns、recommended_action。
"""

class LLMJudge:
    """按 rubric 自动化评估主观质量（如'有用性'），可规模化。"""
    def __init__(self, model_name="gemini-1.5-flash-latest", temperature=0.2):
        self.model = genai.GenerativeModel(model_name)

    def judge(self, content: str):
        try:
            response = self.model.generate_content(
                f"{JUDGE_RUBRIC}\n---\n待评估内容：\n{content}",
                generation_config=genai.types.GenerationConfig(
                    temperature=self.temperature,
                    response_mime_type="application/json"))
            if not response.parts:    # 空响应/被安全策略拦截时留痕
                logging.error(f"评审被拦截：{response.prompt_feedback.safety_ratings}")
                return None
            return json.loads(response.text)
        except Exception as e:
            logging.error(f"LLM 评审异常：{e}")
            return None

# 2. 模式接线 / 3. 执行入口：LLMJudge().judge(question) → 结构化评分
# 4. 观测与护栏：低分项的 concerns / recommended_action 进入反馈回路触发整改
```

### 5.4 Google ADK 评估（书中第 19 章口径 [F]，改写为骨架）

```python
# google-adk（书中第 19 章：WebUI / pytest / 命令行三种评估方式；需核对最新文档）
from google.adk.eval import AgentEvaluator

# 1. 组件定义：评估资产
#   测试文件 evals/my_agent.test.json —— 单会话多轮交互（用户请求 / 工具使用轨迹 /
#   中间响应 / 最终回复），适合开发阶段单元测试；test_config.json 定义评估标准
#   evalset 文件 evals/my_agent.evalset.json —— 多个 eval 会话，适合集成测试

# 2. 模式接线：pytest 集成，进入 CI/CD 测试流水线
def test_my_agent():
    AgentEvaluator.evaluate(
        agent_module="my_agent",                            # 被评估的智能体模块
        eval_dataset_file_path="evals/my_agent.test.json",  # 测试文件
    )

# 3. 执行入口（自动化）：
#   adk eval my_agent evals/my_agent.evalset.json          # 命令行批量评估
#   adk eval ... evals/my_agent.evalset.json eval_1,eval_2 # 逗号分隔指定具体 eval
#   adk web                                               # WebUI 交互式评估与数据集生成

# 4. 观测与护栏：评估状态与详细结果输出，用于构建验证与回归追踪
```

## 6. 反模式与坑点

1. **只测最终输出、不看轨迹** [F]：传统测试仅判通过/失败；智能体行为概率性，需定性分析输出与决策过程，轨迹是定位失败的关键。
2. **严格匹配当万能指标** [F]：字符串相等无法识别语义等价；按场景升级到相似度、嵌入、LLM 评审与 RAG 指标。
3. **LLM 评审当唯一裁判** [F]：LLM 评审可能忽略中间步骤、受限于模型能力；应与人工评估、自动化指标交叉验证。
4. **评估一次性完成** [F]：部署后会出现漂移、异常交互、目标偏离；必须建立反馈回路持续评估并触发告警。
5. **多智能体只评估个体** [F]：只测单个智能体会漏掉协作失败（参数传错、偏离计划、选错智能体）；需开发协作与沟通指标。
6. **指标采集了但不持久化** [F]：延迟等数据须记录到持久化存储（时序库/数仓/可观测平台）；内存态指标无法支撑漂移检测与审计。

## 7. 与其他模式的组合

- **评估 + 护栏（18）**：护栏拦截率/误拦率本身是评估对象；护栏需持续监控与优化 [F]。
- **评估 + 目标监控（13）**：目标监控（第 11 章）是内建自我测量，本章是外部持续测量，二者构成内外反馈回路 [F]。
- **评估 + 学习适应（09）**：跟踪学习曲线与泛化能力；评估结果驱动学习优化 [F]。
- **评估 + 多智能体（10）**：重点转向协作与整体表现——协作有效性、计划遵循、任务分配、新增智能体的边际收益 [F]。
- **评估 + HITL（15）**：人工评估即质量保障环节的人类介入；LLM 评审难裁决的边界样本升级人工终裁 [E]。

## 8. 评估指标（对评估系统自身的元指标）

- **结果导向**：评估召回——线上事故被测试集/监控提前发现的比例；A/B 决策正确率 [E]。
- **过程导向**：评估成本（评审 Token、人工工时）；评估周期；轨迹覆盖率（被评估交互占比）[E]。
- **轨迹审查**：漂移告警时效（下降发生到发现的时延）；审计报告完整性与可追溯性 [E]。
