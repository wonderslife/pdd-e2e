# -*- coding: utf-8 -*-
"""离线 UID 解析回归验证（不启浏览器）

为什么需要它
------------
`testcase-ai.py` 里「目标文本 -> uid」的定位逻辑（find_uid / _resolve_uid /
_nearby_text）改一行就可能悄悄回归，而真机跑一遍 E2E 要 1~2 分钟还得起前后端。
本工具把「已抓到的真实 MCP 快照」直接喂给引擎里的 SnapshotParser，
单测这一步的解析结果，秒级出结论。

典型用法
--------
    python tests/tools/verify-uid-offline.py \
        --engine tests/testcase-ai.py \
        --snapshot path/to/snap-20260918-095201.txt \
        --expect "fill:例如 RM-A-001:22_201" \
        --expect "click:查询:22_205"

`--expect` 格式：``action:target:期望uid``（target 里允许有空格和冒号，
解析时按「第一个冒号前是 action、最后一个冒号后是 uid」切分）。
期望 uid 写成 ``-`` 表示「应当**匹配不到**任何元素」（回归用：确认目标不存在时
不会退化成点到 RootWebArea 这类结构性节点）。

快照从哪来
----------
引擎每次解析前都会把快照落盘到
``<项目>/test-result/run-*/snapshots/snap-*.txt``，
从那里挑一个能复现场景的文件即可（例如登录页、扫码页各留一份）。

退出码：全部命中 0，有未命中 1。
"""
from __future__ import annotations

import argparse
import importlib.util
import sys


def load_engine(path: str):
    """按文件路径加载 testcase-ai.py（文件名带连字符，不能直接 import）。"""
    spec = importlib.util.spec_from_file_location("tcai_engine", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["tcai_engine"] = module
    spec.loader.exec_module(module)
    return module


def parse_expect(raw: str):
    """'fill:例如 RM-A-001:22_201' -> ('fill', '例如 RM-A-001', '22_201')"""
    first = raw.find(":")
    last = raw.rfind(":")
    if first <= 0 or last <= first:
        raise ValueError(f"--expect 格式应为 action:target:uid，收到 {raw!r}")
    return raw[:first].strip(), raw[first + 1:last].strip(), raw[last + 1:].strip()


def main() -> int:
    ap = argparse.ArgumentParser(description="离线验证 testcase-ai.py 的 UID 解析")
    ap.add_argument("--engine", required=True, help="testcase-ai.py 路径")
    ap.add_argument("--snapshot", required=True, help="MCP 快照文本文件路径")
    ap.add_argument("--expect", action="append", default=[],
                    help="action:target:期望uid，可重复")
    args = ap.parse_args()

    if not args.expect:
        print("[ERROR] 至少给一个 --expect")
        return 2

    engine = load_engine(args.engine)

    with open(args.snapshot, "r", encoding="utf-8") as f:
        text = f.read()

    parser = engine.SnapshotParser()
    parser.parse(text)
    print(f"快照: {args.snapshot}")
    print(f"解析元素数: {len(parser.elements)}  (element_lines={len(parser.element_lines)})")
    print("-" * 70)

    cache: dict = {}
    total = hit = 0
    for raw in args.expect:
        action, target, want = parse_expect(raw)
        total += 1
        step = {"action": action, "target": target, "desc": target}
        got = engine._resolve_uid(step, parser, cache)
        got_role = ""
        if got and got in parser.elements:
            got_role = parser.elements[got].role
        # 期望 "-" 表示「不应匹配到任何元素」
        if want in ("-", "None", ""):
            ok = got is None
            shown = "-"
        else:
            ok = got == want
            shown = want
        hit += ok
        flag = "PASS" if ok else "BAD "
        print(f"[{flag}] {action:6s} {target!r} -> {got} (role={got_role!r})  期望 {shown}")

    print("-" * 70)
    print(f"结果: {hit}/{total} 通过")
    return 0 if hit == total else 1


if __name__ == "__main__":
    sys.exit(main())
