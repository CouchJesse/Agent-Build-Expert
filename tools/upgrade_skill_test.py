"""upgrade_skill.py 沙箱测试套件：六场景，逐断言 PASS/FAIL。"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

PY = sys.executable
TOOL = r"E:\Project\Persnoal Project\AgentBuildExpert\tools\upgrade_skill.py"
REAL_SRC = r"E:\Project\Persnoal Project\AgentBuildExpert\dev-work\agent-design-patterns"
REAL_USER = r"C:\Users\JiangXing\.workbuddy\skills\agent-design-patterns"
REAL_PLUGIN = (r"C:\Users\JiangXing\.workbuddy\plugins\marketplaces\my-experts"
               r"\plugins\agent-design-patterns")
REAL_DEPLOY = r"E:\Project\Persnoal Project\AgentBuildExpert\doc\deployment"
SB = Path(r"C:\Users\JiangXing\AppData\Local\Temp\upg_test")
NAME = "agent-design-patterns"

results = []


def check(label, cond, detail=""):
    results.append((label, bool(cond), detail))
    print("  %s %s%s" % ("✅" if cond else "❌", label,
                         ("｜" + detail) if detail and not cond else ""))


def md5_file(p):
    h = hashlib.md5()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def md5_tree(root):
    out = {}
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in {"__pycache__", ".git"}]
        for f in fns:
            p = Path(dp) / f
            out[str(p.relative_to(root)).replace(os.sep, "/")] = md5_file(p)
    return out


def run_tool(*extra):
    return subprocess.run(
        [PY, TOOL, NAME,
         "--source", str(SB / "project/dev-work" / NAME),
         "--project-root", str(SB / "project"),
         "--deploy-dir", str(SB / "deploy"),
         "--user-root", str(SB / "home/skills"),
         "--marketplaces-root", str(SB / "home/plugins/marketplaces"),
         *extra], capture_output=True, text=True)


def setup():
    if SB.exists():
        shutil.rmtree(SB)
    shutil.copytree(REAL_SRC, SB / "project/dev-work" / NAME)
    shutil.copytree(REAL_USER, SB / "home/skills" / NAME)
    shutil.copytree(REAL_PLUGIN, SB / "home/plugins/marketplaces/my-experts/plugins" / NAME)
    (SB / "deploy").mkdir(parents=True)
    for z in ("agent-design-patterns-skill.zip", "agent-design-patterns-expert.zip"):
        shutil.copyfile(Path(REAL_DEPLOY) / z, SB / "deploy" / z)
    # 专家包纯净副本（供场景 4 重建）
    shutil.copytree(REAL_PLUGIN, SB / "pristine_plugin")


def snap_state():
    s = {}
    s["user"] = md5_tree(SB / "home/skills" / NAME)
    s["mount"] = md5_tree(SB / "home/plugins/marketplaces/my-experts/plugins" / NAME
                          / "skills" / NAME)
    pj_path = (SB / "home/plugins/marketplaces/my-experts/plugins" / NAME
               / ".codebuddy-plugin/plugin.json")
    s["plugin_json"] = pj_path.read_bytes() if pj_path.exists() else None
    s["skill_zip"] = (SB / "deploy/agent-design-patterns-skill.zip").read_bytes()
    s["expert_zip"] = (SB / "deploy/agent-design-patterns-expert.zip").read_bytes()
    return s


print("== 沙箱搭建 ==")
setup()
SRC = SB / "project/dev-work" / NAME
skill_md = SRC / "SKILL.md"
ORIG_SKILL = skill_md.read_bytes()
print("沙箱就绪：%s" % SB)

# ---------- 场景 1：正常升级 1.0.0 → 1.0.1 ----------
print("\n== 场景 1：正常升级（内容变更 + --version 1.0.1）==")
skill_md.write_bytes(ORIG_SKILL + "\n\n升级测试追加行（沙箱）。\n".encode("utf-8"))
r = run_tool("--version", "1.0.1")
check("1.1 退出码 0", r.returncode == 0, r.stdout[-500:] + r.stderr[-300:])
pj = SB / "home/plugins/marketplaces/my-experts/plugins" / NAME / ".codebuddy-plugin/plugin.json"
check("1.2 plugin.json → 1.0.1",
      json.loads(pj.read_text(encoding="utf-8"))["version"] == "1.0.1")
new_skill_md5 = md5_file(skill_md)
check("1.3 用户级安装 SKILL.md 与源一致",
      md5_file(SB / "home/skills" / NAME / "SKILL.md") == new_skill_md5)
check("1.4 专家包挂载 SKILL.md 与源一致",
      md5_file(SB / "home/plugins/marketplaces/my-experts/plugins" / NAME
               / "skills" / NAME / "SKILL.md") == new_skill_md5)
with zipfile.ZipFile(SB / "deploy/agent-design-patterns-skill.zip") as zf:
    check("1.5 skill zip 完整 + 版本戳 1.0.1",
          zf.testzip() is None and b"version=1.0.1" in zf.comment
          and hashlib.md5(zf.read("%s/SKILL.md" % NAME)).hexdigest() == new_skill_md5)
with zipfile.ZipFile(SB / "deploy/agent-design-patterns-expert.zip") as zf:
    check("1.6 expert zip 完整 + 版本戳 1.0.1",
          zf.testzip() is None and b"version=1.0.1" in zf.comment)
check("1.7 源 SKILL.md 未被工具改动",
      skill_md.read_bytes() == ORIG_SKILL + "\n\n升级测试追加行（沙箱）。\n".encode("utf-8"))

# ---------- 场景 2：校验失败 → 回滚 ----------
print("\n== 场景 2：校验失败回滚（注入硬编码密钥 → validate 必败）==")
pre = snap_state()
skill_md.write_bytes(ORIG_SKILL + '\napi_key = "1234567890abcdef"\n'.encode("utf-8"))
r = run_tool("--version", "1.0.2")
check("2.1 退出码 1", r.returncode == 1, "rc=%d" % r.returncode)
check("2.2 输出含回滚声明", "已回滚" in r.stdout and "validate_skill.py 未通过" in r.stdout)
post = snap_state()
check("2.3 用户级安装逐字节还原", post["user"] == pre["user"])
check("2.4 专家包挂载逐字节还原", post["mount"] == pre["mount"])
check("2.5 plugin.json 逐字节还原", post["plugin_json"] == pre["plugin_json"])
check("2.6 两个 zip 逐字节还原",
      post["skill_zip"] == pre["skill_zip"] and post["expert_zip"] == pre["expert_zip"])
# 还原源（工具不回滚源文件——源是升级输入，非升级目标）
S1_SKILL = ORIG_SKILL + "\n\n升级测试追加行（沙箱）。\n".encode("utf-8")
skill_md.write_bytes(S1_SKILL)

# 场景 2b：降级拦截
print("\n== 场景 2b：降级拦截（1.0.1 → 1.0.0）==")
r = run_tool("--version", "1.0.0")
check("2b.1 退出码 2 且提示降级",
      r.returncode == 2 and "降级" in r.stderr, r.stderr[:200])

# ---------- 场景 3：专家包缺失 ----------
print("\n== 场景 3：专家包缺失（删除整个专家包目录）==")
shutil.rmtree(SB / "home/plugins/marketplaces/my-experts/plugins" / NAME)
r = run_tool("--version", "1.0.2")
check("3.1 退出码 0（skill 侧照常升级）", r.returncode == 0,
      r.stdout[-400:] + r.stderr[-200:])
check("3.2 输出响亮声明专家包未发现/滞后",
      "未发现" in r.stdout and "滞后" in r.stdout)
check("3.3 skill zip 版本戳 1.0.2",
      b"version=1.0.2" in zipfile.ZipFile(
          SB / "deploy/agent-design-patterns-skill.zip").comment)
check("3.4 expert zip 未重建（保持 1.0.1 戳）",
      b"version=1.0.1" in zipfile.ZipFile(
          SB / "deploy/agent-design-patterns-expert.zip").comment)

# ---------- 场景 4：plugin.json 缺失 ----------
print("\n== 场景 4：专家包存在但 plugin.json 缺失 ==")
shutil.copytree(SB / "pristine_plugin",
                SB / "home/plugins/marketplaces/my-experts/plugins" / NAME)
pre = snap_state()          # 先快照，再制造缺陷
pj.unlink()
r = run_tool("--version", "1.0.3")
check("4.1 默认中止（退出码 2）", r.returncode == 2, "rc=%d" % r.returncode)
check("4.2 提示修复或 --force", "plugin.json" in r.stderr and "--force" in r.stderr)
post = snap_state()
check("4.3 中止后无任何变更", post["user"] == pre["user"] and post["mount"] == pre["mount"]
      and post["skill_zip"] == pre["skill_zip"])
print("  -- --force 跳过异常专家包 --")
r = run_tool("--version", "1.0.3", "--force")
check("4.4 --force 退出码 0", r.returncode == 0, r.stdout[-300:] + r.stderr[-200:])
check("4.5 输出含跳过声明", "跳过" in r.stdout and "滞后" in r.stdout)
check("4.6 异常专家包挂载未被触碰（保持 pristine 内容）",
      md5_file(SB / "home/plugins/marketplaces/my-experts/plugins" / NAME
               / "skills" / NAME / "SKILL.md") == pre["mount"]["SKILL.md"])
check("4.7 skill zip 版本戳 1.0.3",
      b"version=1.0.3" in zipfile.ZipFile(
          SB / "deploy/agent-design-patterns-skill.zip").comment)
# 还原 plugin.json（场景 5 需要可解析版本状态）
shutil.copyfile(SB / "pristine_plugin/.codebuddy-plugin/plugin.json", pj)

# ---------- 场景 5：安装实例漂移 ----------
print("\n== 场景 5：安装实例漂移（人为改动用户级 SKILL.md → 无版本参数修复）==")
user_md = SB / "home/skills" / NAME / "SKILL.md"
user_md.write_bytes(user_md.read_bytes() + "\n人为漂移行。\n".encode("utf-8"))
r = run_tool()
check("5.1 退出码 0", r.returncode == 0, r.stdout[-300:])
check("5.2 漂移被检出（输出含 漂移 1 项）", "漂移 1 项" in r.stdout)
check("5.3 漂移被修复（与源一致）", md5_file(user_md) == md5_file(skill_md))

# ---------- 汇总 ----------
fails = [x for x in results if not x[1]]
print("\n== 汇总：%d 项断言，%d 通过，%d 失败 ==" %
      (len(results), len(results) - len(fails), len(fails)))
for label, _, detail in fails:
    print("  FAIL:", label, detail)
shutil.rmtree(SB, ignore_errors=True)
print("沙箱已清理")
sys.exit(1 if fails else 0)
