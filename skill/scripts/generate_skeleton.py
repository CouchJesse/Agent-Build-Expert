#!/usr/bin/env python3
"""代码骨架生成器：从模式分章文件提取代码模板，物化为骨架文件。

用法：
    python generate_skeleton.py --pattern 04 [--framework langchain|adk|crewai|all] [--out DIR]

参数：
    --pattern   模式编号（01-21）或名称片段（如 planning / rag）
    --framework 生成哪个框架的骨架，默认 all
    --out       输出目录，默认 ./skeleton_output

行为：
    解析 references/NN-*.md 第 5 节的代码块，按框架写入骨架文件。
    伪代码块（text）写入 README_pseudocode.txt；python 块按标题归类写入 .py。
    版本告警与 SAFETY 注释原样保留。
"""
import argparse
import os
import re
import sys
import glob

HERE = os.path.dirname(os.path.abspath(__file__))
REF_DIR = os.path.normpath(os.path.join(HERE, "..", "references"))

# 标题关键词 → 框架名映射（按分章模板的 5.x 节标题）
FRAMEWORK_KEYS = {
    "langchain": "langchain",
    "langgraph": "langchain",   # LangChain/LangGraph 归并为 langchain 系
    "adk": "adk",
    "crewai": "crewai",
    "fastmcp": "adk",           # MCP 章：FastMCP 服务器归 adk 侧消费链路
    "openai": "openai",
    "openrouter": "openrouter",
    "提示模板": "prompt",
    "框架无关": "pseudocode",
}


def find_chapter(pattern: str) -> str:
    """按编号或名称片段定位分章文件。"""
    if pattern.isdigit() and len(pattern) == 2:
        hits = glob.glob(os.path.join(REF_DIR, f"{pattern}-*.md"))
    else:
        hits = [f for f in glob.glob(os.path.join(REF_DIR, "[0-9][0-9]-*.md"))
                if pattern.lower() in os.path.basename(f).lower()]
    if not hits:
        sys.exit(f"[FAIL] 未找到模式分章：{pattern}")
    if len(hits) > 1:
        sys.exit(f"[FAIL] 匹配到多个分章，请用两位编号：{[os.path.basename(h) for h in hits]}")
    return hits[0]


def extract_blocks(chapter_path: str):
    """提取第 5 节代码块：[(框架, 语言, 标题, 代码), ...]。"""
    text = open(chapter_path, encoding="utf-8").read()
    # 截取「## 5. 多框架代码模板」到「## 6.」之间
    m = re.search(r"## 5\..*?(?=## 6\.)", text, re.S)
    if not m:
        sys.exit(f"[FAIL] {chapter_path} 未找到第 5 节代码模板")
    section = m.group(0)

    blocks = []
    # 逐个匹配小节标题 + 代码块
    for hm in re.finditer(r"### (5\.\d) ([^\n]+)\n(.*?)(?=### 5\.\d|\Z)", section, re.S):
        heading_no, heading_title, body = hm.groups()
        for cm in re.finditer(r"```(\w+)\n(.*?)```", body, re.S):
            lang, code = cm.groups()
            framework = "other"
            for key, fw in FRAMEWORK_KEYS.items():
                if key in heading_title.lower():
                    framework = fw
                    break
            blocks.append((framework, lang, f"{heading_no} {heading_title.strip()}", code.rstrip()))
    return blocks


def main():
    ap = argparse.ArgumentParser(description="从模式分章提取代码骨架")
    ap.add_argument("--pattern", required=True, help="模式编号(01-21)或名称片段")
    ap.add_argument("--framework", default="all",
                    choices=["all", "langchain", "adk", "crewai", "openai", "openrouter", "pseudocode"])
    ap.add_argument("--out", default="./skeleton_output")
    args = ap.parse_args()

    chapter = find_chapter(args.pattern)
    base = os.path.basename(chapter)          # 04-planning.md
    num = base.split("-")[0]                  # 04
    name = base[:-3].split("-", 1)[1]         # planning

    blocks = extract_blocks(chapter)
    if not blocks:
        sys.exit(f"[FAIL] {base} 第 5 节未解析到代码块")

    out_dir = os.path.abspath(args.out)
    os.makedirs(out_dir, exist_ok=True)

    written = []
    for i, (framework, lang, heading, code) in enumerate(blocks, 1):
        if args.framework != "all" and framework != args.framework:
            continue
        if lang == "text":
            fname = f"{num}_{name}_pseudocode_{i:02d}.txt"
        else:
            ext = "py" if lang == "python" else lang
            fname = f"{num}_{name}_{framework}_{i:02d}.{ext}"
        header = (f"# 来源：references/{base} · {heading}\n"
                  f"# 框架：{framework} · 语言：{lang}\n"
                  f"# 注意：版本以文中标注为准；未验证处须核对最新文档。\n"
                  f"# SAFETY 注释处为高风险操作，执行前须人工确认。\n\n")
        path = os.path.join(out_dir, fname)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(header + code + "\n")
        written.append(fname)

    if not written:
        sys.exit(f"[FAIL] 框架 {args.framework} 在 {base} 中无匹配代码块")
    print(f"[OK] {base} → {len(written)} 个骨架文件写入 {out_dir}")
    for w in written:
        print(f"  - {w}")


if __name__ == "__main__":
    main()
