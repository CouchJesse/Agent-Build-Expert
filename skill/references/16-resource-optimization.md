# 16 · 资源感知优化（Resource-Aware Optimization）

> 溯源：《智能体设计模式》第 16 章 资源感知优化 · 板块：可靠性与工程化
> 证据基准：本节内容除特别标注外，均为书中原文确认 [F]。

## 1. 模式定义

资源感知优化使智能体在运行过程中动态监控和管理计算、时间与财务资源，在指定资源预算内实现目标或优化效率 [F]。它与仅关注动作序列的简单规划不同：智能体在执行动作时同步做出资源决策——在更准确但昂贵的模型与更快、低成本的模型之间选择，或权衡是否分配更多算力换取更精细的响应。关键策略还包括回退机制：当首选模型因过载或限流不可用时，系统自动切换到备选或更经济的模型，保证服务连续性而非完全失败 [F]。

## 2. 工作机制

标准实现是「路由智能体 + 批判智能体 + 回退链」的协作结构 [F]：

```
输入: 用户请求 + 资源约束（预算 / 时延 / 能耗）
  ↓
[分类] 路由智能体评估请求复杂度
       （简单指标如查询长度，或 LLM/ML 判别任务类型）
  ↓
[分流] 简单问题 → 经济模型；复杂推理 → 高阶模型；
       需实时信息 → 触发外部搜索后再作答
  ↓
[评审] 批判智能体评估响应质量，识别不合理分流
       （如简单问题误用高阶模型），反馈修正路由逻辑
  ↓
[回退] 首选模型过载 / 限流 / 内容过滤失败 →
       按优先级列表自动切换备选模型
  ↓
输出: 预算与时延约束内、质量达标的响应
```

路由质量可进一步优化：提示工程引导路由决策、在「问题-最佳模型」数据集上微调路由模型，实现响应质量与成本的动态平衡 [F]。

**超越动态模型切换的技术谱系** [F]——动态模型切换只是资源优化的一种，完整谱系包括：

| 技术 | 要点 |
|---|---|
| 动态模型切换 | 按任务复杂度战略性选择大型或轻量 LLM：简单问题用经济模型，复杂问题用高阶模型 |
| 自适应工具选择 | 综合考虑 API 成本、延迟与执行时间，从工具库中选取最适合的工具 |
| 上下文剪枝与摘要 | 智能摘要并选择性保留历史关键信息，削减处理 token 与推理成本 |
| 主动资源预测 | 预测未来工作负载与系统需求，提前分配资源、防止瓶颈 |
| 成本敏感探索 | 多智能体系统中优化通信与计算成本，最小化整体资源消耗 |
| 能效部署 | 面向边缘设备等受限环境优化能耗，延长运行时间 |
| 并行与分布式计算感知 | 将计算分散到多机多处理器，提升算力与吞吐量 |
| 学习型资源分配策略 | 依据反馈与性能指标持续优化资源分配，实现持续效率提升 |
| 优雅降级与回退机制 | 资源极度受限时维持基本功能：性能降级但系统持续运行 |

## 3. 适用场景与不适用场景

| 适用 ✅ | 不适用 ❌ |
|---|---|
| 成本优化的 LLM 使用：复杂任务用大型昂贵模型，简单查询用小型经济模型 [F] | 单一模型且调用量极小的原型：路由层的复杂度大于节省 [E] |
| 延迟敏感操作：实时系统选择更快但不够全面的推理路径，确保及时响应 [F] | 质量恒定优先且预算不受限的场景：无需在质量与成本间权衡 [E] |
| 服务可靠性回退：主模型不可用时自动切换备选，优雅降级不中断 [F] | 任务类型单一稳定：分类路由几乎总给出相同结果 [E] |
| 能效优化：边缘设备 / 电池受限环境节省电量 [F] | |
| 数据使用管理：选择摘要数据而非完整下载，节省带宽与存储 [F] | |
| 自适应任务分配：多智能体按算力负载与可用时间自我分配任务 [F] | |

## 4. 选型决策要点

