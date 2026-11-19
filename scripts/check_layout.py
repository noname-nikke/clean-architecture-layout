#!/usr/bin/env python3
"""启发式检查项目目录是否符合「整洁架构：内外分离 + 按共享模型聚合用例」。

用法:
    python check_layout.py <项目根目录> [--depth N]

只做结构诊断，不做语义判断；结论仍需用 SKILL.md 的判定表复核。
"""

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

NOISE_DIRS = {
    ".git", ".hg", ".svn", ".venv", "venv", "env", "node_modules", "__pycache__",
    "dist", "build", "target", "out", "bin", "obj", "coverage", ".next", "vendor",
    ".idea", ".vscode", ".mypy_cache", ".pytest_cache", ".ruff_cache",
}
CODE_EXT = {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".java", ".kt", ".cs", ".php", ".rb", ".rs"}
DOMAIN_DIRS = {"domain", "entities", "model", "models"}
APP_DIRS = {"application", "usecase", "usecases", "use_cases", "services"}
ADAPTER_DIRS = {"adapters", "adapter", "infra", "infrastructure", "gateway", "gateways"}
CORE_LAYERS = DOMAIN_DIRS | APP_DIRS | ADAPTER_DIRS
LAYER_ALL = CORE_LAYERS | {"api", "web", "controller", "controllers", "repository", "repositories", "app", "core"}
FALLBACK_DIRS = {"utils", "util", "helpers", "helper", "tools", "tool", "common", "misc", "lib", "libs", "shared"}
WRAPPERS = {"src", "internal", "lib", "packages", "modules", "source"}
APP_META = {"__init__", "index", "mod", "ports", "port", "dto", "dtos", "schema", "schemas",
            "types", "errors", "exceptions", "config", "main", "router", "routes", "settings"}
DUP_BASES = {"db", "database", "dao", "repo", "repository", "model", "entity", "helper", "util", "utils", "client"}
VERSION_SUFFIX = re.compile(r"(_v\d+|_old|_new|_bak|_backup|_copy|-v\d+|-old|-new)$", re.I)


def code_files(root: Path, depth: int) -> list[Path]:
    out, stack = [], [(root, 0)]
    while stack:
        cur, d = stack.pop()
        if d > depth:
            continue
        try:
            entries = list(cur.iterdir())
        except (PermissionError, OSError):
            continue
        for e in entries:
            if e.is_dir():
                if e.name.lower() in NOISE_DIRS or e.name.startswith("."):
                    continue
                stack.append((e, d + 1))
            elif e.suffix.lower() in CODE_EXT:
                out.append(e)
    return out


def child_dirs(path: Path) -> list[Path]:
    try:
        return sorted([p for p in path.iterdir() if p.is_dir() and p.name.lower() not in NOISE_DIRS
                       and not p.name.startswith(".")], key=lambda p: p.name.lower())
    except (PermissionError, OSError):
        return []


def layer_hits(path: Path) -> list[str]:
    return [d.name for d in child_dirs(path) if d.name.lower() in LAYER_ALL]


def core_hits(path: Path) -> list[str]:
    return [d.name for d in child_dirs(path) if d.name.lower() in CORE_LAYERS]


def stems_in(path: Path) -> set[str]:
    try:
        return {p.stem for p in path.iterdir() if p.is_file() and p.suffix.lower() in CODE_EXT}
    except (PermissionError, OSError):
        return set()


def unwrap_wrapper(root: Path) -> Path:
    base = root
    for _ in range(3):
        kids = child_dirs(base)
        wrappers = [k for k in kids if k.name.lower() in WRAPPERS]
        if len(wrappers) == 1 and len(kids) <= 2:
            base = wrappers[0]
            continue
        break
    return base


