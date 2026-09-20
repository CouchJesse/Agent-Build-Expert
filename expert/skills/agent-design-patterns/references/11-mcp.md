# 11 · 模型上下文协议（Model Context Protocol，MCP）

> 溯源：《智能体设计模式》第 10 章 模型上下文协议（MCP）· 板块：协作与通信
> 证据基准：本节内容除特别标注外，均为书中原文确认 [F]。

## 1. 模式定义

模型上下文协议（MCP）是一项开放标准，为大语言模型（LLM）与外部应用、数据源和工具的通信提供标准化接口，目标是建立任何合规工具都能被任何合规 LLM 访问的生态系统 [F]。它解决的核心问题是：没有标准化通信协议时，每次集成都需定制开发、难以复用，阻碍复杂 AI 系统的扩展与互联。

可以把 MCP 想象成一个通用适配器：任何 LLM 都能无缝连接任何外部系统、数据库或工具，无需为每种组合单独开发集成 [F]。MCP 本质上是一种「智能体接口」契约，其效果高度依赖底层 API 的设计质量——智能体并不能神奇地替代确定性流程，往往需要更强的确定性支持 [F]。

## 2. 工作机制

MCP 采用客户端-服务器架构 [F]：**服务器**暴露三类能力——资源（静态数据，如 PDF、数据库记录）、Prompt（引导 LLM 与资源或工具交互的模板）、工具（可执行功能，如发邮件、API 查询）；**客户端**（LLM 宿主应用或智能体本身）负责发现、连接并消费这些能力。

```text
组件: LLM（决策核心） ↔ MCP 客户端（发现/连接/通信） ↔ MCP 服务器（暴露工具/资源/Prompt） ↔ 第三方服务（最终执行终点）

交互流程 [F]:
1. 发现       客户端查询服务器能力 → 返回工具/资源/Prompt 清单
2. 请求构造   LLM 决定使用某工具，指定参数（收件人/主题/正文）
3. 客户端通信 客户端将请求按标准格式发送至服务器
4. 服务器执行 服务器认证客户端、校验请求，调用底层软件执行
5. 响应更新   返回标准化响应 → 客户端反馈给 LLM → 更新上下文，继续任务
```

关键工程考量 [F]：

- **传输机制**：本地用 JSON-RPC over STDIO（高效进程间交互）；远程用 StreamableHTTP 与 SSE（持久高效通信）。
- **可发现性**：客户端可动态查询服务器能力，实现「即时发现」，智能体无需重启即可适应新功能。
- **安全性**：任何暴露工具和数据的协议都需强安全措施，必须支持认证和授权，控制客户端访问权限与操作范围。
- **错误处理**：协议需定义错误（工具执行失败、服务器不可用、请求无效）如何反馈给 LLM，便于智能体理解并尝试替代方案。
- **部署形态**：服务器可本地（敏感数据、高性能）或远程（组织共享、扩展）部署；支持实时交互与批处理两种模式。

## 3. 适用场景与不适用场景

| 适用 ✅ | 不适用 ❌ |
|---|---|
| 数据库集成：自然语言驱动查询数据仓库、生成报告、更新记录 [F] | 固定少量函数即可满足：直接工具调用更简单（书中经验法则）[F] |
| 外部 API 交互：实时天气、行情、邮件、CRM 对接 [F] | [E] 一次性原型/演示：协议接入成本大于收益 |
| 自定义工具开发：FastMCP 快速开发并通过 MCP 服务器暴露专有功能 [F] | [E] 输入输出格式智能体无法理解的 API（如仅返回二进制文件）：应先改造数据层 |
| 复杂流程编排：组合多工具、多数据源的多步骤自动化 [F] | |
| 物联网设备控制 / 金融服务自动化（合规报告、市场分析）[F] | |
| 生成式媒体编排：图片/视频/语音/音乐生成服务接入 [F] | |

## 4. 选型决策要点

**MCP 与工具函数调用的对比**（书中核心选型依据）[F]：

| 特性 | 工具函数调用 | 模型上下文协议（MCP） |
|---|---|---|
| 标准化 | 专有、厂商定制，格式与实现各异 | 开放标准协议，促进 LLM 与工具间互操作 |
| 范围 | LLM 直接请求某个预定义函数 | 工具发现与通信的通用框架 |
| 架构 | LLM 与应用工具逻辑一对一交互 | 客户端-服务器架构，可连接多个 MCP 服务器 |
| 发现机制 | 需显式告知 LLM 可用工具 | 支持动态发现，客户端可查询服务器能力 |
| 复用性 | 工具集成与应用和 LLM 高度耦合 | 可复用、独立的服务器，任何应用可访问 |

