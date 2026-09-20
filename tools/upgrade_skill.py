#!/usr/bin/env python3
"""skill → 专家包 同步升级器（atomic skill/expert co-upgrader）。

将「skill 升级」从人工五步流程固化为原子操作：以 dev-work/<name> 为源，
一次执行完成 校验 → 版本写入 → 双安装实例镜像同步 → 双分发包重建 → 终验；
任一步骤失败即按变更日志回滚，保证不留半升级状态。

升级模型
--------
版本单一事实源：专家包 `.codebuddy-plugin/plugin.json` 的 `version` 字段。
skill 本体（SKILL.md 等）不携带版本；两个分发包以 zip 注释携带版本戳，
终验时回读比对，实现「skill 与专家包版本一致」的可验证约束。

执行步骤（全有或全无）
--------------------
1.  前置检查：源/安装实例/专家包/部署目录定位；plugin.json 可解析性；
    版本解析（--version / --bump / 不变）；降级拦截（--force 覆盖）。
2.  漂移报告：源 vs 各安装实例 MD5 差异（只报告，不阻断——升级即消除漂移）。
3.  validate_skill.py 硬门槛（rc=0 方可继续；校验器缺失视为致命错误）。
4.  写入新版本到 plugin.json（正则精确替换，恰一处匹配，否则中止）。
5.  镜像同步：源 → 用户级安装目录；源 → 各专家包 skills/<name> 挂载。
    语义为严格镜像：差异覆盖 / 新增复制 / 多余删除，全部记入变更日志。
6.  重建分发包：<deploy-dir>/<name>-skill.zip（前缀 <name>/）与
    <name>-expert.zip（前缀 <插件目录名>/），写入版本戳注释。
7.  终验：安装实例 MD5 全等；zip 完整性与包内 SKILL.md 比对；zip 注释
    版本回读；plugin.json 版本回读。
8.  任一步骤失败：按变更日志回滚全部变更（含新建文件删除、删除文件恢复、
    空目录清理），退出码 1；成功则退出码 0。

边界情况处置
------------
- 专家包目录不存在：跳过专家包同步与专家包 zip 重建（响亮告警，不静默），
  skill 侧照常升级；专家包 zip 将滞后，报告中明示。
- 专家包存在但 plugin.json 缺失/不可解析：默认整体中止（版本无法写入，
  强行继续将造成版本不一致）；--force 时降级为跳过该专家包并响亮告警。
- 版本不匹配：--bump 依赖 plugin.json 现值，缺失即中止；目标版本低于
  现值属降级，默认中止，--force 覆盖。
- 安装实例漂移：前置检出并写入报告，升级过程将其强制对齐到源。
- 用户级安装目录不存在：视为首次安装，全量创建（可回滚）。

用法
----
    python tools/upgrade_skill.py <name> [--version X.Y.Z | --bump patch|minor|major]
                                   [--source DIR] [--project-root DIR]
                                   [--deploy-dir DIR] [--user-root DIR]
                                   [--marketplaces-root DIR]
                                   [--dry-run] [--force]

设计约束：仅标准库；无网络；不执行被升级技能中的代码（校验器经子进程
调用且属项目自带的确定性脚本）。

退出码：0 成功；1 失败（已回滚）；2 前置条件/用法错误（未执行任何变更）。
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

EXCLUDE_DIRS = {"__pycache__", ".git", "node_modules"}
VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
PLUGIN_VERSION_RE = re.compile(r'("version"\s*:\s*")([^"]+)(")')


class Abort(Exception):
    """可回滚的执行中断。"""


def md5_file(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for blk in iter(lambda: fh.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def collect(root: Path) -> dict:
    """返回 {相对路径: 绝对路径}，跳过排除目录。"""
    out = {}
    if not root.is_dir():
        return out
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in EXCLUDE_DIRS]
        for f in fns:
            p = Path(dp) / f
            out[p.relative_to(root).as_posix()] = p
    return out


def md5_map(root: Path) -> dict:
    return {rel: md5_file(p) for rel, p in collect(root).items()}


def parse_version(text: str):
    m = VERSION_RE.match(text.strip())
    return tuple(int(x) for x in m.groups()) if m else None


class Journal:
    """变更日志：记录 set（覆盖/新建/删除）与新建目录，支持完整回滚。"""

    def __init__(self):
        self._saved = {}   # path -> 旧字节；None 表示执行前不存在（回滚时删除）
        self._dirs = []    # 本流程新建的目录（回滚时逐个尝试删空目录）

    def set_file(self, path: Path, new_bytes: bytes | None):
        """记录对 path 的写入（new_bytes=None 表示随后将删除）。"""
        if path not in self._saved:
            self._saved[path] = path.read_bytes() if path.exists() else None
        if new_bytes is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(new_bytes)

    def note_dir(self, d: Path):
        if d not in self._dirs:
            self._dirs.append(d)

    def snapshot_file(self, path: Path):
        if path not in self._saved:
            self._saved[path] = path.read_bytes() if path.exists() else None

    def rollback(self) -> dict:
        restored = deleted = 0
        for path, old in self._saved.items():
            if old is None:
                if path.exists():
                    path.unlink()
                    deleted += 1
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(old)
                restored += 1
        for d in sorted(self._dirs, key=lambda x: len(x.parts), reverse=True):
            try:
                d.rmdir()  # 仅删除空目录，非空则保留（保底不误删）
            except OSError:
                pass
        return {"restored": restored, "deleted": deleted}

    def dispose(self):
        self._saved.clear()
        self._dirs.clear()


def discover_experts(marketplaces_root: Path, name: str) -> list:
    """扫描 marketplaces/<市场>/plugins/<插件>/skills/<name>，返回专家包信息列表。"""
    experts = []
    if not marketplaces_root.is_dir():
        return experts
    for mkt in sorted(marketplaces_root.iterdir()):
        plugins = mkt / "plugins"
        if not plugins.is_dir():
            continue
        for plugin_dir in sorted(plugins.iterdir()):
            mount = plugin_dir / "skills" / name
            if mount.is_dir() and (mount / "SKILL.md").is_file():
                experts.append({
                    "plugin_dir": plugin_dir,
                    "mount": mount,
                    "plugin_json": plugin_dir / ".codebuddy-plugin" / "plugin.json",
                    "marketplace": mkt.name,
                    "error": None,
                })
    return experts


def read_plugin_version(plugin_json: Path):
    """返回 (版本字符串或 None, 错误信息或 None)。"""
    if not plugin_json.is_file():
        return None, "plugin.json 不存在"
    try:
        data = json.loads(plugin_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as e:
        return None, "plugin.json 不可解析（%s）" % e
    ver = data.get("version")
    if not isinstance(ver, str) or parse_version(ver) is None:
        return None, "plugin.json version 字段缺失或非语义化版本"
    return ver, None


def set_plugin_version(text: str, new_ver: str) -> str:
    matches = list(PLUGIN_VERSION_RE.finditer(text))
    if len(matches) != 1:
        raise Abort("plugin.json 中 version 字段匹配到 %d 处（应为恰 1 处），拒绝写入"
                    % len(matches))
    m = matches[0]
    return text[:m.start()] + m.group(1) + new_ver + m.group(3) + text[m.end():]


def mirror_sync(src_root: Path, dst_root: Path, journal: Journal) -> dict:
    """严格镜像：覆盖差异 / 复制新增 / 删除多余。返回统计。"""
    src = collect(src_root)
    dst = collect(dst_root)
    changed = created = deleted = 0
    for rel in sorted(src):
        sp, dp = src[rel], dst_root / rel
        if rel in dst:
            if md5_file(sp) != md5_file(dp):
                journal.set_file(dp, sp.read_bytes())
                changed += 1
        else:
            if not dp.parent.exists():
                journal.note_dir(dp.parent)
            journal.set_file(dp, sp.read_bytes())
            created += 1
    for rel in sorted(set(dst) - set(src)):
        dp = dst_root / rel
        journal.set_file(dp, None)   # 记录原内容快照，随后删除
        dp.unlink()
        deleted += 1
    return {"覆盖": changed, "新增": created, "删除": deleted}


def build_zip(src_root: Path, prefix: str, out_path: Path,
              version: str | None, built: str, journal: Journal) -> int:
    import zipfile
    journal.snapshot_file(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in sorted(collect(src_root)):
            zf.write(src_root / rel, "%s/%s" % (prefix, rel))
        if version:
            zf.comment = ("version=%s; built=%s; source=%s"
                          % (version, built, prefix)).encode("utf-8")
    with zipfile.ZipFile(out_path) as zf:
        return len(zf.namelist())


def verify_zip(zip_path: Path, expect_prefix: str, src_md5_map: dict,
               version: str | None, skill_rel: str = "SKILL.md") -> list:
    """返回问题列表（空 = 通过）。skill_rel 为包内 SKILL.md 相对前缀的路径
    （skill zip 为 SKILL.md；expert zip 为 skills/<name>/SKILL.md）。"""
    import zipfile
    problems = []
    with zipfile.ZipFile(zip_path) as zf:
        if zf.testzip() is not None:
            problems.append("完整性校验失败")
        names = zf.namelist()
        if any(not n.startswith(expect_prefix + "/") for n in names):
            problems.append("存在前缀 %s/ 之外的条目" % expect_prefix)
        inner = "%s/%s" % (expect_prefix, skill_rel)
        if inner not in names:
            problems.append("缺少 %s" % inner)
        elif hashlib.md5(zf.read(inner)).hexdigest() != src_md5_map.get("SKILL.md"):
            problems.append("包内 SKILL.md 与源不一致")
        if version:
            m = re.search(r"version=([\d.]+)",
                          zf.comment.decode("utf-8", "replace"))
            if not m or m.group(1) != version:
                problems.append("zip 版本戳缺失或不匹配（%r）"
                                % zf.comment.decode("utf-8", "replace"))
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(
        description="skill → 专家包 同步升级器（原子升级，失败自动回滚）")
    ap.add_argument("name", help="技能名（如 agent-design-patterns）")
    ap.add_argument("--source", default=None,
                    help="技能源目录（默认 <project>/dev-work/<name>）")
    ap.add_argument("--project-root", default=None,
                    help="项目根（默认为脚本所在目录的上一级）")
    ap.add_argument("--deploy-dir", default=None,
                    help="分发包目录（默认 <project-root>/doc/deployment）")
    ap.add_argument("--user-root", default=None,
                    help="用户级技能根目录（默认 ~/.workbuddy/skills）")
    ap.add_argument("--marketplaces-root", default=None,
                    help="专家包市场根目录（默认 ~/.workbuddy/plugins/marketplaces）")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--version", default=None, help="目标版本 X.Y.Z")
    g.add_argument("--bump", choices=["patch", "minor", "major"], default=None,
                   help="自当前版本递增")
    ap.add_argument("--dry-run", action="store_true", help="只输出计划，不执行")
    ap.add_argument("--force", action="store_true",
                    help="覆盖保护：允许降级；plugin.json 异常时跳过该专家包而非中止")
    args = ap.parse_args()

    name = args.name
    project_root = Path(args.project_root).resolve() if args.project_root \
        else Path(__file__).resolve().parent.parent
    source = Path(args.source).resolve() if args.source \
        else project_root / "dev-work" / name
    user_root = Path(args.user_root or os.path.expanduser("~/.workbuddy/skills"))
    mkt_root = Path(args.marketplaces_root or
                    os.path.expanduser("~/.workbuddy/plugins/marketplaces"))
    deploy_dir = Path(args.deploy_dir).resolve() if args.deploy_dir \
        else project_root / "doc" / "deployment"
    user_install = user_root / name
    validator = source / "scripts" / "validate_skill.py"

    L = []
    A = L.append

    # ---------- 1. 前置定位 ----------
    A("== 1. 前置定位 ==")
    if not (source / "SKILL.md").is_file():
        print("[FAIL] 技能源目录无效（缺 SKILL.md）：%s" % source, file=sys.stderr)
        return 2
    A("源目录          ：%s" % source)
    A("用户级安装目录  ：%s%s" % (user_install,
                                  "" if user_install.is_dir() else "（不存在，将首次安装）"))
    A("分发包目录      ：%s%s" % (deploy_dir,
                                  "" if deploy_dir.is_dir() else "（不存在，将创建）"))
    experts = discover_experts(mkt_root, name)
    if experts:
        for e in experts:
            A("专家包          ：%s（marketplace=%s）" % (e["plugin_dir"], e["marketplace"]))
    else:
        A("专家包          ：未发现（将跳过专家包同步与专家包 zip 重建，⚠️ 专家包将滞后）")

    # ---------- 2. 版本解析与一致性检查 ----------
    A("")
    A("== 2. 版本解析 ==")
    cur = None
    broken = []
    for e in experts:
        ver, err = read_plugin_version(e["plugin_json"])
        e["error"] = err
        if err:
            broken.append(e)
        elif cur is None:
            cur = ver
        if not err:
            A("plugin.json 现版本：%s（%s）" % (ver, e["plugin_dir"]))

    skipped = []
    if broken:
        if args.force:
            skipped = broken
            experts = [e for e in experts if not e["error"]]
            A("⚠️ %d 个专家包 plugin.json 异常（--force 降级为跳过，其版本将滞后）：%s"
              % (len(broken), "；".join("%s：%s" % (e["plugin_dir"], e["error"])
                                        for e in broken)))
        else:
            print("[FAIL] 专家包 plugin.json 状态异常，拒绝升级（强行继续将造成版本不一致）：",
                  file=sys.stderr)
            for e in broken:
                print("  - %s：%s" % (e["plugin_dir"], e["error"]), file=sys.stderr)
            print("  处置：修复 plugin.json，或 --force 跳过异常专家包（其版本将滞后）",
                  file=sys.stderr)
            return 2
    if experts:
        for e in experts:
            ver, _ = read_plugin_version(e["plugin_json"])
            e["version"] = ver
    else:
        for e in experts:
            e["version"] = None

    target = None
    if args.version:
        if parse_version(args.version) is None:
            print("[FAIL] --version 需为 X.Y.Z：%r" % args.version, file=sys.stderr)
            return 2
        target = args.version
    elif args.bump:
        if not cur:
            print("[FAIL] --bump 需要可读的当前版本（plugin.json）；当前不可得，"
                  "请改用 --version 明确指定", file=sys.stderr)
            return 2
        a, b, c = parse_version(cur)
        target = {"patch": "%d.%d.%d" % (a, b, c + 1),
                  "minor": "%d.%d.%d" % (a, b + 1, 0),
                  "major": "%d.%d.%d" % (a + 1, 0, 0)}[args.bump]
    if target and cur and parse_version(target) < parse_version(cur) and not args.force:
        print("[FAIL] 目标版本 %s 低于当前版本 %s（降级需 --force）" % (target, cur),
              file=sys.stderr)
        return 2
    A("目标版本        ：%s" % (target or "（不变更，仅同步）"))

    # ---------- 3. 漂移报告 ----------
    A("")
    A("== 3. 漂移报告（源 vs 各安装实例，升级将消除漂移）==")
    src_map = md5_map(source)
    drift_total = 0
    targets = [("用户级安装", user_install)] + \
        [("专家包挂载(%s)" % e["marketplace"], e["mount"]) for e in experts]
    for label, root in targets:
        if not root.is_dir():
            A("  %s：不存在（将全量创建）" % label)
            drift_total += 1
            continue
        ins_map = md5_map(root)
        diff = sorted(r for r in set(src_map) | set(ins_map)
                      if src_map.get(r) != ins_map.get(r))
        drift_total += len(diff)
        A("  %s：%d/%d 文件一致%s"
          % (label, len(src_map) - len(diff), len(src_map),
             ("，漂移 %d 项：%s%s" % (len(diff), "、".join(diff[:5]),
                                     "…" if len(diff) > 5 else "")) if diff else "，无漂移"))
    for e in skipped:
        A("  专家包(%s)：已跳过（plugin.json 异常，内容不检查不更新）" % e["marketplace"])
    if not drift_total and not (target and target != cur):
        A("  （无漂移且版本无变化——执行则为幂等同步 + zip 重建）")

    # ---------- dry-run ----------
    if args.dry_run:
        A("")
        A("== dry-run 计划（未执行任何变更）==")
        A("1. validate_skill.py 硬门槛（%s）" % validator)
        A("2. plugin.json %s" % ("version → %s" % target
                                 if (target and target != cur) else "不变更"))
        A("3. 镜像同步 → %s" % user_install)
        for e in experts:
            A("4. 镜像同步 → %s" % e["mount"])
        A("5. 重建 %s（前缀 %s/）" % (deploy_dir / ("%s-skill.zip" % name), name))
        if experts:
            A("6. 重建 %s（前缀 %s/）" % (deploy_dir / ("%s-expert.zip" % name),
                                          experts[0]["plugin_dir"].name))
        A("7. 终验：MD5 / zip 完整性 / 版本戳与 plugin.json 版本回读")
        print("\n".join(L))
        return 0

    # ---------- 4. 执行（全有或全无） ----------
    built = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    journal = Journal()
    try:
        A("")
        A("== 4. 执行（任一步失败即回滚）==")
        if not validator.is_file():
            raise Abort("校验器缺失：%s（发布硬门槛，拒绝跳过）" % validator)
        r = subprocess.run([sys.executable, str(validator), str(source)],
                           capture_output=True, text=True)
        out = (r.stdout or r.stderr).strip()
        if r.returncode != 0:
            raise Abort("validate_skill.py 未通过（rc=%d）：%s"
                        % (r.returncode, out.splitlines()[-1] if out else "无输出"))
        A("✅ validate_skill.py rc=0")

        if target and target != cur:
            for e in experts:
                pj = e["plugin_json"]
                journal.snapshot_file(pj)
                pj.write_text(set_plugin_version(pj.read_text(encoding="utf-8"), target),
                              encoding="utf-8", newline="\n")
                A("✅ plugin.json version → %s（%s）" % (target, e["plugin_dir"]))
        else:
            A("— plugin.json 不变更")

        st = mirror_sync(source, user_install, journal)
        A("✅ 用户级安装同步：%s" % st)
        for e in experts:
            st = mirror_sync(source, e["mount"], journal)
            A("✅ 专家包挂载同步（%s）：%s" % (e["marketplace"], st))

        n = build_zip(source, name, deploy_dir / ("%s-skill.zip" % name),
                      target, built, journal)
        A("✅ skill zip 重建：%d 条目" % n)
        if experts:
            n = build_zip(experts[0]["plugin_dir"], experts[0]["plugin_dir"].name,
                          deploy_dir / ("%s-expert.zip" % name), target, built, journal)
            A("✅ expert zip 重建：%d 条目" % n)

        # ---------- 5. 终验 ----------
        A("")
        A("== 5. 终验 ==")
        problems = []
        for label, root in targets:
            ins_map = md5_map(root)
            diff = sorted(r for r in set(src_map) | set(ins_map)
                          if src_map.get(r) != ins_map.get(r))
            if diff:
                problems.append("%s 仍有差异：%s" % (label, "、".join(diff[:5])))
        pr = verify_zip(deploy_dir / ("%s-skill.zip" % name), name, src_map, target)
        if pr:
            problems.append("skill zip：%s" % "；".join(pr))
        if experts:
            pr = verify_zip(deploy_dir / ("%s-expert.zip" % name),
                            experts[0]["plugin_dir"].name, src_map, target,
                            skill_rel="skills/%s/SKILL.md" % name)
            if pr:
                problems.append("expert zip：%s" % "；".join(pr))
        if target and experts:
            for e in experts:
                ver, err = read_plugin_version(e["plugin_json"])
                if err or ver != target:
                    problems.append("plugin.json 版本回读异常：%s（%s）"
                                    % (e["plugin_dir"], err or ver))
        if problems:
            raise Abort("终验未通过：" + "；".join(problems))
        A("✅ 安装实例 MD5 全等；zip 完整性与 SKILL.md 一致；版本戳回读 = %s"
          % (target or "—"))

        A("")
        A("== 6. 结果 ==")
        A("升级完成：版本 %s → %s%s"
          % (cur or "（无）", target or (cur or "（无）"),
             "；跳过专家包 %d 个（版本滞后）" % len(skipped) if skipped else ""))
        n_ops = len(journal._saved)
        journal.dispose()
        A("变更日志：快照 %d 项（成功后弃用）" % n_ops)
        print("\n".join(L))
        return 0

    except Abort as e:
        rb = journal.rollback()
        A("")
        A("!! 升级失败：%s" % e)
        A("!! 已回滚：恢复 %d 项、删除新建 %d 项 —— 系统保持升级前状态"
          % (rb["restored"], rb["deleted"]))
        print("\n".join(L))
        print("[FAIL] 升级已回滚，退出码 1", file=sys.stderr)
        return 1
    except Exception as e:  # 未预期异常同样回滚，不留半升级状态
        rb = journal.rollback()
        print("!! 未预期异常：%r" % e)
        print("!! 已回滚：恢复 %d 项、删除新建 %d 项" % (rb["restored"], rb["deleted"]))
        print("[FAIL] 升级已回滚，退出码 1", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
