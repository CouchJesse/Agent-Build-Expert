#!/usr/bin/env python3
"""模式查询器：按关键词检索 21 模式分章 / 方法论 / 附录，返回命中位置。

用法：
    python query_pattern.py 幻觉
    python query_pattern.py "重规划" --max 20

输出：文件 → 小节 → 命中行（截断显示）。
用于快速定位「该查哪个分章」，配合 SKILL.md 第 8 节检索建议。
"""
import argparse
import glob
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.normpath(os.path.join(HERE, "..", "references"))


def main():
    ap = argparse.ArgumentParser(description="按关键词检索技能 references")
    ap.add_argument("keyword", help="检索关键词")
    ap.add_argument("--max", type=int, default=15, help="每文件最多显示命中数，默认 15")
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(REF, "**", "*.md"), recursive=True))
    total = 0
    for path in files:
        rel = os.path.relpath(path, REF)
        # 跳过打包前应删除的工作模板
        if os.path.basename(path).startswith("_"):
            continue
        lines = io.open(path, encoding="utf-8").read().split("\n")
        section = ""
        in_code = False
        hits = []
        for ln in lines:
            if ln.startswith("```"):
                in_code = not in_code
                continue
            if not in_code and ln.startswith("#"):
                section = ln.lstrip("# ").strip()
            if args.keyword.lower() in ln.lower():
                hits.append((section, ln.strip()[:100]))
        if hits:
            total += len(hits)
            print(f"\n◆ {rel}（{len(hits)} 处）")
            for sec, text in hits[: args.max]:
                print(f"  [{sec}] {text}")
            if len(hits) > args.max:
                print(f"  ...另有 {len(hits) - args.max} 处未显示")

    if total == 0:
        print(f"[无命中] 关键词「{args.keyword}」在 references 中未检索到")
        sys.exit(1)
    print(f"\n共 {total} 处命中。")


if __name__ == "__main__":
    main()