1. **按规模与复用需求选型** [F]：函数调用适合简单场景（像给 AI 配一套专用扳手）；MCP 是复杂、互联 AI 系统不可或缺的标准化通信框架（像通用电源插座系统）。
2. **经验法则** [F]：构建复杂、可扩展或企业级智能体系统，需与多样化外部工具、数据源和 API 交互，尤其需要不同 LLM 与工具互操作、智能体动态发现新能力时，优先采用 MCP；仅需固定少量函数时直接工具调用即可。
3. **契约不等于效果** [F]：MCP 只是接口契约；底层 API 若不支持过滤、排序等确定性特性，或返回格式智能体无法解析，简单包装成 MCP 依然无效。
4. **实现复杂度** [F]：MCP 实现可能较复杂，可借助 FastMCP 等 SDK 简化开发流程。
5. **与工具使用（05）的关系** [E]：MCP 不是替代工具调用，而是工具调用在系统间的标准化封装——单一应用内的少量工具直接调用即可，跨应用复用才需要 MCP。

## 5. 多框架代码模板

### 5.1 框架无关伪代码

```text
# MCP 服务器侧
mcp_server = McpServer(name="my_service_server")
mcp_server.tool(name="query_data",
                params={"filter": str, "sort": str},   # 支持确定性过滤/排序 [F]
                returns="markdown 文本")                # 返回智能体可读格式 [F]

# MCP 客户端侧（智能体宿主）
client = McpClient()
capabilities = client.discover(server_url)    # 1. 发现：动态查询能力清单
result = client.call_tool("query_data",       # 2-4. 构造请求→标准格式通信→服务器执行
                          params={"filter": "high_priority", "sort": "created_at"})
agent_context.update(result)                  # 5. 响应更新上下文，继续后续任务
```

### 5.2 FastMCP：创建 MCP 服务器（源自书中第 10 章实码 [F]，改写为骨架）

```python
# FastMCP（示例性质，需核对最新文档；pip install fastmcp）
# 1. 组件定义：装饰器注册工具，类型提示与 docstring 自动生成接口规范
from fastmcp import FastMCP

mcp_server = FastMCP()

@mcp_server.tool
def greet(name: str) -> str:
    """生成个性化问候语。

    Args:
        name: 要问候的对象名称。
    """
    return f"你好，{name}！很高兴认识你。"  # TODO(user): 替换为实际业务工具

# 2. 模式接线：一个服务器可继续注册多个工具/资源/Prompt（按需追加）
# 3. 执行入口：以 HTTP 传输启动，供任意 MCP 客户端远程调用
if __name__ == "__main__":
    mcp_server.run(transport="http", host="127.0.0.1", port=8000)

# 4. 观测与护栏：生产部署应置于认证授权之后，限制可访问的客户端
```

### 5.3 Google ADK：智能体消费 MCP 服务器（源自书中第 10 章实码 [F]，改写为骨架）

```python
# google-adk（示例性质，需核对最新文档）
# 1. 组件定义：MCPToolset 桥接 MCP 服务器与 ADK 智能体
import os
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import (
    MCPToolset, StdioServerParameters, HttpServerParameters)

TARGET_FOLDER_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "mcp_managed_files")
os.makedirs(TARGET_FOLDER_PATH, exist_ok=True)

# 2. 模式接线（本地 STDIO 服务器）：经 npx 启动社区文件系统服务器
root_agent = LlmAgent(
    model="gemini-2.0-flash",  # TODO(user): 按需更换模型
    name="filesystem_assistant_agent",
    instruction=(f"帮助用户管理文件。你可以列出和读取文件。"
                 f"你的操作目录为：{TARGET_FOLDER_PATH}"),
    tools=[
        MCPToolset(
            connection_params=StdioServerParameters(
                command="npx",
                args=["-y", "@modelcontextprotocol/server-filesystem",
                      TARGET_FOLDER_PATH],
            ),
            # SAFETY: 文件写入属高风险操作，建议用 tool_filter 收敛为只读工具
            # tool_filter=["list_directory", "read_file"],
        )
    ],
)

# 2b. 远程 HTTP 服务器（如 5.2 的 FastMCP 服务）的消费方式：
http_agent = LlmAgent(
    model="gemini-2.0-flash",
    name="fastmcp_greeter_agent",
    instruction='你是友好的助手，可通过 "greet" 工具向人问好。',
    tools=[
        MCPToolset(
            connection_params=HttpServerParameters(url="http://localhost:8000"),
            tool_filter=["greet"],  # 限制暴露的工具范围
        )
    ],
)
# 3. 执行入口：在智能体目录的父目录执行 `adk web`，于 Web UI 中选择智能体交互
# 4. 观测与护栏：tool_filter 限制工具暴露；服务器密钥经 env 参数注入，不硬编码
```