1. **书中经验法则** [F]：需严格控制 API 调用成本或算力、构建延迟敏感应用、部署在电池有限的边缘设备、需程序化平衡响应质量与成本、或管理多步骤复杂工作流时，推荐采用本模式。
2. **与路由（02）的边界**：路由模式解决「请求往哪去」的通用分流；资源感知优化以成本、时延、能耗为显式优化目标，路由智能体只是其标准实现载体 [E]。
3. **分类器成本要计入**：路由判别自身消耗 token 与延迟；应从简单规则起步，复杂度证明必要时再升级为 LLM/ML 判别 [E]。
4. **回退链必须显式设计**：依赖单一模型端点等于把可用性押注在外部服务上；应配置模型优先级列表，故障时顺序切换直到成功或列表耗尽 [F]。
5. **分层架构的分工** [F]：复杂规划（理解复杂请求、拆解多步行程、逻辑决策）交给高能力模型；简单重复的工具调用（查价格、查可用性）交给经济模型——既保证逻辑严密又节约资源。

## 5. 多框架代码模板

### 5.1 框架无关伪代码

```text
router_agent = Agent(
    role = "资源感知路由器",
    instructions = """
      对每个请求：
      1. CLASSIFY  评估复杂度（规则指标 / LLM 判别任务类型）
      2. ROUTE     简单 → 经济模型；复杂推理 → 高阶模型；
                   需实时信息 → 触发搜索工具后再作答
      3. FALLBACK  首选模型过载/限流/不可用 → 按优先级列表
                   顺序切换备选模型，直到成功或列表耗尽
      4. AUDIT     记录实际使用模型与成本，供批判智能体
                   复核分流是否合理
    """
)
```

### 5.2 OpenAI（书中第 16 章实码 [F]，改写为骨架）

```python
# OpenAI SDK（版本需核对最新文档）
# 1. 组件定义：分类器 + 模型档位（密钥从环境变量读取）
import os, json
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def classify_prompt(prompt: str) -> dict:
    """问题分类：simple / reasoning / internet_search 三类。"""
    system_message = {"role": "system", "content": (
        "你是分类器，只返回 simple / reasoning / internet_search 之一，"
        '仅用 JSON 回复：{ "classification": "simple" }')}
    response = client.chat.completions.create(
        model="gpt-4o",  # TODO(user): 分类环节可换更小模型降本
        messages=[system_message, {"role": "user", "content": prompt}])
    return json.loads(response.choices[0].message.content)

# 2. 模式接线：按分类选择「性价比最优」的模型档位
def generate_response(prompt: str, classification: str, search_results=None):
    if classification == "simple":
        model = "gpt-4o-mini"   # 简单事实问题 → 经济模型
    elif classification == "reasoning":
        model = "o4-mini"       # 多步推理 → 推理增强模型
    else:
        model = "gpt-4o"        # 需实时信息 → 检索结果作为上下文
        prompt = f"请用以下网页结果回答问题：\n{search_results}\n\n问题：{prompt}"
    response = client.chat.completions.create(
        model=model, messages=[{"role": "user", "content": prompt}])
    return response.choices[0].message.content, model

# 3. 执行入口：综合路由
def handle_prompt(prompt: str) -> dict:
    classification = classify_prompt(prompt)["classification"]
    search_results = None
    if classification == "internet_search":
        search_results = web_search(prompt)  # TODO(user): 接入搜索 API，密钥从环境变量读取
    answer, model = generate_response(prompt, classification, search_results)
    return {"classification": classification, "model": model, "response": answer}

# 4. 观测与护栏：记录每条请求的分类与实际使用模型，审计成本分布与分流合理性
# SAFETY: 模型调用产生真实费用，建议设置每日用量上限并监控告警
```

### 5.3 OpenRouter（书中第 16 章实码 [F]，改写为骨架）

```python
# OpenRouter API（版本需核对最新文档）— 统一接口接入数百种模型
import os
import requests

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")  # 密钥从环境变量读取

# 1. 组件定义：统一 chat completions 端点
url = "https://openrouter.ai/api/v1/chat/completions"

# 2. 模式接线 A —— 自动模型选择：平台按问题内容自动选取最优模型，
#    响应元数据返回实际处理模型的标识
auto_payload = {"model": "openrouter/auto",
                "messages": [{"role": "user", "content": "TODO(user): 用户问题"}]}

# 模式接线 B —— 顺序模型回退：显式指定模型优先级列表，首选模型故障
# （服务不可用 / 限流 / 内容过滤）时自动切换下一个，直到成功或列表耗尽
fallback_payload = {
    "models": ["vendor-a/model-primary", "vendor-b/model-fallback"],  # TODO(user): 按需配置
    "messages": [{"role": "user", "content": "TODO(user): 用户问题"}]}

# 3. 执行入口
response = requests.post(
    url, headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
    json=fallback_payload)

# 4. 观测与护栏：最终费用与模型标识以「实际完成请求的模型」为准，
#    须解析响应元数据记账，避免按首选模型估算造成成本偏差
```

