# 智能体设计模式技能与专家包（Agent Design Patterns） v1.0.1

> 面向 AI 智能体应用设计的「知识库 + 工程指南 + 专家包」一体化交付物，基于 21 个智能体设计模式，支持从零设计、模式选型、多框架代码骨架生成与已有 Agent 评审修正。

- **版本**：v1.0.1
- **发布日期**：2026-09-20
- **语义化版本**：`1.0.1`（Patch 级——触发词表扩充、框架可用性实测补全、配套工具与验证技能沉淀；技能本体结构无破坏性变更）
- **兼容环境**：WorkBuddy CLI / 兼容 OpenAI 插件规范的智能体运行时

---

## 1. 本发布包包含内容

| 目录 / 文件 | 说明 | 文件数 |
| --- | --- | --- |
| `skill/` | 技能本体（可直接安装到 `~/.workbuddy/skills/agent-design-patterns/`） | 36 |
| `expert/` | 专家包（marketplace 插件结构，含 plugin.json / agents / avatars / skills） | 40 |
| `deployment/` | 预构建安装包：`agent-design-patterns-skill.zip`、`agent-design-patterns-expert.zip`（zip 注释携带版本戳 `version=1.0.1`） | 2 |
| `tools/` | 原子升级工具 `upgrade_skill.py` 及其回归测试 `upgrade_skill_test.py` | 2 |
| `docs/` | 项目交付文档（实施计划 / 需求规格 / 验收报告 / 审计报告 / 回归记录 / 文档规范） | 7 |
| `README.md` | 本发布说明 | 1 |
| `CHANGELOG.md` | 语义化版本变更记录 | 1 |
| `SHA256SUMS.txt` | 发布包内全部文件 SHA-256 校验清单 | 1 |

**技能本体（skill/）结构**：

```
skill/
├── SKILL.md                       # 技能入口（8 节：角色/触发/模式/代码生成/评审/框架/反模式/资源）
├── assets/overview.svg            # 21 模式全景图
├── references/                    # 21 个模式详解（01~21）
│   ├── appendices/                # 附录 A~G（提示工程/交互/框架概览/Agentspace/CLI/推理引擎/编码智能体）
│   └── methodology/build-guide.md # 技能构建指南
└── scripts/                       # 配套脚本
    ├── generate_skeleton.py       # 按模式+框架生成可运行骨架
    ├── query_pattern.py           # 模式检索
    └── validate_skill.py          # 技能结构校验（升级前置硬门槛）
```

---

## 2. 安装方式

### 方式 A：目录复制（推荐用于开发 / 调试）

**安装技能**：

```
# Windows
xcopy skill  C:\Users\<你>\.workbuddy\skills\agent-design-patterns\  /E /I
# macOS / Linux
cp -r skill ~/.workbuddy/skills/agent-design-patterns
```

**安装专家包**：将 `expert/` 整体复制到你的 marketplace 插件目录（示例路径）：

```
C:\Users\<你>\.workbuddy\plugins\marketplaces\my-experts\plugins\agent-design-patterns\
```

> 复制后请在连接器管理页面对该自定义插件点击「信任」以启用。

### 方式 B：zip 一键安装

使用 `deployment/` 下的预构建包：

- `agent-design-patterns-skill.zip` → 解压到 `~/.workbuddy/skills/agent-design-patterns/`
- `agent-design-patterns-expert.zip` → 解压到 marketplace 插件目录

两个 zip 均在中央目录注释中写入 `version=1.0.1; built=2026-09-20T16:53:10`，可用于安装后版本核对。

---

## 3. 技能能力速览

- **三位一体工程指南**：代码生成（多框架骨架）/ 构建指导（设计要点与架构）/ 评审修正（体检清单 + 分级修正）。
- **21 个设计模式**：提示链、路由、并行化、规划、工具使用、RAG、反思、记忆管理、学习适应、多智能体、MCP、A2A、目标监控、异常恢复、HITL、资源优化、推理、护栏、评估、优先级、探索发现。
- **多框架支持**：LangChain / LangGraph、Google ADK、CrewAI、OpenAI / OpenRouter、以及框架无关伪代码；框架可用性实测见 `skill/references/` 与 `docs/technical/`。
- **触发覆盖率**：42 项触发词（v1.0.1 由 17 项扩充），覆盖「模式名 / 症状态 / 框架 / 语序变体」六类，回归触发覆盖率 58% → 100%。

---

## 4. 配套工具

- `tools/upgrade_skill.py`：原子升级器。当技能升级时同步升级关联专家包，保证双方 `version` 一致；内置回滚、版本不匹配拦截、专家包缺失处理与安装实例漂移修复。仅依赖标准库。
- `tools/upgrade_skill_test.py`：沙箱六场景回归套件（正常升级 / 校验失败回滚 / 降级拦截 / 专家包缺失 / plugin.json 缺失 / 安装漂移），28 项断言。

---

## 5. 本发布包已排除的内容（范围说明）

为保证发布包「可直接用于 GitHub Release」且不含冗余 / 敏感 / 大体积文件，以下项**未纳入**本包，特此说明：

| 排除项 | 原因 |
| --- | --- |
| `dochistory/`（历史归档 zip） | 历史版本归档，GitHub Release 仅发布当前版本 |
| `config/`（dev/prod/test 环境配置） | 本地环境内部配置，非发布交付物 |
| `doc/technical/ref_智能体设计模式_源书_*.pdf`（5.8 MB） | 源书参考材料，体积大且为引用来源，不随包分发 |
| `doc/product/`、`doc/user/`（空目录） | 无内容 |
| `skill-package-verify`（全局技能） | 独立的跨项目全局技能，非本仓库交付物，另行发布 |
| `__pycache__/`、`*.pyc`、`.git` 等 | 构建缓存与版本控制元数据（如有则自动剔除） |

如需历史归档或源书 PDF，请参照项目仓库对应路径获取。

---

## 6. 校验

发布包根目录提供 `SHA256SUMS.txt`，列举全部 87 个文件的 SHA-256 值。安装或分发前可校验完整性：

```
# Windows (PowerShell)
Get-FileHash -Algorithm SHA256 <文件>
# macOS / Linux
shasum -a 256 <文件>   # 与 SHA256SUMS.txt 逐行比对
```

---

## 7. 许可

本交付物以项目团队名义发布，仅供学习与内部项目实施使用。源书 PDF 等第三方引用材料的权利归原权利人所有。