### 5.4 LangChain / LangGraph（书中第 10 章未提供，以下为工程实践推断 [E]）

```python
# LangChain langchain-mcp-adapters（示例性质，需核对最新文档）
# 1. 组件定义：多服务器 MCP 客户端
import os
from langchain_mcp_adapters.client import MultiServerMCPClient

client = MultiServerMCPClient({
    "my_local_server": {                        # 本地 STDIO 服务器
        "transport": "stdio",
        "command": "python3",
        "args": ["./mcp_server.py"],            # TODO(user): 替换为实际服务器脚本
        "env": {"MY_SERVICE_TOKEN": os.environ.get("MY_SERVICE_TOKEN", "")},
    },
    "my_remote_server": {                       # 远程 HTTP 服务器
        "transport": "http",
        "url": "https://api.example.com/mcp",
    },
})

# 2. 模式接线：发现工具并转换为 LangChain 工具
# tools = await client.get_tools()
# 3. 执行入口：tools 传入 create_react_agent 或 StateGraph 节点
# 4. 观测与护栏：按工具名白名单过滤后再交给智能体，防止工具过载
```

## 6. 反模式与坑点

1. **直接包装传统 API 不做优化** [F]：如工单 API 只能逐条获取详情，智能体汇总高优先级工单时既慢又不准；底层 API 应支持过滤、排序等确定性特性。
2. **数据格式智能体无法理解** [F]：文档 API 只返回 PDF 时智能体无法解析，这样的 MCP 服务没有实际意义；应先开发能返回文本（如 Markdown）的 API。
3. **暴露工具不设认证授权** [F]：任何协议暴露工具和数据都需强安全措施，必须控制客户端访问权限与操作范围。
4. **固定少量函数仍上 MCP** [F]：书中经验法则——仅需固定少量函数时直接工具调用即可，MCP 是复杂、互联系统的标准化框架。
5. **错误处理缺失** [F]：未定义工具执行失败、服务器不可用等错误如何反馈给 LLM，智能体便无法理解失败并尝试替代方案。
6. **[E] 无限制暴露全部工具**：工具过多会稀释模型的选择准确率，应用 tool_filter 收敛到任务相关的最小集合。

## 7. 与其他模式的组合

- **MCP + 工具使用（05）**：MCP 是工具使用模式的标准化、跨系统落地形态——工具经 MCP 协议被发现与调用 [F]。
- **MCP + 多智能体（10）**：可复用的独立 MCP 服务器可被任何应用访问，多个智能体共享同一工具资产（联邦模型）[F]。
- **MCP + 规划（04）**：复杂流程编排中，智能体组合多种 MCP 工具和数据源完成多步骤流程（取客户数据→生成图片→撰写邮件→发送）[F]。
- **MCP + 异常恢复（14）**：协议层定义错误反馈机制，让智能体理解失败并尝试替代方案 [F]。
- **MCP + A2A（12）**：MCP 面向智能体与工具/数据，A2A 面向智能体之间，二者互为补充 [F]（对比详见第 12 章）。

## 8. 评估指标

- **结果导向**：工具调用成功率（发现→构造→执行→响应全链路）；依赖外部工具的任务完成率 [E]。
- **过程导向**：能力发现延迟与命中率；服务器响应延迟（本地 STDIO 与远程 HTTP 的传输开销对比）；工具选择准确率（从已暴露工具中选对的比率）[E]。
- **架构导向**：服务器复用度（被多少不同应用/智能体消费）；集成成本变化（新工具接入是否无需修改智能体代码）[E]。