### 5.4 Google ADK（书中第 16 章实码 [F]，改写为骨架）

```python
# google-adk（版本需核对最新文档）
from google.adk.agents import Agent, BaseAgent
from google.adk.events import Event
from google.adk.agents.invocation_context import InvocationContext

# 1. 组件定义：不同成本档位的两个智能体（模型名按实际替换）
pro_agent = Agent(
    name="my_pro_agent", model="gemini-2.5-pro",
    description="复杂查询的高能力 Agent。",
    instruction="你是复杂问题解决的专家助手。")
flash_agent = Agent(
    name="my_flash_agent", model="gemini-2.5-flash",
    description="简单问题的快速高效 Agent。",
    instruction="你是简单问题的快速助手。")

# 2. 模式接线：路由智能体按复杂度指标分流（书中示例：查询词数阈值）
class QueryRouterAgent(BaseAgent):
    name: str = "QueryRouter"
    description: str = "根据复杂度将用户查询路由到合适的 Agent。"

    async def _run_async_impl(self, context: InvocationContext):
        user_query = context.current_message.text
        query_length = len(user_query.split())  # 简单指标：词数
        if query_length < 20:                   # TODO(user): 阈值按业务调优
            response = await flash_agent.run_async(context.current_message)
        else:
            response = await pro_agent.run_async(context.current_message)
        yield Event(author=self.name, content=f"处理结果：{response}")

# 3. 执行入口：ADK 编排支持 LLM 驱动的动态路由与多智能体扩展
# 4. 观测与护栏：记录每次分流依据；批判智能体复核响应质量与分流
#    合理性，反馈修正路由逻辑（组合第 07 章反思）
```

## 6. 反模式与坑点

1. **全链路单档模型** [F]：所有任务都用最优模型并不高效——LLM 应用常常昂贵且缓慢，须在输出质量与资源消耗间权衡；缺乏动态管理策略的系统无法适应任务复杂度变化与预算、性能约束。
2. **路由指标过于粗糙** [F]：仅凭查询长度等简单指标分流易误判；更稳健的做法是用 LLM/ML 分析查询复杂度（事实回忆类走经济模型、深度分析类走高阶模型），并以提示工程和微调提升路由质量。
3. **无回退的单一依赖** [F]：首选模型因过载、限流不可用时系统整体失败。应设计模型优先级列表与自动切换，实现优雅降级而非完全失败。
4. **分类错误无纠偏通道** [F]：分流器误判（简单问题用了高阶模型、复杂问题用了经济模型）若无人复核，成本漏洞会持续存在——批判智能体的质量反馈正是路由逻辑的纠偏机制。
5. **忽略隐性资源消耗** [E]：路由判别、搜索前置、上下文膨胀都消耗预算；只盯模型单价而不审计端到端 token 成本，优化会失真。

## 7. 与其他模式的组合

- **资源优化（16）+ 路由（02）**：路由智能体是本模式的标准载体，分类-分流逻辑即路由模式的资源版实例 [F]。
- **资源优化（16）+ 反思（07）**：批判智能体评估响应质量、识别不合理分流，其反馈还可用于强化学习或微调，持续优化路由逻辑 [F]。
- **资源优化（16）+ 多智能体（10）**：分层架构中规划者用高能力模型、工具执行者用经济模型；多智能体间还可做成本敏感探索与自适应任务分配 [F]。
- **资源优化（16）+ 异常恢复（14）**：顺序模型回退本质是模型层的故障转移，与异常恢复模式的检测-回退-重试闭环互补 [E]。
- **资源优化（16）+ 评估（19）**：内置评估系统性评测分流后的智能体表现，为路由策略优化提供数据依据 [F]。
- **资源优化（16）+ 记忆管理（08）**：上下文剪枝与摘要既是资源优化技术谱系的一项，也是记忆管理的压缩策略，二者可共用一套裁剪机制 [E]。

## 8. 评估指标

- **结果导向**：响应质量保持度（分流后答案准确率不劣于全高阶模型基线）；单位任务成本（每千次请求的 token 费用降幅）[E]。
- **过程导向**：模型档位分布（各档位调用占比是否与请求复杂度分布匹配）；回退触发率与回退后成功率（回退频繁说明上游不稳定或配置过激进）[E]。
- **轨迹审查**：抽样审计「分类 → 选模 → 实际模型」链路，统计误分流率——书中将「简单问题用高阶模型、复杂问题用经济模型」两类误分流列为批判智能体的识别对象 [F]。
