# 变更记录（CHANGELOG）

本文件遵循 [语义化版本 2.0.0](https://semver.org/lang/zh-CN/) 与 Keep a Changelog 约定。

版本号格式 `主.次.修订`：
- **主版本（MAJOR）**：技能本体结构或调用契约发生不兼容变更时递增；
- **次版本（MINOR）**：向后兼容地新增模式、能力或文档时递增；
- **修订（PATCH）**：向后兼容的缺陷修正、触发词扩充、实测数据补全时递增。

版本单一事实源 = 专家包 `.codebuddy-plugin/plugin.json` 的 `version` 字段；`deployment/` 双 zip 以 zip 注释携带 `version=1.0.1` 版本戳。

---

## [1.0.1] — 2026-09-20

首个正式 GitHub Release 版本。技能内容版本与专家包 `plugin.json` 经真实同步升级对齐至 `1.0.1`。

### 新增（Added）
- 触发词表由 17 项扩充至 **42 项**（H-01），覆盖「领域核心词 / 英文模式名 / 症状态词 / 框架词 / 语序变体 / 调用动词」六类，触发回归覆盖率 **58% → 100%**。
- `requirements-spec`（需求规格）升 v1.1.0：新增 §2.1「触发与调用契约」（三层通道表 + 42 项词表构成 + 框架可用性实测表）。
- 框架可用性实测：6 框架 × 21 章 = 126 组合全量实跑，结果写入 `skill/references/` 与需求规格；自然语「LangGraph」归 langchain 系、「框架无关」归 pseudocode。
- 配套工具：`tools/upgrade_skill.py`（原子升级器，技能升级时同步升级关联专家包、保证版本一致，含回滚 / 降级拦截 / 缺失处理 / 漂移修复）与回归测试 `tools/upgrade_skill_test.py`（28 断言）。
- 全局技能 `skill-package-verify`（五维验证法：结构 / 触发 / 执行 / 护栏 / 引用），由本项目的验证实践沉淀而成（独立跨项目资产，另行发布，本包 README 已说明）。

### 修正（Fixed）
- 验收报告 SAFETY 标注计数勘误：「14 处」实为 **14 个文件含 22 处标注**（11 分章 17 处 + build-guide 2 + generate_skeleton 2 + SKILL.md 1）（H-02）。
- 端到端回归记录（test_04）G-03 数据勘误：CrewAI 不可用章节原记 5 章，实测 **6 章**（含 §12，因 `langgraph` 键先于 `crewai` 匹配归 langchain 系），经 126 组合全量复核确认。
- 验收报告编号算术修正：「11 分章含 16 处」实为 **17 处**。

### 变更（Changed）
- 验收报告（test_01）升 v1.0.2、端到端回归记录（test_04）升 v1.0.1，按「先归档→再改文」铁律升版，旧版归档至 `dochistory/`。
- 专家包 `plugin.json` 由 1.0.0 经真实同步升级对齐至 **1.0.1**；源 / 用户级安装实例 / 专家挂载三方 `SKILL.md` MD5 全等，双 zip 版本戳一致。

---

## [1.0.0] — 2026-09-20

初始交付版本。

### 新增（Added）
- 智能体设计模式技能本体 `skill/`：SKILL.md（8 节）+ assets/overview.svg + references（21 模式详解 + 附录 A~G + methodology/build-guide.md）+ scripts（generate_skeleton.py / query_pattern.py / validate_skill.py），共 36 文件。
- 专家包 `expert/`：`.codebuddy-plugin/plugin.json`（version 1.0.0）、README.md、agents/agent-design-patterns.md、avatars/expert.png，内嵌完整技能本体，共 40 文件。
- 部署包 `deployment/`：agent-design-patterns-skill.zip（36 条目）、agent-design-patterns-expert.zip（40 条目），zip 注释携带版本戳。
- 项目文档 `docs/`：实施计划（dev）、需求规格（technical）、验收报告 / 项目收尾审计报告 / 审计发现处理裁定记录 / 端到端回归记录（test）、文档规范（DOCUMENTATION_GUIDELINES.md）。

### 已知遗留（Pending）
- `/adp` 真实会话触发实测（D-02 关闭依据）属用户动作，待在真实会话中执行后确认。