def main() -> int:
    ap = argparse.ArgumentParser(description="整洁架构目录结构体检")
    ap.add_argument("root", help="项目根目录")
    ap.add_argument("--depth", type=int, default=6, help="扫描深度，默认 6")
    args = ap.parse_args()

    root = Path(args.root).expanduser().resolve()
    if not root.exists():
        print(f"路径不存在: {root}")
        return 2

    files = code_files(root, args.depth)
    if not files:
        print(f"在 {root} 下未找到源码文件（深度 {args.depth}）")
        return 1

    base = unwrap_wrapper(root)
    tops = child_dirs(base)
    layer_split = [d for d in tops if d.name.lower() in CORE_LAYERS]
    modules, fallbacks, others = [], [], []
    for d in tops:
        core = core_hits(d)
        if len([x for x in core if x.lower() in CORE_LAYERS]) >= 2:
            modules.append(d)
        elif d.name.lower() in FALLBACK_DIRS:
            fallbacks.append(d)
        else:
            others.append(d)

    print(f"项目根: {root}")
    print(f"分析目录: {base}    源码文件: {len(files)}")

    print("\n== 1. 顶层划分 ==")
    if layer_split:
        print(f"[!] 按层分包: {', '.join(d.name + '/' for d in layer_split)} 直接位于 {base.name}/ 之下")
        print("    症状: 新增一个完整功能要在这几个目录之间来回跳，业务被拆散。")
    if modules:
        print(f"[OK] 业务模块 {len(modules)} 个:")
        for m in modules:
            n = len(code_files(m, args.depth))
            layers = ", ".join(layer_hits(m)) or "无"
            print(f"    - {m.name}/  ({n} 个源码文件; 子层: {layers})")
    if not modules and not layer_split:
        print("[!] 既没有模块化结构，也没有分层结构，疑似平铺/大杂烩。")
    for d in fallbacks:
        n = len(code_files(d, args.depth))
        print(f"[?] 兜底/共享目录 {d.name}/  ({n} 个源码文件): 确认只放纯技术设施，不放业务规则")
    for d in others:
        if d.name.lower() in CORE_LAYERS:
            continue
        n = len(code_files(d, args.depth))
        if n:
            print(f"[i] 其他目录 {d.name}/  ({n} 个源码文件)")

    print("\n== 2. 三个验收问题 ==")
    domain_of, adapters_of, use_cases = {}, {}, defaultdict(list)
    for m in modules:
        hits = {h.lower(): h for h in layer_hits(m)}
        dname = next((hits[k] for k in DOMAIN_DIRS if k in hits), None)
        aname = next((hits[k] for k in APP_DIRS if k in hits), None)
        adname = next((hits[k] for k in ADAPTER_DIRS if k in hits), None)
        if dname:
            domain_of[m.name] = dname
        if aname:
            app_dir = m / aname
            for f in sorted(app_dir.rglob("*")):
                if f.is_file() and f.suffix.lower() in CODE_EXT and f.stem.lower() not in APP_META \
                        and not any(part.lower() in {"tests", "test", "__tests__"} for part in f.parts):
                    use_cases[m.name].append(f.stem)
        if adname:
            adapters_of[m.name] = adname

    if domain_of:
        print("Q1 业务规则在哪?   可答 → " + ", ".join(f"{k}/{v}" for k, v in domain_of.items()))
    elif layer_split:
        print("Q1 业务规则在哪?   只能答到全局层目录（所有业务模型混在一起），无法定位到具体业务")
    else:
        print("Q1 业务规则在哪?   无法回答（没有模块级 domain/）")

    if use_cases:
        print("Q2 对外有哪些用例? 可答 → 各模块 application/ 一文件一用例:")
        for k, v in use_cases.items():
            print(f"    - {k}: {', '.join(sorted(set(v))) or '未发现用例文件'}")
    elif layer_split:
        print("Q2 对外有哪些用例? 只能答到全局 application 目录，需逐个打开文件才知道归属哪个业务")
    else:
        print("Q2 对外有哪些用例? 无法回答（application/ 下没有用例文件）")

    if adapters_of:
        print("Q3 换存储改哪里?   可答 → " + ", ".join(f"{k}/{v}" for k, v in adapters_of.items()))
    elif layer_split:
        print("Q3 换存储改哪里?   只能答到全局 adapters 目录，且无法判断哪个实现属于哪个业务")
    else:
        print("Q3 换存储改哪里?   无法回答（没有模块级 adapters/）")

    print("\n== 3. 重复与混乱信号 ==")
    alerts = []
    stems_by_module = defaultdict(set)
    for m in modules:
        hits = {h.lower(): h for h in layer_hits(m)}
        for key in DOMAIN_DIRS:
            if key in hits:
                for s in stems_in(m / hits[key]):
                    stems_by_module[s].add(m.name)
    for s, mods in sorted(stems_by_module.items()):
        if len(mods) > 1:
            alerts.append(f"模型 {s} 同时出现在模块 {sorted(mods)} → 判定是否应合并为一个模块")

    layer_domain = next((d for d in layer_split if d.name.lower() in DOMAIN_DIRS), None)
    if layer_domain:
        for s in sorted(stems_in(layer_domain)):
            if VERSION_SUFFIX.search(s):
                alerts.append(f"{layer_domain.name}/{s} 疑似并行副本版本 → 收敛为单一定义")

    for m in modules:
        hits = {h.lower(): h for h in layer_hits(m)}
        for key in DOMAIN_DIRS:
            if key in hits:
                for s in sorted(stems_in(m / hits[key])):
                    if VERSION_SUFFIX.search(s):
                        alerts.append(f"{m.name}/{hits[key]}/{s} 疑似并行副本版本 → 收敛为单一定义")

    groups = defaultdict(list)
    for f in files:
        stem = f.stem.lower()
        base_name = re.sub(r"[\d_]+$", "", stem)
        if base_name in DUP_BASES:
            groups[base_name].append(str(f.relative_to(root)))
    for s, paths in sorted(groups.items()):
        if len(paths) > 1:
            alerts.append(f"疑似重复实现（{s}*）{len(paths)} 处: " +
                          ", ".join(paths[:4]) + (" …" if len(paths) > 4 else ""))

    for d in fallbacks:
        n = len(code_files(d, args.depth))
        if n >= 5:
            alerts.append(f"兜底目录 {d.name}/ 已有 {n} 个文件 → 逐个归类到 domain（含业务规则）或 shared（纯技术）")

    if not alerts:
        print("[OK] 未发现重复模型、并行副本或兜底目录膨胀。")
    for a in alerts:
        print(f"[!] {a}")

    print("\n== 4. 结论 ==")
    score = 0
    score += 1 if modules else 0
    score += 1 if domain_of else 0
    score += 1 if use_cases else 0
    score += 1 if adapters_of else 0
    score += 1 if not layer_split else 0
    verdict = "方向正确" if score >= 4 else ("骨架基本就位" if score >= 3 else "结构尚未成型")
    print(f"结构得分 {score}/5（模块化 / 模块级 domain / 用例可见 / 模块级 adapters / 未按层切顶层）→ {verdict}")
    if score >= 4 and not alerts:
        print("继续用三个成本判据（定位、阅读、波及）在真实改动中验证。")
    elif score >= 3:
        print("优先处理上面 [!] 项，再做模块边界合并。")
    else:
        print("先列对外用例清单，按「共用同一领域模型与端口接口」划模块，参考 references/migration-playbook.md。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
