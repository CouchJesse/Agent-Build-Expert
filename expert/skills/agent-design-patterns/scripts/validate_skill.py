#!/usr/bin/env python3
"""技能自检器：结构完整性 + 脱敏 + 硬编码密钥全量校验。

用法：
    python validate_skill.py [技能根目录]

检查项：
    1. SKILL.md frontmatter（name/description/agent_created）
    2. 21 个模式分章存在，且各含 8 节结构、溯源行、[F] 标记、代码块 ≤ 6
    3. methodology 3 文件 + appendices 7 文件存在，含溯源行与证据分级
    4. 脱敏扫描（个人/公司敏感词，可扩充 SENSITIVE_WORDS）
    5. 硬编码密钥扫描（api_key= 字面量、sk- 前缀长串）

退出码：0=全部通过；1=存在问题（并打印问题清单）。
"""
import glob
import io
import os
import re
import sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF = os.path.join(ROOT, "references")

PATTERN_SECTIONS = ["1. 模式定义", "2. 工作机制", "3. 适用场景与不适用场景",
                    "4. 选型决策要点", "5. 多框架代码模板", "6. 反模式与坑点",
                    "7. 与其他模式的组合", "8. 评估指标"]
METHODOLOGY_FILES = ["build-guide.md", "review-guide.md", "decision-tree.md"]
APPENDIX_FILES = ["appendix-a-prompt-engineering.md", "appendix-b-agent-interaction.md",
                  "appendix-c-framework-overview.md", "appendix-d-agentspace.md",
                  "appendix-e-cli-agents.md", "appendix-f-reasoning-engines.md",
                  "appendix-g-coding-agents.md"]
# 敏感词以拼接形式存储，避免脚本自身被扫描时误报
SENSITIVE_WORDS = ["蒋" + "兴", "Jiang" + "Xing", "戎" + "畅", "Ro" + "yo", "毕恩" + "吉"]
KEY_PATTERNS = [r"api_key\s*=\s*[\"'][A-Za-z0-9_-]{8,}[\"']", r"sk-[A-Za-z0-9]{20,}"]


def check_skill_md(problems):
    path = os.path.join(ROOT, "SKILL.md")
    if not os.path.exists(path):
        problems.append("缺 SKILL.md")
        return
    head = io.open(path, encoding="utf-8").read()[:800]
    for field in ["name:", "description:", "agent_created:"]:
        if field not in head:
            problems.append(f"SKILL.md frontmatter 缺 {field}")


def check_patterns(problems):
    files = sorted(glob.glob(os.path.join(REF, "[0-9][0-9]-*.md")))
    nums = {os.path.basename(f)[:2] for f in files}
    for n in range(1, 22):
        if f"{n:02d}" not in nums:
            problems.append(f"缺模式分章 {n:02d}")
    for f in files:
        text = io.open(f, encoding="utf-8").read()
        base = os.path.basename(f)
        for s in PATTERN_SECTIONS:
            if s not in text:
                problems.append(f"{base} 缺节[{s}]")
        if "溯源" not in "\n".join(text.split("\n")[:6]):
            problems.append(f"{base} 缺溯源行")
        if "[F]" not in text:
            problems.append(f"{base} 无[F]标记")
        ncode = len(re.findall(r"^```", text, re.M)) // 2
        if ncode > 6:
            problems.append(f"{base} 代码块过多({ncode})")


def check_methodology_appendices(problems):
    for rel in [os.path.join("methodology", m) for m in METHODOLOGY_FILES] + \
               [os.path.join("appendices", a) for a in APPENDIX_FILES]:
        path = os.path.join(REF, rel)
        if not os.path.exists(path):
            problems.append(f"缺 {rel}")
            continue
        text = io.open(path, encoding="utf-8").read()
        if "溯源" not in "\n".join(text.split("\n")[:6]):
            problems.append(f"{rel} 缺溯源行")
        if "[F]" not in text and "[E]" not in text:
            problems.append(f"{rel} 无证据分级")


def scan_sensitive_and_keys(problems):
    for path in glob.glob(os.path.join(ROOT, "**", "*"), recursive=True):
        if not os.path.isfile(path) or path.endswith((".pyc",)):
            continue
        rel = os.path.relpath(path, ROOT)
        try:
            text = io.open(path, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        for w in SENSITIVE_WORDS:
            if w.lower() in text.lower():
                problems.append(f"{rel} 含敏感词[{w}]")
        for pat in KEY_PATTERNS:
            for m in re.finditer(pat, text):
                problems.append(f"{rel} 疑似硬编码密钥: {m.group(0)[:20]}...")


def main():
    problems = []
    check_skill_md(problems)
    check_patterns(problems)
    check_methodology_appendices(problems)
    scan_sensitive_and_keys(problems)

    if problems:
        print(f"[FAIL] 共 {len(problems)} 个问题：")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)
    print("[OK] 技能自检全部通过：结构 / 溯源 / 证据分级 / 脱敏 / 密钥扫描")


if __name__ == "__main__":
    main()
