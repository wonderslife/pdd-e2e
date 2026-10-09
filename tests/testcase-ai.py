"""
AI Test Framework v2.1 - 通用 AI 测试框架（含思维链）
======================================================
基于 Chrome DevTools MCP + LLM 的 YAML 驱动 E2E 测试执行器

v2.1 新增:
  🧠 LLM 思维链：每步执行前后调用大模型输出决策思考过程
  📝 智能分析：元素匹配推理、操作风险评估、断言预测
  💭 可视化思考：清晰展示模型的"为什么这样做"

v2.0 改进:
  ✅ 完整执行保证：所有步骤强制执行，支持 continue_on_error 策略
  ✅ 智能重试机制：自动重试失败操作（可配置次数和间隔）
  ✅ 增强元素匹配：多策略匹配 + 同义词扩展 + 位置感知
  ✅ 完整断言系统：10+ 断言类型，支持复合断言和置信度
  ✅ 插件化架构：支持自定义 Action 和 Assertion 扩展

用法:
  python testcase-ai.py                          # 列出用例
  python testcase-ai.py --all                     # 全部运行
  python testcase-ai.py tc2-zccz                  # 运行目录
  python testcase-ai.py testcases/tc2-zccz/asset-eval-apply.yaml
  python testcase-ai.py --think                   # 启用思维链输出
  python testcase-ai.py --think-deep              # 深度思维模式
"""

import asyncio
import copy
import json
import os
import re
from pathlib import Path


def _safe_json_dumps(obj, **kwargs):
    """JSON序列化，自动处理非标准类型（date/datetime/bytes等）"""
    def _default(o):
        if hasattr(o, 'isoformat'):
            return o.isoformat()
        if isinstance(o, (bytes, bytearray)):
            return o.decode('utf-8', errors='replace')
        if hasattr(o, '__dict__'):
            return o.__dict__
        return str(o)
    try:
        return json.dumps(obj, **kwargs)
    except (TypeError, ValueError):
        return json.dumps(obj, default=_default, **kwargs)
import shutil
import sys
import tempfile
import time
import traceback
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union

import yaml
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


# ============================================================
# LLM 配置区
# ============================================================

LLM_CONFIG = {
    "enabled": True,
    "base_url": os.environ.get("LLM_BASE_URL", "http://10.0.11.6:8005/v1"),
    "api_key": os.environ.get("LLM_API_KEY", "APIKEY"),
    "model": os.environ.get("LLM_MODEL", "gemma-4-26B-A4B-it"),
    "temperature": 0.3,
    "max_tokens": 2048,
    "timeout": 30,
    "think_mode": "auto",
}

try:
    from openai import OpenAI
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False


# ============================================================
# MCP 配置区
# ============================================================
# Chrome DevTools MCP 连接参数（Isolated 隔离模式）
# ============================================================

def _create_incognito_server_params() -> StdioServerParameters:
    """创建使用隔离模式 Chrome 的 MCP 连接参数

    chrome-devtools-mcp 通过 --chromeArg=VALUE 格式传递额外 Chrome 启动参数
    参考: https://github.com/ChromeDevTools/chrome-devtools-mcp/pull/338

    重要: --chromeArg 仅在 chrome-devtools-mcp 自己启动 Chrome 时生效，
    如果连接到已存在的 Chrome 实例则参数会被忽略。

    注意: 不使用 --incognito 参数！
    原因: --incognito + --isolated 会导致 Chrome 打开两个窗口：
    1) Incognito 窗口（无操作） 2) 普通窗口（实际操作在此）
    这是因为 Puppeteer 连接的是浏览器默认目标页面而非 Incognito 页面。
    --isolated 本身已提供隔离（临时用户数据目录），无需 --incognito。
    """
    npx_args = [
        "-y", "chrome-devtools-mcp@latest",
        "--isolated",                    # 使用临时用户数据目录（隔离模式）
        "--chromeArg=--no-first-run",
        "--chromeArg=--no-default-browser-check",
        "--chromeArg=--disable-sync",
        "--chromeArg=--disable-extensions",
        "--chromeArg=--disable-component-extensions-with-background-pages",
        "--chromeArg=--disable-popup-blocking",
        "--chromeArg=--ignore-certificate-errors",
        "--chromeArg=--ignore-certificate-errors-spki-list",
        "--chromeArg=--disable-web-security",
        "--chromeArg=--allow-running-insecure-content",
        "--chromeArg=--unsafely-treat-insecure-origin-as-secure",
        "--chromeArg=--disable-password-manager-reauthentication",
        "--chromeArg=--disable-features=PasswordLeakDetection",
        "--chromeArg=--disable-features=SafeBrowsingPasswordProtectionTrigger",
        "--chromeArg=--disable-save-password-bubble",
        "--chromeArg=--password-store=basic",
    ]

    viewport_w = os.environ.get("BROWSER_VIEWPORT_WIDTH") or os.environ.get("BROWSER_WIDTH", "1366")
    viewport_h = os.environ.get("BROWSER_VIEWPORT_HEIGHT") or os.environ.get("BROWSER_HEIGHT", "768")
    npx_args.append(f"--chromeArg=--window-size={viewport_w},{viewport_h}")

    # 优先使用本地构建的 chrome-devtools-mcp（避免 npx 联网拉包卡死/超时）
    # 环境变量 PDD_MCP_PATH 可覆盖；未指定时探测常见本地路径
    local_mcp = os.environ.get("PDD_MCP_PATH") or ""
    if not local_mcp:
        for cand in (
            os.path.join(PROJECT_ROOT, "node_modules", "chrome-devtools-mcp", "build", "src", "bin", "chrome-devtools-mcp.js"),
            r"E:\ZHAI\APPPROJECT\pdd-test-system\chrome-devtools-mcp-main\build\src\bin\chrome-devtools-mcp.js",
            r"D:\APPPROJECTS\chrome-devtools-mcp-main\chrome-devtools-mcp-main\build\src\bin\chrome-devtools-mcp.js",
        ):
            if os.path.exists(cand):
                local_mcp = cand
                break
    if local_mcp and os.path.exists(local_mcp):
        print(f"[MCP] 使用本地构建: {local_mcp}")
        return StdioServerParameters(
            name="Chrome DevTools MCP (Local)",
            command="node",
            args=[local_mcp] + npx_args,
            env=None,
        )

    return StdioServerParameters(
        name="Chrome DevTools MCP (Isolated)",
        command="npx",
        args=npx_args,
        env=None,
    )


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
os.environ.setdefault("PROJECT_ROOT", PROJECT_ROOT)
# RUN_TAG：本批次唯一标签（套件 runner 会在外层设置一次，所有用例共享；
# 单独跑用例时自动生成，保证测试数据名跨运行不撞库唯一索引）
os.environ.setdefault("RUN_TAG", time.strftime("%m%d%H%M%S"))

# 将项目根加入 sys.path，保证 `from tests.framework.xxx import ...` 包导入可用
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

SERVER_PARAMS = _create_incognito_server_params()

TESTCASES_ROOT = os.path.join(PROJECT_ROOT, "testcases")
RESULT_BASE_DIR = os.path.join(PROJECT_ROOT, "test-result")
ENV_FILE_PATH = os.path.join(BASE_DIR, ".env.test")

# wait_after(type=time) 的单步等待上限（秒）。
# 原值 10s 是硬编码在 _handle_wait 里的 min(duration, 10.0)，会把
# 「停留 15 秒」这类诉求静默截断成 10s —— 用例作者无法察觉。
_MAX_WAIT_AFTER_SEC = 60.0

DEFAULT_CONFIG = {
    "max_retries": 3,
    "retry_delay": 1.0,
    "default_wait": 2.0,
    "snapshot_timeout": 10.0,
    "element_wait_timeout": 5.0,
    "continue_on_error": True,
    "screenshot_on_error": True,
    "verbose_logging": True,
    "llm_think_enabled": False,
    "llm_think_deep": False,
}


# ============================================================
# 数据模型
# ============================================================

INTERACTIVE_ROLES = frozenset({
    "button", "link", "textbox", "input", "combobox", "select",
    "checkbox", "radio", "menuitem", "option", "tab", "spinbutton",
    "treeitem", "slider", "switch",
    # uni-app 的搜索类输入框在快照里是 searchbox（既不是 textbox 也不是 search）。
    # 漏掉它会让这类输入框既不算交互元素、也进不了邻近文本的加分名单，
    # fill 会直接报「无候选元素」。
    "searchbox",
})

INPUT_ROLES = frozenset({"textbox", "input", "textarea", "combobox", "select",
                         "search", "searchbox"})


class StepStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    FAILED_ASSERT = "failed_assert"
    SKIPPED = "skipped"
    ERROR = "error"
    RETRIED = "retried"


@dataclass
class SnapshotElement:
    uid: str
    role: str = ""
    name: str = ""
    text: str = ""
    value: str = ""
    attributes: Dict[str, str] = field(default_factory=dict)
    raw_line: str = ""
    indent_level: int = 0
    # 是否位于**当前打开的模态对话框**内部。
    # 用途：弹窗打开时，页面背后往往有同名控件（如列表页的「机房名称」搜索框
    # 与新增弹窗里的「机房名称」必填项），命中歧义时必须优先取弹窗内的那个。
    in_modal: bool = False
    # 本次快照里该 uid 是否被**多个节点复用**（见 SnapshotParser._mark_reused_uids）。
    # MCP 的 click/fill 是按 uid 定位的，复用 uid 点不到（报 no longer exists）。
    uid_reused: bool = False

    @property
    def combined_text(self) -> str:
        parts = [self.role, self.name, self.text, self.value]
        return " ".join(p for p in parts if p).lower()

    @property
    def is_disabled(self) -> bool:
        """a11y 行内显式标注 disabled。

        背景（pc-002 步骤13 实测）：机房列表页有**工具栏「修改」按钮（disabled，
        需先勾选行才启用）**和每行的「修改」按钮，同文本同角色。工具栏按钮的
        快照行带 `disableable disabled` 标注，但旧逻辑只看 role → 两者
        is_interactive 同为 True → 打平后「uid 唯一性」把**禁用的工具栏按钮**
        排到前面 → 点了它 = 无操作，编辑弹窗根本没打开，后续 fill/提交全部
        落在隐藏 DOM 上静默假阳性。
        """
        if str(self.attributes.get("disabled", "")).lower() == "true":
            return True
        # \bdisabld\b 不会误伤 "disableable"（后者不含完整的 disabled 词）
        return bool(re.search(r"\bdisabled\b", self.raw_line or ""))

    @property
    def is_interactive(self) -> bool:
        if self.is_disabled:
            return False
        return self.role in INTERACTIVE_ROLES

    @property
    def is_visible(self) -> bool:
        return self.role not in ("ignored",) and self.role != ""

    @property
    def is_readonly(self) -> bool:
        return "readonly" in self.raw_line.lower() or self.attributes.get("readonly") == "true"


@dataclass
class StepResult:
    step_num: int
    desc: str
    action: str
    status: StepStatus
    mcp_tool: str = ""
    mcp_args: Dict[str, Any] = field(default_factory=dict)
    output: str = ""
    error: str = ""
    assertions: List[Dict[str, Any]] = field(default_factory=list)
    duration_ms: int = 0
    retry_count: int = 0
    snapshot_before: str = ""
    snapshot_after: str = ""
    snapshot_path: str = ""
    thinking: str = ""           # LLM 思考过程（思维链）
    thinking_pre: str = ""       # 执行前思考
    thinking_post: str = ""      # 执行后反思
    llm_confidence: float = 0.0  # LLM 置信度
    llm_suggestions: List[str] = field(default_factory=list)  # LLM 建议


@dataclass
class TestcaseResult:
    test_id: str
    title: str
    priority: str
    yaml_file: str
    timestamp: str
    config: Dict[str, Any] = field(default_factory=dict)
    steps: List[StepResult] = field(default_factory=list)
    screenshots: List[str] = field(default_factory=list)
    log_lines: List[str] = field(default_factory=list)
    env_used: Dict[str, str] = field(default_factory=dict)

    @property
    def total_steps(self) -> int:
        return len(self.steps)

    @property
    def passed_count(self) -> int:
        return sum(1 for s in self.steps if s.status == StepStatus.SUCCESS)

    @property
    def failed_count(self) -> int:
        return sum(1 for s in self.steps if s.status in (StepStatus.FAILED, StepStatus.FAILED_ASSERT, StepStatus.ERROR))

    @property
    def skipped_count(self) -> int:
        return sum(1 for s in self.steps if s.status == StepStatus.SKIPPED)

    @property
    def pass_rate(self) -> float:
        if self.total_steps == 0:
            return 0.0
        executed = self.total_steps - self.skipped_count
        if executed == 0:
            return 0.0
        return (self.passed_count / executed) * 100

    @property
    def overall_status(self) -> str:
        if self.failed_count == 0 and self.skipped_count == 0:
            return "PASS"
        elif self.passed_count > 0:
            return "PARTIAL"
        else:
            return "FAIL"


# ============================================================
# 工具函数
# ============================================================

def resolve_env_vars(value):
    """解析环境变量 ${VAR} 和 ${VAR:-default} 格式"""
    if not isinstance(value, str):
        return value

    def replacer(match):
        var_expr = match.group(1)
        if ":-" in var_expr:
            var_name, default = var_expr.split(":-", 1)
            return os.environ.get(var_name.strip(), default.strip())
        resolved = os.environ.get(var_expr.strip())
        if resolved is None:
            return match.group(0)
        return resolved

    return re.sub(r"\$\{([^}]+)\}", replacer, value)


def _resolve_includes(testcase: Dict, base_dir: str, depth: int = 0) -> Dict:
    """解析 _include 字段，将共享步骤合并到当前测试用例
    
    Args:
        testcase: 已加载的 YAML 字典
        base_dir: 基础目录（用于解析相对路径）
        depth: 当前递归深度（防止循环引用，最大3层）
    
    Returns:
        合并后的 testcase 字典（steps 已包含被引用文件的步骤）
    """
    indent = "  " * depth
    current_file = testcase.get("test_id", "?")
    
    from pathlib import Path
    
    log(f"{indent}[_include] 开始解析 | 文件={current_file} | 深度={depth}", 1)
    
    if depth > 3:
        log(f"{indent}[_include] ❌ 超过最大嵌套深度(3)，停止递归", 2)
        return testcase

    include_path = testcase.get("_include")
    if not include_path:
        log(f"{indent}[_include] 无 _include 字段，跳过", 3)
        return testcase

    if not isinstance(include_path, str):
        log(f"{indent}[_include] ❌ _include 必须是字符串路径，实际类型={type(include_path).__name__}", 2)
        return testcase

    resolved_path = Path(base_dir) / include_path
    abs_path = str(resolved_path.resolve())
    
    if not resolved_path.exists():
        log(f"{indent}[_include] ❌ 引用文件不存在: {abs_path}", 1)
        del testcase["_include"]
        return testcase

    log(f"{indent}[_include] 📂 加载共享模块:", 1)
    log(f"{indent}         路径: {abs_path}", 1)

    with open(resolved_path, "r", encoding="utf-8") as _f:
        included = yaml.safe_load(_f)

    if not included or not isinstance(included, dict):
        log(f"{indent}[_include] ❌ 引用文件格式错误(非dict或空): {include_path}", 2)
        del testcase["_include"]
        return testcase

    included_id = included.get("test_id", "?")
    log(f"{indent}[_include] 📋 共享模块 ID: {included_id}", 2)

    included = _resolve_includes(included, str(resolved_path.parent), depth + 1)

    included_steps = included.get("steps", [])
    current_steps = testcase.get("steps", [])

    log(f"{indent}[_include] ── 合并前统计 ──", 1)
    log(f"{indent}         共享模块({included_id}) 步骤数: {len(included_steps)}", 1)
    log(f"{indent}         当前文件({current_file}) 步骤数: {len(current_steps)}", 1)

    if included_steps:
        log(f"{indent}         共享步骤明细:", 2)
        for i, s in enumerate(included_steps):
            desc = s.get("desc", s.get("target", "?"))
            action = s.get("action", "?")
            step_num = s.get("step", "?")
            log(f"{indent}           [{step_num}] {action}: {desc}", 2)

    if current_steps:
        log(f"{indent}         当前文件步骤明细:", 2)
        for i, s in enumerate(current_steps):
            desc = s.get("desc", s.get("target", "?"))
            action = s.get("action", "?")
            step_num = s.get("step", "?")
            log(f"{indent}           [{step_num}] {action}: {desc}", 2)

    merged_steps = list(included_steps) + list(current_steps)
    step_offset = len(included_steps)
    
    renumbered = []
    for idx, s in enumerate(merged_steps):
        old_num = s.get("step", 0)
        new_num = old_num
        
        source_tag = ""
        if idx < step_offset:
            source_tag = f"[共享:{included_id}]"
        else:
            source_tag = "[本文件]"
            if old_num:
                try:
                    new_num = int(old_num) + step_offset
                    s["step"] = new_num
                except (TypeError, ValueError):
                    pass
        
        desc = s.get("desc", s.get("target", "?"))
        action = s.get("action", "?")
        
        renumbered.append(f"  #{new_num} {source_tag} {action}: {desc}")
        
        log(f"{indent}         → #{new_num} {source_tag} "
            f"action={action} target='{s.get('target', '')}' "
            f"(原编号={old_num})", 3)

    testcase["steps"] = merged_steps
    testcase["_included_from"] = include_path
    del testcase["_include"]

    log(f"{indent}[_include] ✅ 合并完成:", 1)
    log(f"{indent}         总计: {len(merged_steps)} 步 (共享{len(included_steps)} + 本文件{len(current_steps)})", 1)
    log(f"{indent}         步骤偏移量: +{step_offset}", 2)
    log(f"{indent}         最终步骤序列:", 2)
    for line in renumbered:
        log(f"{indent}           {line}", 2)

    return testcase


def _expand_repeats(testcase: Dict) -> Dict:
    """把顶层 `repeat` 块在**加载期**展开成扁平 steps。

    YAML 写法::

        steps:                 # 可选，放在循环之前执行
          - action: navigate
            url: "..."
        repeat:
          times: 10            # 也接受 count / iterations
          as: "第 {i}/{n} 轮"   # 可选，拼在每步 desc 前（{i}=当前轮, {n}=总轮数）
          steps:
            - action: navigate
              url: "https://..."
              wait_after: {type: time, duration: 10000}
            - action: close_page
              pageId: current

    设计取舍：在加载期做**纯文本展开**，而不是往执行器里塞循环控制流。
    展开后所有下游逻辑（步骤编号、重试、失败策略、断言、报告）完全不变，
    因此这是零回归风险的加法。展开结果追加在顶层 steps 之后（order: before
    可改成之前）。
    """
    if not isinstance(testcase, dict):
        return testcase

    rep = testcase.get("repeat")
    if not rep or not isinstance(rep, dict):
        return testcase

    raw_steps = rep.get("steps")
    if not isinstance(raw_steps, list) or not raw_steps:
        log("[repeat] ⚠️ repeat.steps 为空，跳过展开", 1)
        del testcase["repeat"]
        return testcase

    raw_times = rep.get("times", rep.get("count", rep.get("iterations", 1)))
    # 支持 ${LOOP_TIMES} —— 用例级 .env 在 run_single_testcase 之前已加载，
    # 所以这里能安全取值；轮数不该逼着人改 YAML 本体。
    try:
        times = int(float(resolve_env_vars(str(raw_times))))
    except (TypeError, ValueError):
        log(f"[repeat] ⚠️ times 不是整数({raw_times!r})，按 1 次处理", 1)
        times = 1
    if times < 1:
        log(f"[repeat] ⚠️ times={times} < 1，按 1 次处理", 1)
        times = 1

    prefix_tpl = str(rep.get("as", rep.get("desc_prefix", "")) or "")
    order = str(rep.get("order", "after")).lower()

    expanded: List[Dict] = []
    for i in range(1, times + 1):
        for raw in raw_steps:
            if not isinstance(raw, dict):
                continue
            s = copy.deepcopy(raw)
            if prefix_tpl:
                pfx = prefix_tpl.replace("{i}", str(i)).replace("{n}", str(times))
                s["desc"] = f"{pfx} {s.get('desc', '')}".strip()
            # 供断言/日志引用轮次（env 变量展开走 resolve_env_vars，故用 os.environ 传递）
            s.setdefault("_repeat_index", i)
            s.setdefault("_repeat_total", times)
            expanded.append(s)

    head = list(testcase.get("steps") or [])
    merged = (head + expanded) if order != "before" else (expanded + head)

    for idx, s in enumerate(merged, 1):
        s["step"] = idx
    testcase["steps"] = merged
    testcase["_repeat_expanded"] = {"times": times, "per_iteration": len(raw_steps)}

    log(f"[repeat] 🔁 展开 {times} 轮 × {len(raw_steps)} 步 = {len(expanded)} 步"
        f"（前置 {len(head)} 步，位置={order}）", 1)

    del testcase["repeat"]
    return testcase


def _load_env_from_file():
    """从 .env 文件加载环境变量（优先级：.env.local > .env.test）"""
    import re as _re
    from pathlib import Path

    env_files = [
        Path(ENV_FILE_PATH),
        Path(BASE_DIR) / ".env.local",
    ]

    for env_file in env_files:
        if env_file.exists():
            loaded_count = 0
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    match = _re.match(r'^([A-Za-z_][A-Za-z0-9_]*)=(.*)$', line)
                    if match:
                        key, value = match.group(1), match.group(2).strip()
                        if (value.startswith('"') and value.endswith('"')) or \
                           (value.startswith("'") and value.endswith("'")):
                            value = value[1:-1]
                        if key not in os.environ:
                            os.environ[key] = value
                            loaded_count += 1

            if loaded_count > 0:
                log(f"📂 从 {env_file.name} 加载了 {loaded_count} 个环境变量")
            break


def _load_testcase_env(yaml_path: str) -> Dict[str, str]:
    """从 YAML 同目录加载同名 .env 文件（如 asset-eval-apply.yaml → asset-eval-apply.env）

    返回加载的变量字典，用于执行后清理。
    """
    import re as _re
    from pathlib import Path

    yaml_path = Path(yaml_path)
    env_path = yaml_path.with_suffix('.env')
    loaded = {}

    if not env_path.exists():
        log(f"  [Env] 无配套 .env 文件: {env_path.name}", 2)
        return loaded

    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            match = _re.match(r'^([A-Za-z_][A-Za-z0-9_]*)=(.*)$', line)
            if match:
                key, value = match.group(1), match.group(2).strip()
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                # env 值支持 ${VAR} / ${VAR:-default} 组合（如
                # ROOM_NAME=自动化测试机房-${RUN_TAG}），未定义的变量原样保留
                value = resolve_env_vars(value)
                old_val = os.environ.get(key)
                os.environ[key] = value
                loaded[key] = old_val

    if loaded:
        log(f"  [Env] 📂 从 {env_path.name} 加载 {len(loaded)} 个变量: {list(loaded.keys())}", 1)
    return loaded


def log(msg: str, level: int = 0, timestamp: bool = True):
    prefix = "  " * level
    ts = f"[{time.strftime('%H:%M:%S')}]" if timestamp else ""
    print(f"{prefix}{ts} {msg}" if ts else f"{prefix}{msg}")


def deep_get(d: Dict, keys: str, default=None):
    """安全获取嵌套字典值"""
    keys = keys.split(".")
    for key in keys:
        if isinstance(d, dict):
            d = d.get(key, default)
        else:
            return default
    return d


# ============================================================
# 智能登录状态检测器
# ============================================================

class LoginStateDetector:
    """
    登录状态智能检测器 - 使用 LLM 判断当前是否已登录
    
    功能:
      1. 获取页面快照，分析当前页面状态
      2. 调用 LLM 判断是否已登录（基于 home_indicator 等标志）
      3. 自动识别并跳过登录相关步骤
      
    使用场景:
      - 测试用例包含登录步骤，但浏览器可能已处于登录状态
      - 避免重复登录导致的测试失败或时间浪费
      - 提高测试执行效率
    """
    
    DETECTION_PROMPT = """你是一个专业的 Web 应用状态检测 AI。

## 任务
判断当前用户是否已经登录了目标系统。

## 判断依据
1. **页面特征**: 当前页面显示的关键元素（如用户头像、姓名、已登录标志等）
2. **URL 特征**: 当前 URL 是否包含已登录后的路径特征
3. **元素存在性**: 是否存在登录表单 vs 已登录后的导航/内容区域

## 输出格式（严格 JSON）
{
  "is_logged_in": true/false,
  "confidence": 0.0-1.0,
  "reason": "判断理由（中文，简短）",
  "indicators": {
    "found": ["检测到的已登录标志"],
    "missing": ["缺失的未登录标志"]
  }
}

## 参考信息
- **期望的已登录标志 (home_indicator)**: {home_indicator}
- **登录页特征**: 包含"欢迎登录"、用户名输入框、密码输入框、登录按钮等
- **已登录后特征**: 包含首页内容、用户信息、导航菜单、工作台等

## 页面快照
{snapshot_summary}

请分析上述快照，判断用户是否已登录。只输出 JSON，不要其他内容。"""

    def __init__(self, session, parser, config: Dict[str, Any], think_engine=None):
        self.session = session
        self.parser = parser
        self.config = config
        self.think_engine = think_engine
        self.detection_result = None
        
    async def detect_login_state(self, context_check: Dict[str, Any]) -> Dict[str, Any]:
        """
        检测当前登录状态
        
        Args:
            context_check: YAML 中的 context_check 配置
            
        Returns:
            {
                "is_logged_in": bool,
                "confidence": float,
                "reason": str,
                "method": "llm" | "rule" | "fallback",
                "skipped_steps": List[int]
            }
        """
        home_indicator = context_check.get("home_indicator", "")
        login_url = context_check.get("login_url", "")
        
        log(f"🔍 开始检测登录状态...", 2)
        
        # 策略 1：使用 LLM 智能检测（优先）
        if self.think_engine and self.think_engine.enabled:
            result = await self._detect_with_llm(home_indicator)
            if result:
                self.detection_result = result
                return result
        
        # 策略 2：规则匹配（备选）
        result = await self._detect_with_rules(home_indicator, login_url)
        if result:
            self.detection_result = result
            return result
        
        # 策略 3：默认未登录（兜底）
        return {
            "is_logged_in": False,
            "confidence": 0.0,
            "reason": "无法检测，默认为未登录状态",
            "method": "fallback",
            "skipped_steps": []
        }
    
    async def _detect_with_llm(self, home_indicator: str) -> Optional[Dict]:
        """使用 LLM 进行智能检测"""
        try:
            snapshot_text = await self._get_snapshot_summary()
            if not snapshot_text:
                return None
            
            prompt = self.DETECTION_PROMPT.format(
                home_indicator=home_indicator,
                snapshot_summary=snapshot_text[:3000]
            )
            
            response = await self.think_engine._call_llm(prompt, max_tokens=500)
            if not response or not response.strip():
                return None
            
            import json
            # 清理响应文本，提取 JSON
            cleaned_response = response.strip()
            
            # 尝试直接解析
            try:
                result = json.loads(cleaned_response)
            except json.JSONDecodeError:
                # 尝试提取 JSON 对象（处理 markdown 代码块等情况）
                json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', cleaned_response, re.DOTALL)
                if json_match:
                    try:
                        result = json.loads(json_match.group())
                    except json.JSONDecodeError:
                        log(f"  ⚠️ LLM JSON 解析失败，尝试修复...", 3)
                        # 尝试修复常见的 JSON 格式问题
                        json_str = json_match.group()
                        json_str = re.sub(r',\s*([}\]])', r'\1', json_str)  # 移除尾部逗号
                        json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', json_str)  # 移除控制字符
                        try:
                            result = json.loads(json_str)
                        except json.JSONDecodeError as e2:
                            log(f"  ⚠️ LLM JSON 修复失败: {e2}", 3)
                            return None
                else:
                    return None
            
            is_logged_in = result.get("is_logged_in", False)
            confidence = result.get("confidence", 0)
            reason = result.get("reason", "")
            
            log(f"  🧠 LLM 判断: {'✅ 已登录' if is_logged_in else '❌ 未登录'} (置信度: {confidence:.0%})", 2)
            log(f"     理由: {reason}", 3)
            
            return {
                "is_logged_in": is_logged_in,
                "confidence": confidence,
                "reason": reason,
                "method": "llm",
                "skipped_steps": []
            }
                
        except Exception as e:
            log(f"  ⚠️ LLM 检测失败: {e}", 3)
        
        return None
    
    async def _detect_with_rules(self, home_indicator: str, login_url: str) -> Optional[Dict]:
        """使用规则进行快速检测"""
        try:
            snapshot_text = await self._get_snapshot_summary()
            if not snapshot_text:
                return None
            
            text_lower = snapshot_text.lower()
            indicator_lower = home_indicator.lower() if home_indicator else ""
            
            # 已登录标志检测
            logged_in_indicators = [
                indicator_lower,
                "个人工作台",
                "首页",
                "退出",
                "注销",
                "用户信息",
                "我的",
                "dashboard",
                "welcome",
                "已登录",
            ]
            
            # 未登录标志检测
            logged_out_indicators = [
                "欢迎登录",
                "请登录",
                "登录表单",
                "username",
                "password",
                "用户名",
                "密码",
                "sign in",
                "log in",
                "login",
            ]
            
            found_logged_in = sum(1 for ind in logged_in_indicators if ind and ind in text_lower)
            found_logged_out = sum(1 for ind in logged_out_indicators if ind and ind in text_lower)
            
            is_logged_in = found_logged_in > found_logged_out and found_logged_in > 0
            confidence = min(0.9, abs(found_logged_in - found_logged_out) / max(found_logged_in, found_logged_out, 1))
            
            reason = f"规则检测: 已登录标志={found_logged_in}, 未登录标志={found_logged_out}"
            
            log(f"  📋 规则判断: {'✅ 已登录' if is_logged_in else '❌ 未登录'} (置信度: {confidence:.0%})", 2)
            
            return {
                "is_logged_in": is_logged_in,
                "confidence": confidence,
                "reason": reason,
                "method": "rule",
                "skipped_steps": []
            }
            
        except Exception as e:
            log(f"  ⚠️ 规则检测失败: {e}", 3)
        
        return None
    
    async def _get_snapshot_summary(self) -> str:
        """获取页面快照摘要"""
        try:
            result = await self.session.call_tool("take_snapshot", {"verbose": True})
            snapshot_text = ""
            if result.content:
                for item in result.content:
                    if hasattr(item, 'text'):
                        snapshot_text += item.text + "\n"
                    else:
                        snapshot_text += str(item) + "\n"
            
            if snapshot_text:
                self.parser.parse(snapshot_text)
            
            return snapshot_text
        except Exception as e:
            log(f"  [Snapshot Error] {e}", 3)
            return ""
    
    def identify_login_steps(self, steps: List[Dict], context_check: Dict) -> Tuple[List[int], List[int]]:
        """
        识别哪些步骤属于登录流程
        
        Returns:
            (login_step_indices, post_login_step_indices)
        """
        login_steps = []
        post_login_steps = []
        
        login_keywords = [
            "登录", "login", "用户名", "密码", "username", "password",
            "凭据", "credential", "认证", "auth"
        ]
        
        for idx, step in enumerate(steps):
            step_text = " ".join([
                str(step.get("desc", "")),
                str(step.get("action", "")),
                str(step.get("target", ""))
            ]).lower()
            
            is_login_step = any(kw in step_text for kw in login_keywords)
            
            if is_login_step:
                login_steps.append(idx)
            else:
                post_login_steps.append(idx)
        
        return login_steps, post_login_steps


def should_skip_step(step_idx: int, detection_result: Dict, login_step_indices: List[int]) -> bool:
    """
    判断某个步骤是否应该被跳过
    
    Args:
        step_idx: 步骤索引（从 0 开始）
        detection_result: 登录检测结果
        login_step_indices: 登录步骤索引列表
        
    Returns:
        True 表示应该跳过
    """
    if not detection_result.get("is_logged_in"):
        return False
    
    return step_idx in login_step_indices


# 用例「自带登录」的判据：出现了带登录语义的填写/点击动作
_LOGIN_ACTION_WORDS = (
    "登 录", "登录", "登陆", "login", "sign in", "signin",
    "账号", "帐号", "用户名", "密码", "password", "username",
)
_LOGIN_ACTION_TYPES = frozenset({"fill", "type", "input", "click", "tap"})


def _case_self_handles_login(steps: List[Dict]) -> bool:
    """用例自身是否已经写了「填账号/密码 → 点登录」的动作。

    用于决定要不要走引擎的自动登录：
      - 返回 True  → 用例自己负责登录（pc-001 / h5-001），引擎不干预
      - 返回 False → 用例把登录态寄托在别处（pc-002~pc-00x / h5-002 / h5-003），
                     引擎按 context_check 自动登录

    只看「动作型」步骤（fill/click 等），不看 navigate 步骤的 desc ——
    h5-002 / h5-003 的步骤 1 描述里写着「完成登录」，但实际只是打开页面。
    同理** desc 一律不参与判定 **（实测 pc-009 步骤4 desc「…选中当前登录用户」
    含「登录」二字 → 误判为自带登录 → 跳过自动登录 → 全用例跑在登录页上 45%）。
    真实登录步骤的 target/value 本身就是「用户名/密码/登 录」，只看它们足够。
    """
    for step in steps or []:
        action = str(step.get("action", "")).lower()
        if action not in _LOGIN_ACTION_TYPES:
            continue
        text = " ".join([
            str(step.get("target", "")),
            str(step.get("value", "")),
        ]).lower()
        if any(word in text for word in _LOGIN_ACTION_WORDS):
            return True
    return False


# ============================================================
# LLM 思维链引擎 v2.1
# ============================================================

class ThinkChainEngine:
    """
    LLM 思维链引擎 - 为每步测试生成 AI 决策思考过程
    
    功能:
      1. 执行前分析：理解步骤意图、评估页面状态、预测操作结果
      2. 执行后反思：验证结果符合预期、分析异常原因、给出建议
    
    输出格式:
      🧠 [思考] 分析当前步骤的目标和上下文...
      🔍 [观察] 页面状态：检测到 X 个可交互元素...
      🎯 [决策] 选择元素 UID=xxx，理由是...
      ⚠️ [风险] 潜在问题：...
      💡 [建议] 后续步骤可能需要...
    """
    
    SYSTEM_PROMPT = """你是一个专业的 UI 测试自动化 AI 助手。
你的任务是为每个测试步骤生成结构化的思维链（Chain-of-Thought）输出。

## 你的角色
- 测试执行分析师：分析每步操作的合理性和可行性
- 风险评估员：识别潜在的操作失败点
- 问题诊断师：当步骤失败时，分析可能的原因

## 输出格式要求
请严格按照以下格式输出，使用中文：

### 执行前思考 (Pre-execution Thinking)
```
🧠 **目标理解**: [用一句话描述这步要做什么]
📊 **上下文分析**: 
   - 当前动作类型: {action}
   - 目标元素: {target}
   - 操作参数: {params}
🔍 **页面状态**: [基于快照描述当前可见的关键元素]
🎯 **元素匹配推理**:
   - 候选元素: [列出可能的匹配项]
   - 最佳选择: [最终选择的元素及原因]
   - 匹配置信度: [高/中/低] + 理由
⚠️ **风险评估**:
   - 风险等级: [低/中/高]
   - 可能失败原因: [...]
   - 缓解措施: [...]
💡 **预期结果**: [执行后应该看到什么]
```

### 执行后反思 (Post-execution Reflection)
```
✅ **执行状态**: [成功/失败/异常]
📋 **结果分析**: [实际发生了什么]
🔎 **断言预判**: [断言是否可能通过，为什么]
🚨 **问题诊断** (如果失败): [可能的原因和解决方案]
➡️ **下一步建议**: [对后续步骤的影响和建议]
```

## 重要约束
1. 保持简洁但信息丰富
2. 使用具体的观察数据，不要泛泛而谈
3. 如果无法确定，明确说明不确定性
4. 关注用户意图而非机械执行"""

    PRE_THINK_TEMPLATE = """## 测试步骤 {step_num} 执行前分析

### 步骤信息
- **描述**: {desc}
- **动作类型**: {action}
- **目标元素**: {target}
- **操作参数**: {params}

### 页面快照摘要
{snapshot_summary}

### 已知缓存元素
{cache_info}

### 请生成执行前思维链，包括：
1. 目标理解：这步要达成什么目的？
2. 元素匹配：如何找到正确的元素？
3. 风险评估：可能会遇到什么问题？
4. 预期结果：执行后应该看到什么？"""

    POST_THINK_TEMPLATE = """## 测试步骤 {step_num} 执行后反思

### 步骤信息
- **描述**: {desc}
- **动作类型**: {action}
- **执行状态**: {status}
- **耗时**: {duration_ms}ms
- **重试次数**: {retry_count}

### 执行前思考回顾
{pre_thinking}

### 执行结果
{execution_result}

### 断言结果
{assertion_results}

### 请生成执行后反思，包括：
1. 结果验证：是否符合预期？
2. 问题诊断：如果有异常，原因是什么？
3. 下一步影响：这对后续步骤有什么影响？"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = {**LLM_CONFIG, **(config or {})}
        self.client = None
        self.enabled = self.config.get("enabled", False) and LLM_AVAILABLE
        self.deep_mode = self.config.get("think_mode") == "deep"
        
        if self.enabled:
            try:
                self.client = OpenAI(
                    base_url=self.config["base_url"],
                    api_key=self.config["api_key"],
                )
                log(f"🧠 LLM 思维链已启用 | 模型: {self.config['model']}", 1)
            except Exception as e:
                log(f"⚠️ LLM 初始化失败: {e}", 1)
                self.enabled = False
                self.client = None

    async def pre_execute_think(self, step: Dict[str, Any], step_num: int,
                                parser: 'SnapshotParser', cache: Dict[str, str],
                                snapshot_text: str = "") -> Dict[str, str]:
        """执行前思考：分析步骤并生成决策思路"""
        if not self.enabled or not self.client:
            return {"thinking": "", "confidence": 0.0, "suggestions": []}

        try:
            snapshot_summary = self._summarize_snapshot(snapshot_text, parser)
            cache_info = self._format_cache(cache)
            params = self._format_params(step)

            prompt = self.PRE_THINK_TEMPLATE.format(
                step_num=step_num,
                desc=step.get("desc", ""),
                action=step.get("action", ""),
                target=step.get("target", "未指定"),
                params=params,
                snapshot_summary=snapshot_summary,
                cache_info=cache_info,
            )

            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.client.chat.completions.create(
                    model=self.config["model"],
                    messages=[
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=self.config["temperature"],
                    max_tokens=self.config["max_tokens"],
                    timeout=self.config["timeout"],
                )
            )

            thinking = response.choices[0].message.content if response.choices else ""
            
            confidence = self._extract_confidence(thinking)
            suggestions = self._extract_suggestions(thinking)

            return {
                "thinking": thinking,
                "confidence": confidence,
                "suggestions": suggestions,
            }

        except Exception as e:
            log(f"  [Think Error] Pre-execution think failed: {e}", 2)
            return {"thinking": f"[思考出错] {str(e)}", "confidence": 0.0, "suggestions": []}

    async def post_execute_reflect(self, step: Dict[str, Any], step_num: int,
                                   result: 'StepResult',
                                   pre_thinking: str = "") -> str:
        """执行后反思：分析结果并生成总结"""
        if not self.enabled or not self.client:
            return ""

        try:
            exec_result = self._format_execution_result(result)
            assertion_results = self._format_assertion_results(result.assertions)

            prompt = self.POST_THINK_TEMPLATE.format(
                step_num=step_num,
                desc=result.desc,
                action=result.action,
                status=result.status.value,
                duration_ms=result.duration_ms,
                retry_count=result.retry_count,
                pre_thinking=pre_thinking[:500] if pre_thinking else "无",
                execution_result=exec_result,
                assertion_results=assertion_results,
            )

            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.client.chat.completions.create(
                    model=self.config["model"],
                    messages=[
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=self.config["temperature"],
                    max_tokens=self.config["max_tokens"],
                    timeout=self.config["timeout"],
                )
            )

            return response.choices[0].message.content if response.choices else ""

        except Exception as e:
            log(f"  [Think Error] Post-execution reflect failed: {e}", 2)
            return f"[反思出错] {str(e)}"

    def _summarize_snapshot(self, snapshot_text: str, parser: 'SnapshotParser') -> str:
        """生成快照摘要"""
        if not snapshot_text and parser.elements:
            elements = list(parser.elements.values())[:15]
            lines = []
            for e in elements:
                line = f"- uid={e.uid} | role={e.role}"
                if e.name:
                    line += f" | name={e.name}"
                if e.text:
                    line += f" | text='{e.text[:40]}'"
                if e.value:
                    line += f" | value={e.value}"
                lines.append(line)
            return "\n".join(lines) if lines else "(无元素)"
        elif snapshot_text:
            lines = snapshot_text.split("\n")
            summary_lines = [l for l in lines[:30] if l.strip()]
            return "\n".join(summary_lines) + (f"\n... (共 {len(lines)} 行)" if len(lines) > 30 else "")
        return "(无快照)"

    def _format_cache(self, cache: Dict[str, str]) -> str:
        """格式化缓存信息"""
        if not cache:
            return "(空)"
        lines = [f"  '{k}' -> uid={v}" for k, v in list(cache.items())[:10]]
        return "\n".join(lines) + (f"\n... (共 {len(cache)} 项)" if len(cache) > 10 else "")

    def _format_params(self, step: Dict[str, Any]) -> str:
        """格式化参数"""
        params = {}
        for key in ["value", "option", "url", "text", "key"]:
            val = step.get(key)
            if val is not None:
                params[key] = resolve_env_vars(str(val)) if isinstance(val, str) else str(val)
        
        if not params:
            return "(无特殊参数)"
        return json.dumps(params, ensure_ascii=False, indent=2)

    def _format_execution_result(self, result: 'StepResult') -> str:
        """格式化执行结果"""
        parts = [
            f"- MCP 工具: {result.mcp_tool}",
            f"- 参数: {_safe_json_dumps(result.mcp_args, ensure_ascii=False)[:200]}",
        ]
        if result.output:
            output_preview = result.output[:300] + "..." if len(result.output) > 300 else result.output
            parts.append(f"- 返回值: {output_preview}")
        if result.error:
            parts.append(f"- 错误: {result.error}")
        return "\n".join(parts)

    def _format_assertion_results(self, assertions: List[Dict]) -> str:
        """格式化断言结果"""
        if not assertions:
            return "(无断言)"
        lines = []
        for a in assertions:
            icon = "✅" if a.get("passed") else "❌"
            lines.append(f"{icon} [{a.get('type', '?')}] {a.get('expected', '')}: {a.get('detail', '')}")
        return "\n".join(lines)

    @staticmethod
    def _extract_confidence(thinking: str) -> float:
        """从思考文本提取置信度"""
        high_keywords = ["高置信度", "很有把握", "确定", "非常可能", "high confidence"]
        low_keywords = ["低置信度", "不确定", "可能不", "不太确定", "low confidence"]
        
        thinking_lower = thinking.lower()
        if any(k in thinking_lower for k in high_keywords):
            return 0.9
        elif any(k in thinking_lower for k in low_keywords):
            return 0.3
        elif "中等" in thinking or "medium" in thinking_lower:
            return 0.6
        return 0.7

    @staticmethod
    def _extract_suggestions(thinking: str) -> List[str]:
        """从思考文本提取建议"""
        suggestions = []
        patterns = [
            r'建议[：:]\s*(.+)',
            r'提示[：:]\s*(.+)',
            r'注意[：:]\s*(.+)',
            r'Suggestion[：:]\s*(.+)',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, thinking, re.IGNORECASE)
            suggestions.extend(matches)
        return suggestions[:5]

    def format_thinking_output(self, result: 'StepResult') -> str:
        """格式化思考内容用于输出"""
        if not result.thinking_pre and not result.thinking_post:
            return ""
        
        output_parts = []
        output_parts.append("\n" + "─" * 50)
        output_parts.append(f"  🧠 LLM 思维链 | 置信度: {result.llm_confidence:.0%}")
        output_parts.append("─" * 50)
        
        if result.thinking_pre:
            output_parts.append("\n  【执行前思考】")
            for line in result.thinking_pre.split("\n"):
                if line.strip():
                    output_parts.append(f"    {line}")
        
        if result.thinking_post:
            output_parts.append("\n  【执行后反思】")
            for line in result.thinking_post.split("\n"):
                if line.strip():
                    output_parts.append(f"    {line}")
        
        if result.llm_suggestions:
            output_parts.append("\n  【AI 建议】")
            for i, s in enumerate(result.llm_suggestions, 1):
                output_parts.append(f"    {i}. {s}")
        
        output_parts.append("─" * 50)
        return "\n".join(output_parts)


# ============================================================
# 插件系统 - Action 注册表
# ============================================================

class ActionRegistry:
    """Action 类型注册表，支持动态注册和扩展"""

    _actions: Dict[str, Tuple[str, Callable]] = {}
    _needs_uid: set = set()
    _pre_hooks: Dict[str, List[Callable]] = {}
    _post_hooks: Dict[str, List[Callable]] = {}

    @classmethod
    def register(cls, action_name: str, mcp_tool: str, arg_builder: Callable,
                 needs_uid: bool = False):
        """注册新的 action 类型"""
        cls._actions[action_name.lower()] = (mcp_tool, arg_builder)
        if needs_uid:
            cls._needs_uid.add(action_name.lower())

    @classmethod
    def add_pre_hook(cls, action_name: str, hook: Callable):
        """添加前置钩子"""
        if action_name not in cls._pre_hooks:
            cls._pre_hooks[action_name] = []
        cls._pre_hooks[action_name].append(hook)

    @classmethod
    def add_post_hook(cls, action_name: str, hook: Callable):
        """添加后置钩子"""
        if action_name not in cls._post_hooks:
            cls._post_hooks[action_name] = []
        cls._post_hooks[action_name].append(hook)

    @classmethod
    def get(cls, action_name: str) -> Optional[Tuple[str, Callable]]:
        """获取 action 映射"""
        return cls._actions.get(action_name.lower())

    @classmethod
    def needs_uid(cls, action_name: str) -> bool:
        """判断 action 是否需要 UID"""
        return action_name.lower() in cls._needs_uid

    @classmethod
    def list_actions(cls) -> List[str]:
        """列出所有已注册的 action"""
        return list(cls._actions.keys())

    @classmethod
    def run_pre_hooks(cls, action_name: str, context: Dict):
        """运行前置钩子"""
        hooks = cls._pre_hooks.get(action_name, [])
        for hook in hooks:
            try:
                hook(context)
            except Exception as e:
                log(f"[Hook Error] Pre-hook for {action_name}: {e}", 2)

    @classmethod
    def run_post_hooks(cls, action_name: str, context: Dict, result: StepResult):
        """运行后置钩子"""
        hooks = cls._post_hooks.get(action_name, [])
        for hook in hooks:
            try:
                hook(context, result)
            except Exception as e:
                log(f"[Hook Error] Post-hook for {action_name}: {e}", 2)


# ============================================================
# 插件系统 - Assertion 注册表
# ============================================================

class AssertionRegistry:
    """Assertion 类型注册表"""

    _assertions: Dict[str, Callable] = {}

    @classmethod
    def register(cls, assertion_type: str, validator: Callable):
        """注册断言验证器"""
        cls._assertions[assertion_type.lower()] = validator

    @classmethod
    def get(cls, assertion_type: str) -> Optional[Callable]:
        """获取断言验证器"""
        return cls._assertions.get(assertion_type.lower())

    @classmethod
    def list_assertions(cls) -> List[str]:
        """列出所有已注册的断言类型"""
        return list(cls._assertions.keys())


# ============================================================
# Snapshot 解析器 v2.0 — 增强版
# ============================================================

class SnapshotParser:
    """
    解析 Chrome DevTools MCP take_snapshot 输出
    
    v2.0 增强:
      - 多格式兼容（带/不带 uid= 前缀、引号/无引号）
      - 属性提取（name=, url=, value=, checked= 等）
      - 层级结构保留（indent_level）
      - 位置信息记录
      - 高级匹配算法
    """

    KNOWN_ROLES = {
        "rootwebarea", "textbox", "button", "link", "menu", "menuitem",
        "combobox", "listbox", "option", "checkbox", "radio", "slider",
        "switch", "tab", "tabpanel", "dialog", "alert", "statictext",
        "inlinetextbox", "generic", "image", "heading", "grid", "gridcell",
        "row", "columnheader", "table", "list", "listitem", "group",
        "form", "input", "textarea", "select", "navigation", "banner",
        "main", "complementary", "contentinfo", "search", "searchbox", "ignored",
        "document", "application", "iframe", "section", "sectionheader",
        "separator", "progressbar", "meter", "tooltip", "status",
        "timer", "log", "marquee", "spinbutton", "tree", "treeitem",
        "toolbar", "menubar", "figure", "caption", "term", "definition",
        "math", "note", "code", "strong", "emphasis", "delete", "insert",
        "subscript", "superscript", "article", "aside", "footer", "header",
        "nav", "figure", "figcaption", "details", "summary", "mark",
        "time", "address", "blockquote", "q", "cite", "abbr", "bdi", "bdo",
        "data", "dfn", "kbd", "samp", "var", "wbr", "ruby", "rt", "rp",
    }

    # 结构性 / 容器角色：永远不是「可操作目标」，必须从**所有**候选路径排除
    # （精确匹配 + 模糊评分都要排）。
    #
    # 不排会出真事故：RootWebArea 的 text 是**页面标题**，而 _score_for_button
    # 只要 text 里含按钮关键词就 +10 —— 页面标题叫「登录」「系统管理」「查询」
    # 时都会命中。于是当目标在当前页面根本不存在时，那个 +10 会让整页根节点
    # 成为最高分候选并被当作点击目标：
    #   click '提交巡检' -> uid=2_0 (role=rootwebarea, text='登录')
    #   → MCP: "Failed to interact with the element with uid 2_0.
    #           The element did not become interactive within the timeout."
    # 而且它还会被写进 uid 缓存，重试 3 次全部命中同一个垃圾节点（实测白跑 28s）。
    #
    # 注：旧代码这里本有一组降权分支，但写的是 CamelCase
    # （"RootWebArea" / "StaticText" / "InlineTextBox"），
    # 而 _parse_tokens 解析出的 role 一律是小写 —— 那三段降权**从未生效**，
    # 这正是上面这个 bug 能长期存在的原因。
    NON_TARGET_ROLES = frozenset({
        "rootwebarea", "ignored", "document", "application", "iframe",
    })

    INPUT_ROLES = INPUT_ROLES


    def __init__(self):
        self.elements: Dict[str, SnapshotElement] = {}
        self.raw_text: str = ""
        self.element_order: List[str] = []
        # 按行顺序保存的元素实例。MCP 快照里同一个 uid 会被多个不同节点复用
        # （实测见过 uid=2_1 对应 14 个节点，文本从「登录」到「《隐私协议》」），
        # 于是 elements[uid] 会被后写的那行覆盖，element_order 与 elements 的
        # 对应关系随之失真。凡是要看「相邻元素」的场合都必须走这个列表，
        # 用对象身份而不是 uid 去定位。
        self.element_lines: List[SnapshotElement] = []

    def parse(self, snapshot_text: str) -> Dict[str, SnapshotElement]:
        """解析快照文本为结构化元素字典"""
        self.raw_text = snapshot_text
        self.elements = {}
        self.element_order = []
        self.element_lines = []

        for line in snapshot_text.split("\n"):
            line = line.rstrip()
            if not line or line.startswith("#") or line.startswith("##"):
                continue

            element = self._parse_line(line)
            if element and element.uid:
                self.elements[element.uid] = element
                self.element_order.append(element.uid)
                self.element_lines.append(element)

        self._mark_modal_elements()
        self._mark_reused_uids()
        return self.elements

    def _mark_reused_uids(self) -> None:
        """标出「uid 在本次快照里被多个节点复用」的元素。

        Chrome DevTools 的 a11y 快照里 uid 会被复用：实测 h5 巡检执行页有 **30 处**
        `uid=22_155 InlineTextBox "<各种不同文本>"`，而真正唯一的可点节点是
        `uid=38_32 StaticText "提交巡检"`。

        按复用 uid 去 click（MCP 用 uid 定位）会报
        `Element with uid 22_155 no longer exists on the page` ——
        实测 h5-001 步骤 13「提交巡检」把 4 次尝试（共 13.6s）全打在这个死 uid 上，
        请求永远发不出去，后续「提交成功」断言必然 FAIL。

        只用于**打破原本完全打平的排序**（排序键最后一位），不改变任何既有优先级，
        因此不会影响此前已判定的结果。
        """
        counts: Dict[str, int] = {}
        for el in self.element_lines:
            counts[el.uid] = counts.get(el.uid, 0) + 1
        for el in self.element_lines:
            if counts.get(el.uid, 0) > 1:
                el.uid_reused = True

    def _mark_modal_elements(self) -> None:
        """标出「位于模态对话框内部」的元素。

        快照是**按缩进嵌套**的扁平行序列：dialog 的所有后代缩进都更深，
        因此从 dialog 那一行往下走到第一个缩进不更深的行，就是它的子树范围。

        为什么需要：弹窗打开时页面背后常有同名控件（列表页的搜索框 vs 弹窗里的
        必填项），文本/角色完全一致，靠遍历顺序决定胜负 —— 实测 5 个必填项里
        有 3 个被写进了背后的搜索框，提交时被必填校验全部拦下，数据一条没造出来。
        """
        lines = self.element_lines
        for i, el in enumerate(lines):
            if el.role not in ("dialog", "alertdialog"):
                continue
            base = el.indent_level
            j = i + 1
            while j < len(lines) and lines[j].indent_level > base:
                lines[j].in_modal = True
                j += 1

    def _parse_line(self, line: str) -> Optional[SnapshotElement]:
        """解析单行快照"""
        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        uid_match = re.match(r'^(uid=)?(\S+)\s+(.*)', stripped)
        if not uid_match:
            return None

        raw_uid = uid_match.group(2)
        uid = raw_uid[4:] if raw_uid.startswith("uid=") else raw_uid
        rest = uid_match.group(3).strip()

        if not rest or uid.startswith("#"):
            return None

        role, name, text, value, attrs = self._parse_tokens(rest)

        return SnapshotElement(
            uid=uid,
            role=role,
            name=name,
            text=text,
            value=value,
            attributes=attrs,
            raw_line=line,
            indent_level=indent // 2,
        )

    def _parse_tokens(self, rest: str) -> Tuple[str, str, str, str, Dict[str, str]]:
        """解析角色、名称、文本和属性"""
        tokens = re.findall(r'("[^"]*"|\S+)', rest)
        i = 0
        role = ""
        name = ""
        text = ""
        value = ""
        attrs = {}

        while i < len(tokens):
            token = tokens[i]

            if token.startswith('"') and token.endswith('"'):
                content = token[1:-1]

                if not role:
                    possible_role = content.lower()
                    if possible_role in self.KNOWN_ROLES:
                        role = possible_role
                    elif not text:
                        text = content
                    else:
                        if not name:
                            name = content
                        else:
                            text = content if not text else text + " " + content
                elif not name and role in self.INPUT_ROLES:
                    name = content
                else:
                    if not text:
                        text = content
                    elif not name:
                        name = content
                    else:
                        text = text + " " + content
            else:
                lower_token = token.lower()

                if lower_token in self.KNOWN_ROLES and not role:
                    role = lower_token
                elif lower_token.startswith('url='):
                    attrs['url'] = token[4:].strip('"')
                elif lower_token.startswith('name='):
                    name = token[5:].strip('"')
                elif lower_token.startswith('value='):
                    value = token[6:].strip('"')
                elif lower_token.startswith('checked='):
                    attrs['checked'] = token[8:]
                elif lower_token.startswith('selected='):
                    attrs['selected'] = token[9:]
                elif lower_token.startswith('expanded='):
                    attrs['expanded'] = token[9:]
                elif lower_token.startswith('level='):
                    attrs['level'] = token[6:]
                elif lower_token.startswith('orientation='):
                    attrs['orientation'] = token[12:]
                elif lower_token.startswith('for='):
                    attrs['for'] = token[4:]
                elif lower_token.startswith('href='):
                    attrs['href'] = token[5:]
                elif lower_token == 'ignored' and not role:
                    role = "ignored"

            i += 1

        return role, name, text, value, attrs

    def find_uid(self, target_description: str, cache: Dict[str, str],
                 prefer_role: Optional[str] = None,
                 exclude_roles: Optional[set] = None,
                 require_interactive: bool = False,
                 exact_only: bool = False,
                 prefer_empty: bool = False) -> Optional[str]:
        """
        三层匹配策略（v3.0）:
          Layer 1: 精确匹配 - target文本与元素text/name/value完全一致或包含
          Layer 2: 模糊评分 - 关键词打分排序（兜底，会打WARN）
         缓存层贯穿始终

        exact_only=True 时只做 Layer 1：不行就返回 None，绝不退化成
        「随便挑一个分最高的」。多个字段的 target 都写占位符（"请输入XX"）时，
        模糊层会给**每个**输入框同等分数，于是所有字段都落进同一个框。

        prefer_empty=True（填表类动作）：精确匹配出现多个**完全打平**的控件时优先选空值那个。
        注意此时**不能用 uid 缓存短路**：缓存是按 target 文本存的，第 1 行填完后
        target 仍映射到第 1 行的 uid，第 2 行会被永久跳过。
        """
        target_description = target_description or ""
        target_raw = target_description.strip()

        # v3.1: target@N 语法 —— 同文控件歧义消解。
        # 场景：巡检执行页每个巡检项都有同名「正常/异常/不适用」按钮，旧逻辑
        # 永远命中第 1 个（快照 DOM 序），第 2 项永远选不上，提交被后端以
        # 「第 2 项「XX」未选择判定结果」拒绝（实测 h5-001 步骤 10/11）。
        # 写法：target: "正常@2" = 点第 2 个「正常」（按快照遍历序 = DOM 序）。
        # @N 目标禁用 uid 缓存：同名控件在不同快照里 uid 会漂移，且同名多击
        # 必须每次重新解析（prefer_empty 的缓存旁路同理）。
        nth: Optional[int] = None
        m_nth = re.search(r"@(\d+)$", target_raw)
        if m_nth:
            parsed = int(m_nth.group(1))
            if parsed >= 1:
                nth = parsed
                target_raw = target_raw[: m_nth.start()].strip()
        target_lower = self._cmp_norm(target_raw)

        cached = cache.get(target_lower)
        if cached and cached in self.elements and not prefer_empty and nth is None:
            log(f"[Cache Hit] '{target_description}' -> {cached}", 3)
            return cached

        if not self.elements:
            return None

        exact_uid = self._exact_match_uid(target_raw, target_lower, prefer_role, exclude_roles,
                                          require_interactive, prefer_empty, nth=nth)
        if exact_uid:
            if nth is None:
                cache[target_lower] = exact_uid
            elem = self.elements[exact_uid]
            log(f"[Exact] '{target_description}' -> {exact_uid} "
                f"(role={elem.role}, text='{elem.text[:30]}')", 3)
            return exact_uid

        if exact_only:
            return None

        candidates = self._score_candidates(target_lower, prefer_role, exclude_roles, require_interactive)

        if not candidates:
            log(f"[Miss] '{target_description}' - 无候选元素", 3)
            self._log_debug_info(target_lower)
            return None

        best_uid, best_score = candidates[0]

        # @N 落到模糊层：只认最高分并列组里的第 N 个，组不够大就明确失败，
        # 绝不静默降级到别的元素（宁缺勿错）。
        if nth is not None:
            top_group = [u for u, s in candidates if s == best_score]
            if len(top_group) >= nth:
                chosen = top_group[nth - 1]
                log(f"[Fuzzy-Nth] '{target_description}' -> {chosen} "
                    f"(并列{len(top_group)}个中第{nth}个, score={best_score})", 2)
                return chosen
            log(f"[Nth-Miss] '{target_description}' 最高分并列组仅{len(top_group)}个(<{nth})", 2)
            return None

        log(f"[Fuzzy-WARN] '{target_description}' -> {best_uid} (score={best_score}, "
            f"建议YAML使用精确文本匹配以提升可靠性)", 2)

        if best_score > 0:
            cache[target_lower] = best_uid
            elem = self.elements[best_uid]
            log(f"[Match] '{target_description}' -> {best_uid} "
                f"(score={best_score}, role={elem.role}, text='{elem.text[:30]}')", 3)
        else:
            log(f"[Low Score] '{target_description}' -> {best_uid} (score={best_score})", 3)

        return best_uid

    @staticmethod
    def _cmp_norm(s: str) -> str:
        """比较用的归一化：去掉所有空白 + 转小写。

        必要性：Element Plus / uni-app 的按钮文案常写成「登 录」「提 交」（中间
        插空格做字距），而 YAML 里写的是「登录」「提交」。不做空白归一化，
        `'登录' in '登 录'` 恒为 False —— PC 端的登录按钮永远匹配不到。
        """
        return "".join((s or "").split()).lower()

    def _exact_match_uid(self, target_raw: str, target_lower: str,
                          prefer_role: Optional[str], exclude_roles: Optional[set],
                          require_interactive: bool,
                          prefer_empty: bool = False,
                          nth: Optional[int] = None) -> Optional[str]:
        """Layer 1: 精确文本匹配

        排序键是 **(匹配长度, 是否完全相等, 是否交互元素)**，三元组从高到低取优。

        为什么加第 2 项「是否完全相等」：光比长度会让**长句子里偶然包含目标词**的
        文本节点跟真控件打平，谁先遍历到谁赢。实测 PC 登录页有一句说明文案
        「使用当前账号体系登录到业务工作台。」，target 写「登录」时它和真正的
        「登 录」按钮都是 match_len=2；按钮排在后面时就会被判为「不更新」，
        于是点到了那句说明文字上 —— 登录静默失败，后续 PC 用例全部连锁失败
        （且 url_contains '/index' 还会因为跳转到 /login?redirect=/index 而误判 PASS）。
        加上「完全相等」这一维后，按钮（归一化后 '登录' == 目标）必胜说明句（仅包含）。

        prefer_empty=True（填表类动作用）：当多个控件**完全打平**时优先选当前值为空的那个，
        解决主子表「每行同名输入框」的重复填充问题（见下方注释）。
        """
        best_uid = None
        best_key = None
        best_group: List[str] = []      # 与 best_key 打平的候选（按遍历顺序）
        target_cmp = self._cmp_norm(target_raw)

        for uid, elem in self.elements.items():
            if exclude_roles and elem.role in exclude_roles:
                continue
            # 结构性节点直接出局，否则页面标题能"精确命中"整个动作（见 NON_TARGET_ROLES）
            if elem.role in self.NON_TARGET_ROLES:
                continue
            if require_interactive and not elem.is_interactive:
                continue
            if prefer_role and elem.role != prefer_role:
                continue

            match_len = 0
            match_len = 0
            exact_level = 0   # 2=原文完全相等  1=去空白后才相等  0=仅包含

            def consider(field: str, half: bool = False) -> None:
                """field 命中目标时更新 match_len / exact_level（闭包写外层局部变量）"""
                nonlocal match_len, exact_level
                if not field:
                    return
                field_cmp = self._cmp_norm(field)
                if not field_cmp:
                    return
                damp = 2 if half else 1
                # 原文完全相等 > 去空白后才相等 > 仅包含。
                # 必须区分前两者：uni-app 登录页的**页面标题**就是「登录」，
                # 而真正的按钮文案是「登 录」。只比「归一化后相等」会让两者打平，
                # 标题靠遍历顺序先到就赢（这就是加 exact_level 之前 ①② 回归的原因）。
                if target_raw and field == target_raw:
                    exact_level = max(exact_level, 2)
                    match_len = max(match_len, max(1, len(target_raw) // damp))
                elif target_cmp and field_cmp == target_cmp:
                    exact_level = max(exact_level, 1)
                    match_len = max(match_len, max(1, len(target_raw) // damp))
                elif target_raw and target_raw in field:
                    match_len = max(match_len, max(1, len(target_raw) // damp))
                elif target_cmp and target_cmp in field_cmp:
                    # 仅去空白后才包含（例如 target「登录」命中「登 录」按钮的兄弟文本）
                    match_len = max(match_len, max(1, len(target_cmp) // damp))

            consider(elem.text)
            consider(elem.name, half=True)
            consider(elem.value, half=True)

            # target 比元素文本更长（desc 兜底时常见）：用元素自身文本长度做弱匹配
            if elem.text and elem.text not in target_raw and elem.text in target_raw:
                match_len = max(match_len, len(elem.text))

            if match_len <= 0:
                continue

            # 排序键：匹配长度 → 是否在弹窗内 → 匹配严格度 → 是否交互元素 → uid 是否唯一
            # 「弹窗内」优先：弹窗打开时它才是当前操作面，页面背后同名控件应让位。
            # 「uid 唯一」放最后：只在前面全部打平时才起作用，把「被 30 个节点复用的
            # 文本叶子 uid」让位给唯一的 StaticText（否则 MCP 按 uid 点不到，见
            # _mark_reused_uids 的实测）。
            key = (match_len, 1 if elem.in_modal else 0, exact_level,
                   1 if elem.is_interactive else 0,
                   0 if getattr(elem, "uid_reused", False) else 1)
            if best_key is None or key > best_key:
                best_key = key
                best_uid = uid
                best_group = [uid]
            elif key == best_key:
                best_group.append(uid)

        # 「主子表重复行」歧义：同一 target 命中多个**完全打平**的控件时（典型场景是
        # 明细表每一行都有同名的「请输入XX」输入框），旧实现按遍历顺序取第一个，
        # 于是第二次 fill 又写回第一行 —— 实测 pc-004 步骤 10 把「指示灯状态」覆盖到
        # 第 1 行，第 2 行仍为空，后端以「第 2 行模板明细的「巡检项名称」不能为空」
        # 直接拒绝提交，模板一条也建不出来（下游 pc-005/h5 全断）。
        # 此时优先取**当前还是空**的那个（= 还没填过的那一行）；一个空的都没有就退回首选。
        # 「主子表重复行」歧义：同一 target 命中多个**完全打平**的控件时（典型场景是
        # 明细表每一行都有同名的「请输入XX」输入框），旧实现按遍历顺序取第一个，
        # 于是第二次 fill 又写回第一行 —— 实测 pc-004 步骤 10 把「指示灯状态」覆盖到
        # 第 1 行，第 2 行仍为空，后端以「第 2 行模板明细的「巡检项名称」不能为空」
        # 直接拒绝提交，模板一条也建不出来（下游 pc-005/h5 全断）。
        # 此时优先取**当前还是空**的那个（= 还没填过的那一行）；一个空的都没有就退回首选。
        if prefer_empty and best_uid is not None and len(best_group) > 1:
            best_elem = self.elements.get(best_uid)
            if best_elem is not None and (best_elem.value or "").strip():
                for cand in best_group:
                    ce = self.elements.get(cand)
                    if ce is not None and not (ce.value or "").strip():
                        log(f"[Empty-First] '{target_raw}' 命中 {len(best_group)} 个打平控件，"
                            f"改选空值控件 {cand}（原首选 {best_uid} 已有值 "
                            f"'{best_elem.value[:20]}'）", 2)
                        return cand

        # @N（第 N 个同文控件）：打平组按快照遍历序（= DOM 序）排列，
        # 直接取第 N 个；组不够大时明确返回 None（上层会打 Nth-Miss 日志），
        # 绝不静默回退到首选——那等于没选第 N 个，正是本语法要消灭的假阳性。
        if nth is not None and best_group:
            if len(best_group) >= nth:
                chosen = best_group[nth - 1]
                ce = self.elements.get(chosen)
                log(f"[Nth] '{target_raw}' 第{nth}个同文匹配 -> {chosen} "
                    f"(组大小={len(best_group)}, role={getattr(ce, 'role', '?')})", 2)
                return chosen
            log(f"[Nth-Miss] '{target_raw}' 打平组仅{len(best_group)}个(<{nth})", 2)
            return None

        return best_uid

    def _score_candidates(self, target: str, prefer_role: Optional[str],
                          exclude_roles: Optional[set], require_interactive: bool) -> List[Tuple[str, int]]:
        """对所有候选元素评分并排序"""
        scored = []
        keywords = self._build_keywords(target)

        target_intent = self._detect_intent(target)

        for uid, elem in self.elements.items():
            score = self._score_element(elem, keywords, target_intent, prefer_role, exclude_roles, require_interactive)
            if score > 0:
                scored.append((uid, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:10]

    def _score_element(self, elem: SnapshotElement, keywords: List[str],
                       intent: Dict[str, bool], prefer_role: Optional[str],
                       exclude_roles: Optional[set], require_interactive: bool) -> int:
        """对单个元素评分"""
        score = 0
        combined = elem.combined_text

        if exclude_roles and elem.role in exclude_roles:
            return 0

        if require_interactive and not elem.is_interactive:
            return 0

        # 空文本元素不参与模糊兜底（仅 click 类动作，require_interactive=False 时）。
        # 实测 pc-002 步骤15：「确 定」精确层 Miss（编辑弹窗没开），desc 兜底
        # 「点击「确 定」保存修改」的关键词给一个**空文本下拉触发器**（uid 5_224）
        # 打了 20 分并点击 —— 表单没提交、无 toast、无报错的静默假阳性。
        # 连 text/name/value 都没有的控件跟文本目标毫无语义关联，直接出局。
        # 填表动作（require_interactive=True）不走这条：输入框自身无文本、
        # 靠邻近标签匹配（下方 require_interactive 分支）是**有意设计**。
        if not require_interactive and not (elem.text or elem.name or elem.value):
            return 0

        for kw in keywords:
            kw_l = kw.lower()

            if elem.role and kw_l in elem.role:
                score += 15
            if elem.name and kw_l in elem.name.lower():
                score += 12
            if elem.text and kw_l in elem.text.lower():
                score += 8
            if elem.value and kw_l in elem.value.lower():
                score += 10
            if kw_l in combined:
                score += 5

        if intent["button"]:
            score += self._score_for_button(elem, intent["target_words"])
        if intent["input"]:
            score += self._score_for_input(elem, intent["target_words"])
        if intent["menu"]:
            score += self._score_for_menu(elem, intent["target_words"])
        if intent["link"]:
            score += self._score_for_link(elem, intent["target_words"])
        if intent["select"]:
            score += self._score_for_select(elem, intent["target_words"])

        # 表单控件自身常常没有任何文本（uni-app / uView 的 H5 产物把 placeholder
        # 渲染成独立的文本节点）。此时仅凭角色无法区分同页的多个控件——账号框和
        # 密码框会拿到相同的角色基础分，排序后永远取第一个，表现为「账号和密码
        # 都填进了账号框」。用邻近文本作为该控件的标签来判定命中。
        #
        # 两道门控缺一不可：
        #   ① require_interactive：等同于「这是填表动作」。不能用 intent["input"]
        #      代替 —— 像「例如 RM-A-001」这种纯 placeholder 文案，关键词表猜不出
        #      输入意图，加分会被整体跳过；而 click 动作（require_interactive=False）
        #      又必须关掉它，否则输入框会因「旁边恰好有某段文字」抢走按钮的 target。
        #   ② not (elem.text or elem.name)：控件自身有文本时（PC 端 Element Plus
        #      把 placeholder 挂在 input 上）说明原生匹配已足够，保持原有行为不变。
        if require_interactive and elem.role in INPUT_ROLES and not (elem.text or elem.name):
            label = self._nearby_text(elem)
            if label:
                label_l = label.lower()
                if any(kw.lower() in label_l for kw in keywords if len(kw) >= 2):
                    score += 30

        if prefer_role and elem.role == prefer_role:
            score += 25

        # 结构性节点直接出局（必须放在所有加分之后、max() 之前，
        # 否则 _score_for_button 靠页面标题拿到的 +10 会把它抬成最高分）
        if elem.role in self.NON_TARGET_ROLES:
            return 0

        # 旧代码此处有三段降权，但 role 比较写成了 CamelCase
        # （"RootWebArea" / "StaticText" / "InlineTextBox"），
        # 而解析出的 role 一律小写 → 从未生效。rootwebarea / ignored 已由上方的
        # NON_TARGET_ROLES 直接排除；StaticText / InlineTextBox **故意不再降权**：
        # uni-app 的 <button> 在快照里就是 statictext，降权会把登录/查询这类
        # 真按钮压到普通文本节点之下（这正是之前「登录按钮点了没反应」的成因）。
        if elem.uid.startswith("1_") and len(elem.uid) <= 3:
            score -= 10

        return max(0, score)

    def _nearby_text(self, elem: SnapshotElement, radius: int = 3) -> str:
        """取归属于该控件的紧邻纯文本，用作它的「标签 / 占位符」。

        uni-app / uView 的 H5 产物把 placeholder 渲染成独立的纯文本节点，真正的
        输入框自身不带任何文本；PC 端的 Element Plus 则把 placeholder 直接挂在
        input 上。前者只能靠邻近文本判断「这个框是干什么的」。

        三条规则，每一条都是踩过坑才加上的：
          · 位置在 element_lines 上按**对象身份**取，不能走 elements[uid] —— MCP
            快照里同一 uid 会被多个节点复用，字典里只剩最后写入的那一份，曾因此
            把「《隐私协议》」当成账号框的标签。
          · 半径放宽到 3：placeholder 与输入框之间可能夹着 form / generic 这类
            结构节点（扫码页就是 StaticText → form → searchbox）。
          · 但放宽后必须做「就近归属」：一段文本只算离它最近的控件的标签。否则
            半径一大，账号框就会把密码框的占位符也算进来，两个框重新无法区分。
        """
        lines = getattr(self, "element_lines", None) or []
        my_idx = next((i for i, candidate in enumerate(lines) if candidate is elem), None)
        if my_idx is None:
            return ""
        control_idx = [i for i, c in enumerate(lines)
                       if c is not None and c.role in INPUT_ROLES]
        parts: List[str] = []
        for offset in range(-radius, radius + 1):
            if offset == 0:
                continue
            pos = my_idx + offset
            if not (0 <= pos < len(lines)):
                continue
            neighbor = lines[pos]
            if neighbor is None or not neighbor.text:
                continue
            if neighbor.role.lower() not in ("statictext", "inlinetextbox",
                                             "label", "paragraph", "generic"):
                continue
            if not self._belongs_to(lines, control_idx, pos, my_idx):
                continue
            parts.append(neighbor.text)
        return " ".join(parts)

    @staticmethod
    def _belongs_to(lines: List[SnapshotElement], control_idx: List[int],
                    text_pos: int, my_idx: int) -> bool:
        """判定 text_pos 处的文本是否归属于 my_idx 这个控件。

        比较各控件到该文本的距离；距离相同时，位于文本**后方**的控件优先
        （placeholder 通常写在输入框前面，所以「夹在两框之间」的文本属于后者）。
        """
        def rank(control_pos: int) -> tuple:
            return (abs(text_pos - control_pos), 0 if control_pos > text_pos else 1)

        my_rank = rank(my_idx)
        return all(rank(other) >= my_rank for other in control_idx if other != my_idx)

    def _detect_intent(self, target: str) -> Dict[str, bool]:
        """检测用户意图"""
        words = target.lower().split()
        return {
            "button": any(w in target for w in [
                "按钮", "button", "click", "提交", "submit", "登录", "login",
                "新增", "add", "保存", "save", "删除", "delete", "确认", "confirm",
                "取消", "cancel", "搜索", "search", "查询", "query",
            ]),
            "input": any(w in target for w in [
                "输入框", "input", "字段", "field", "用户名", "密码", "password",
                "名称", "name", "金额", "amount", "项目", "project", "搜索框",
                "填写", "fill", "输入", "type",
            ]),
            "menu": any(w in target for w in [
                "菜单", "menu", "导航", "nav", "侧栏", "sidebar", "展开",
                "expand", "collapse",
            ]),
            "link": any(w in target for w in [
                "入口", "entry", "链接", "link", "系统", "system", "跳转",
            ]),
            "select": any(w in target for w in [
                "下拉", "select", "选择", "option", "类型", "type", "combo",
                "评估类型", "状态",
            ]),
            "need_interactive": True,
            "target_words": words,
        }

    def _score_for_button(self, elem: SnapshotElement, words: List[str]) -> int:
        """按钮类元素加分

        注意最后的按钮关键词加分**必须与目标相关**：原先的写法是
        `if any(kw in elem.text for kw in button_keywords)`，完全无视要查找的目标
        （参数 words 从未被使用），于是**任何**含「登录/提交/搜索/确认」字样的文本
        都会白拿 +10。典型受害者是页面标题 —— 登录页那行
        `uid=2_2 StaticText "登录"` 会因此拿到 10 分，在目标当前页面不存在时
        成为最高分候选被点掉（现象：点『提交巡检』实际点到页面标题上，
        随后 MCP 报 "did not become interactive"，再重试 3 次白跑 28 秒）。

        收紧后：只有当「该按钮词也出现在目标文案里」才给这 10 分，
        候选集严格变小 —— 找不到目标时会诚实报「未定位到目标元素」，
        而不是随便点一个元素。
        """
        score = 0
        if elem.role == "button":
            score += 20
        elif elem.role == "link":
            score += 12
        elif elem.role == "generic" and elem.text and len(elem.text) < 20:
            score += 5

        button_keywords = ["提交", "保存", "新增", "删除", "确认", "搜索", "登录",
                          "login", "submit", "add", "save", "delete", "confirm"]
        # 去掉空格再比：uni-app 的按钮文案常写成「登 录」「提 交」，
        # 而词表里是「登录」「提交」，不做空格归一化会永远匹配不上。
        target_text = " ".join(words).replace(" ", "").lower()
        elem_text = (elem.text or "").lower()
        if target_text and any(kw in elem_text and kw in target_text
                               for kw in button_keywords):
            score += 10

        return score

    def _score_for_input(self, elem: SnapshotElement, words: List[str]) -> int:
        """输入框类元素加分"""
        score = 0
        if elem.role in ("textbox", "input"):
            score += 20
        elif elem.role == "searchbox":
            score += 20
        elif elem.role == "combobox":
            score += 15
        elif elem.role == "spinbutton":
            score += 18
        elif "InlineTextBox" in elem.raw_line or "textbox" in elem.raw_line.lower():
            score += 10

        input_keywords = ["用户名", "密码", "名称", "项目", "金额", "搜索", "username",
                         "password", "name", "project", "amount",
                         "评估值", "报送", "万元", "评估方法"]
        if any(kw in elem.text for kw in input_keywords):
            score += 8
        if any(kw in elem.name for kw in input_keywords):
            score += 10

        return score

    def _score_for_menu(self, elem: SnapshotElement, words: List[str]) -> int:
        """菜单类元素加分"""
        score = 0
        if elem.role in ("menuitem", "menu"):
            score += 18
        if any(w in elem.text.lower() for w in words):
            score += 10
        return score

    def _score_for_link(self, elem: SnapshotElement, words: List[str]) -> int:
        """链接类元素加分"""
        score = 0
        if elem.role == "link":
            score += 18
        if any(w in elem.text.lower() for w in words):
            score += 10
        return score

    def _score_for_select(self, elem: SnapshotElement, words: List[str]) -> int:
        """选择框类元素加分"""
        score = 0
        if elem.role in ("combobox", "select"):
            score += 20
        elif elem.role == "option":
            score += 15
        select_keywords = ["类型", "type", "状态", "status", "选择", "select",
                          "评估类型", "eval-type"]
        if any(kw in elem.text or kw in elem.name for kw in select_keywords):
            score += 10
        return score

    @staticmethod
    def _build_keywords(target: str) -> List[str]:
        """构建搜索关键词列表"""
        keywords = [target]

        expansions = {
            "用户名输入框": ["用户名", "username", "user", "账号", "account", "loginname"],
            "密码输入框": ["密码", "password", "passwd", "pass", "pwd"],
            "登录按钮": ["登录", "login", "signin", "sign in", "submit"],
            "资产评估": ["asset", "eval", "评估", "资产"],
            "资产评估菜单": ["资产评估", "asset-eval", "eval-menu"],
            "资产评估核准": ["核准", "approval", "asset-eval-approval"],
            "核准申请": ["核准申请", "approval-apply", "apply"],
            "新增申请按钮": ["新增", "new", "add", "创建", "create", "+", "添加"],
            "项目名称输入框": ["项目名称", "project", "name", "项目"],
            "金额输入框": ["金额", "amount", "money", "price", "评估金额"],
            "报送评估值输入框": ["报送", "评估值", "评估金额", "万元", "amount", "报送评估值"],
            "评估类型下拉框": ["评估类型", "eval-type", "type", "类型", "下拉", "select"],
            "评估方法下拉框": ["评估方法", "eval-method", "method", "方法", "市场法", "收益法", "成本法", "资产基础法", "下拉", "select"],
            "提交按钮": ["提交", "submit", "save", "保存", "确认", "confirm"],
            "资产评估系统": ["资产评估", "asset-eval", "评估系统", "system"],
        }

        for key, exps in expansions.items():
            if key in target or any(e in target for e in exps):
                keywords.extend(exps)

        words = re.split(r'[\s\'\"\(\)\[\]{}、，。：:；;，,]', target)
        keywords.extend([w for w in words if len(w) >= 2])

        return list(set(keywords))

    def _log_debug_info(self, target: str):
        """输出调试信息"""
        interactive = [(u, e.role, e.text[:40]) for u, e in self.elements.items()
                      if e.is_interactive]
        buttons = [(u, e.role, e.text[:40]) for u, e in self.elements.items()
                  if e.role in ("button", "link")]
        inputs = [(u, e.role, e.text[:40]) for u, e in self.elements.items()
                 if e.role in self.INPUT_ROLES]

        if interactive:
            log(f"[Debug] Interactive elements ({len(interactive)}): {interactive[:8]}", 3)
        if buttons:
            log(f"[Debug] Buttons ({len(buttons)}): {buttons[:5]}", 3)
        if inputs:
            log(f"[Debug] Inputs ({len(inputs)}): {inputs[:5]}", 3)

    def find_all_by_role(self, role: str) -> List[SnapshotElement]:
        """查找所有指定角色的元素"""
        return [e for e in self.elements.values() if e.role == role]

    def find_by_text_contains(self, text: str) -> List[SnapshotElement]:
        """查找包含指定文本的所有元素（排除结构性节点：它们的 text 是页面标题）"""
        text_lower = text.lower()
        return [e for e in self.elements.values()
                if e.role not in self.NON_TARGET_ROLES
                and (text_lower in e.text.lower() or text_lower in e.name.lower())]

    def get_element_context(self, uid: str, radius: int = 2) -> List[SnapshotElement]:
        """获取元素的上下文（前后相邻元素）"""
        if uid not in self.element_order:
            return []

        idx = self.element_order.index(uid)
        start = max(0, idx - radius)
        end = min(len(self.element_order), idx + radius + 1)
        return [self.elements[self.element_order[i]] for i in range(start, end)]


# ============================================================
# Action 参数构建器 v3.0
# ============================================================

# 需要「把纯文本回退到相邻输入框」的动作：这些都是要往输入控件里写值的
_FILL_ACTIONS = frozenset({"fill", "type", "input", "select_option", "select", "choose"})

# 「纯文本录入」动作。范围故意比 _FILL_ACTIONS 窄：**不含 select_option/select/choose**。
# 这两种动作的危险面不同 —— 下拉/选择器的候选节点本来就常挂在弹层里、快照外层，
# 实测 pc-004 步骤 11 模糊命中弹窗外的 combobox（5_393, score=45）是**正常且通过**的；
# 若把选择类动作也纳入下面的弹窗越界防护，会把它误杀。
# 真正需要防的是「把文本静默写进错误的字段」这一种破坏性最强的失败。
_TEXT_ENTRY_ACTIONS = frozenset({"fill", "type", "input"})

# 界面上常见的占位符前缀。YAML 的 target 常直接照抄 placeholder，
# 而这些字样在无障碍树里往往根本不存在（见 _resolve_uid 的 P1b 注释）。
_PLACEHOLDER_PREFIXES = (
    "请输入", "请选择", "请填写", "请上传", "请描述", "请设置", "请搜索", "请确认",
    "输入", "选择", "填写", "例如", "如：", "如:", "示例：", "示例:",
)


def _strip_placeholder_prefix(text: str) -> str:
    """剥掉占位符前缀，返回字段核心名（"请输入机房名称" → "机房名称"）。

    反复剥离以覆盖「请输入：机房名称」这类组合写法；剥到空串则原样返回，
    避免把整段文本吃光。
    """
    core = (text or "").strip()
    changed = True
    while changed and core:
        changed = False
        for prefix in _PLACEHOLDER_PREFIXES:
            if core.startswith(prefix) and len(core) > len(prefix):
                core = core[len(prefix):].strip().lstrip("：:").strip()
                changed = True
    return core


def _sibling_input_uid(parser, elem, max_distance: int = 2) -> Optional[str]:
    """占位符文本节点 → 相邻输入框。

    部分前端框架（uni-app / uView 的 H5 产物）把 placeholder 渲染成独立的
    纯文本节点，真正的输入框自身不带任何文本，于是 `target: "请输入账号"`
    只能匹配到那个文本节点。若把它的 uid 交给 fill，动作会落到页面上第一个
    可编辑元素，表现为「账号和密码都填进了账号框」。
    这里按快照行序就近回溯，优先取后继元素（placeholder 通常排在输入框之前）。

    位置优先在 element_lines 上按对象身份取：MCP 快照里同一 uid 会被多个节点复用，
    elements[uid] 只剩最后写入的那一份，用它做邻居查找会串到完全无关的元素上。
    """
    lines = getattr(parser, "element_lines", None)
    if lines:
        idx = next((i for i, c in enumerate(lines) if c is elem), None)
        if idx is not None:
            for distance in range(1, max_distance + 1):
                for pos in (idx + distance, idx - distance):
                    if 0 <= pos < len(lines):
                        candidate = lines[pos]
                        if candidate is not None and candidate.role in INPUT_ROLES:
                            return candidate.uid
        return None

    # 兼容只有 element_order 的旧解析器
    order = getattr(parser, "element_order", None) or []
    if elem.uid not in order:
        return None
    idx = order.index(elem.uid)
    for distance in range(1, max_distance + 1):
        for pos in (idx + distance, idx - distance):
            if 0 <= pos < len(order):
                candidate = parser.elements.get(order[pos])
                if candidate is not None and candidate.role in INPUT_ROLES:
                    return candidate.uid
    return None


_MCP_WRAPPER_RE = re.compile(r'^\s*Script\s+ran\s+on\s+page\s+and\s+returned\s*:?\s*', re.I)


def _strip_mcp_wrapper(text: str) -> str:
    """去掉 Chrome DevTools MCP 对 evaluate_script 结果的外层包裹。

    MCP 把返回值包成 `Script ran on page and returned:\\n<值>`，
    直接截断 80 字会被这个前缀（31 字）吃掉大半 —— 实测 toast 断言的 detail
    被截成 `LiveToast: 'Script ran on page and returned:`，真正的 toast 文案
    （例如「点位状态不能为空」）完全看不见，排查时只能去翻后端日志。

    只影响**展示与子串判断**，不改变断言语义（包含关系不受前后缀剥离影响）。
    """
    if not text:
        return text
    t = _MCP_WRAPPER_RE.sub('', text).strip()
    # 即使 evaluate_script 返回的是普通字符串，MCP 也会套一层 ```json ... ``` 围栏，
    # 只 strip('`') 会留下 "json\n\"值\"" 这种残渣（实测 detail 显示成 LiveToast: 'json）。
    fence = re.match(r'^```[A-Za-z]*\s*\n?(.*?)\n?```$', t, re.DOTALL)
    if fence:
        t = fence.group(1).strip()
    t = t.strip('`').strip()
    if len(t) >= 2 and t[0] == '"' and t[-1] == '"':
        t = t[1:-1]
    return t.strip()


def _modal_guard(parser, uid: str, label: str) -> bool:
    """弹窗打开时，禁止「纯文本录入」落到弹窗外的控件上。

    返回 True = 放行；False = 拦下（调用方必须当作「没解析到」处理）。

    背景（实测 pc-005 步骤 6/7）：YAML 的 target 写成「全局唯一」「机柜」这类
    **界面上根本不存在**的文本时，P1a/P1b 精确层必然 Miss，落到 P1c 模糊层；
    模糊层给列表页背后那个无关的搜索框（5_267）打了 score=25 就静默返回，
    引擎照样打印 `[Match] ... ✅ 成功`。

    后果：弹窗里的「点位编码」「位置描述」两个必填项始终为空 → 后端必填校验
    拦下提交 → 点位一条也建不出来（下游 pc-005b / h5-002 / h5-003 全部连锁断供），
    而报告里这些步骤却显示**通过**。这类「数据没造出来但用例是绿的」是本项目
    反复踩的坑（引擎 P1b 注释里已记了 pc-003/pc-004 两次同类事故）。

    判定依据：若是同一 target 在弹窗内也存在候选，精确层的排序键里 in_modal 权重
    高于 exact_level，弹窗内的那个必胜（pc-005 步骤 5「点位名称」→ 7_55 即此机制）。
    所以「弹窗已打开、结果却在弹窗外」只能说明该 target 对当前操作面无意义 ——
    此时**大声失败**远好于静默写错位置。
    """
    try:
        modal_open = any(getattr(e, "in_modal", False) for e in parser.elements.values())
    except Exception:
        return True
    if not modal_open:
        return True
    elem = parser.elements.get(uid)
    if elem is None or getattr(elem, "in_modal", False):
        return True
    log(f"[Modal-Guard] '{label}' 模糊命中弹窗外控件 {uid}"
        f"（role={elem.role}, name='{(elem.name or '')[:30]}'）→ 拒绝使用，"
        f"避免把文本静默写进弹窗背后的同名控件", 1)
    return False


def _resolve_uid(step: Dict, parser, cache, prefer_role: Optional[str] = None,
                require_interactive: Optional[bool] = None) -> Optional[str]:
    """统一UID解析（优先级从高到低）:
      P0:   locator.uid        YAML强制定位，零开销
      P0.5: locator.aria_label 通过aria-label属性定位（用于暴露后的隐藏元素）
      P1a:  target严格匹配     只在真正命中文本时返回，命中不到就继续往下走
      P1b:  占位符前缀剥离     把「请输入机房名称」还原成「机房名称」再严格匹配一次
      P1c:  target模糊匹配     关键词打分兜底
      P2:   desc兜底           用步骤描述做模糊匹配
      P3:   text_contains      最宽松的文本包含搜索
    """
    locator = step.get("locator", {}) or {}

    direct_uid = locator.get("uid")
    if direct_uid:
        if direct_uid in parser.elements:
            log(f"[Direct-UID] {direct_uid} (YAML强制定位)", 2)
            return direct_uid
        else:
            log(f"[Direct-UID-FAIL] uid={direct_uid} 不在当前页面元素中，降级到target匹配", 2)

    aria_label = locator.get("aria-label") or locator.get("aria_label")
    if aria_label:
        for uid, elem in parser.elements.items():
            elem_aria = getattr(elem, 'aria_label', None) or ''
            if (elem.text and aria_label.lower() in elem.text.lower()) or \
               (elem.name and aria_label.lower() in elem.name.lower()):
                log(f"[ARIA-LABEL] '{aria_label}' -> {uid} (text='{elem.text[:30] if elem.text else ''}')", 2)
                return uid
        log(f"[ARIA-LABEL-FAIL] '{aria_label}' 未找到匹配元素", 2)

    if require_interactive is None:
        action = (step.get("action") or "").lower()
        # 注意：这里**不含** click / tap。uni-app 的 <button> 在快照里表现为
        # statictext（没有 button 角色），若强制要求交互元素，点击类动作会一个
        # 候选都找不到，随后被 desc 兜底误判到输入框上（表现为「登录按钮点了没反应」）。
        # 精确匹配内部按「交互元素优先」排序，放宽不会把按钮让给普通文本节点。
        require_interactive = action in (
            "fill", "type", "input", "select_option",
            "select", "choose", "hover", "drag_drop", "upload", "upload_file",
        )

    target = step.get("target", "")

    # 「填表」类动作的目标**永远不该**是弹层里的选项节点（option/menuitem/treeitem）：
    # 这些节点的文本会被字段名意外命中 —— 实测 pc-003 step11，target「请输入区域名称」
    # 剥前缀后是「区域名称」，而父区域下拉里恰好有个选项叫「区域名称-101」；
    # step10 刚选完父区域、下拉尚未收起，选项还在无障碍树里，于是精确匹配选中了它，
    # fill 打到一个不可交互的 option 上 → "did not become interactive within the
    # configured timeout"（重试 3 次共 27.8s 后失败，子区域建不出来）。
    # 只对填表类动作排除：click 类动作仍需要能点到 option。
    _action_now = (step.get("action") or "").lower()
    fill_exclude = ({"option", "menuitem", "treeitem"}
                    if _action_now in _FILL_ACTIONS else None)
    # 填表类动作：同名控件完全打平时优先选「当前为空」的那个。
    # 主子表里每一行都是同一个「请输入XX」占位符，不这样做第二次 fill 会写回第 1 行
    # （pc-004 步骤 10 实测：第 2 行留空 → 后端以「第 2 行…不能为空」拒绝整单提交）。
    prefer_empty = _action_now in _FILL_ACTIONS
    # 纯文本录入动作：模糊兜底若命中弹窗外控件要拦下（见 _modal_guard 的实测背景）
    _text_entry = _action_now in _TEXT_ENTRY_ACTIONS

    # ---- P1a: 严格匹配。失败就返回 None，不退化 ----
    if target:
        uid = parser.find_uid(target, cache, prefer_role=prefer_role,
                              exclude_roles=fill_exclude,
                              require_interactive=require_interactive,
                              exact_only=True,
                              prefer_empty=prefer_empty)
        if uid:
            return uid

    # ---- P1b: 剥离占位符前缀后再严格匹配一次 ----
    # 背景：YAML 通常照界面上可见的 placeholder 写 target（"请输入机房名称"），但
    #   · Element Plus 的输入框在无障碍树里挂的是**字段标签**（"* 机房名称"），
    #     placeholder 文本根本不在快照里；
    #   · uni-app 则把 placeholder 渲染成独立的静态文本节点。
    # 不剥前缀 → 精确匹配落空 → 落到模糊层。而模糊层对「自己没文本」的输入框
    # 一视同仁地加分，多个字段的 desc 又长得几乎一样（"填入「机房名称」" /
    # "填入「机房编码」"），结果**所有字段都被写进同一个输入框**，
    # 提交时被必填校验全部拦下 —— 数据一条也造不出来，但步骤却显示 ✅。
    if target:
        core = _strip_placeholder_prefix(target)
        if core and core != target:
            uid = parser.find_uid(core, cache, prefer_role=prefer_role,
                                  exclude_roles=fill_exclude,
                                  require_interactive=require_interactive,
                                  exact_only=True,
                                  prefer_empty=prefer_empty)
            if uid:
                log(f"[Placeholder-Strip] '{target}' → '{core}' → {uid}", 2)
                return uid

    # ---- P1c: 目标文本的整体匹配（含模糊打分兜底）----
    if target:
        uid = parser.find_uid(target, cache, prefer_role=prefer_role,
                              exclude_roles=fill_exclude,
                              require_interactive=require_interactive,
                              prefer_empty=prefer_empty)
        if uid and (not _text_entry or _modal_guard(parser, uid, target)):
            return uid

    desc = step.get("desc", "")
    uid = parser.find_uid(desc, cache, prefer_role=prefer_role,
                          exclude_roles=fill_exclude,
                          require_interactive=require_interactive,
                          prefer_empty=prefer_empty) if desc else None
    if uid and (not _text_entry or _modal_guard(parser, uid, desc)):
        return uid

    if target:
        results = parser.find_by_text_contains(target)
        # find_by_text_contains 不做交互性过滤，可能返回纯文本节点
        # （如 uni-app 把 placeholder 渲染成静态文本）。交互元素优先。
        for elem in results:
            if elem.is_interactive:
                return elem.uid
        # 仅「填表」类动作才回退到相邻输入框：此时文本节点只是输入框的标签。
        # click 类动作的目标本身就是那个文本节点（uni-app 的 button 在快照里
        # 常表现为 statictext），回退会点到隔壁输入框上。
        if (step.get("action") or "").lower() in _FILL_ACTIONS:
            for elem in results:
                sibling = _sibling_input_uid(parser, elem)
                if sibling:
                    log(f"[Placeholder-Sibling] '{target}' -> {sibling} "
                        f"(文本节点 {elem.uid} 不可交互，回退到相邻输入框)", 2)
                    return sibling
        if results:
            return results[0].uid

    return None


def _apply_nav_timeout(args: Dict, step: Dict) -> None:
    """把 YAML 的 `timeout`（毫秒）透传给 MCP 的导航类工具。

    为什么必须支持：chrome-devtools-mcp 的导航默认超时只有 **10s**
    （new_page / navigate_page 的 timeout 传 0 或省略即"用默认值"）。
    抖音这类重页面首屏经常 >10s，于是第一次一定报
    `Error: Navigation timeout of 10000 ms exceeded`。
    引擎会重试，但**首次那个标签页已经建出来了、不会被回收** ——
    每失败一次就漏一个孤儿标签页（实测 10 轮循环漏了 Page-3）。
    所以正确做法是在 YAML 里显式给 timeout，从源头不超时，
    而不是等超时后再去补救。
    """
    raw = step.get("timeout", step.get("nav_timeout"))
    if raw is None:
        return
    try:
        ms = int(float(resolve_env_vars(str(raw))))
    except (TypeError, ValueError):
        log(f"  ⚠️ navigate.timeout 无法解析({raw!r})，回退 MCP 默认值", 2)
        return
    if ms > 0:
        args["timeout"] = ms


def _build_navigate_args(action, step, parser, cache) -> Dict:
    args = {"url": resolve_env_vars(step.get("url", ""))}
    _apply_nav_timeout(args, step)
    return args

def _build_new_page_args(action, step, parser, cache) -> Dict:
    args = {"url": resolve_env_vars(step.get("url", ""))}
    _apply_nav_timeout(args, step)
    return args

def _build_click_args(action, step, parser, cache) -> Dict:
    args = {}
    uid = _resolve_uid(step, parser, cache)
    if uid:
        args["uid"] = uid
    return args

def _build_fill_args(action, step, parser, cache) -> Dict:
    args = {}
    value = resolve_env_vars(step.get("value", ""))
    args["value"] = value
    # 精确匹配所有元素（_exact_match_uid 内部对相同匹配长度优先选可交互元素，
    # 因此 label(StaticText) 不会赢过其对应的 textbox/spinbutton）
    # 注意：不要用 prefer_role 限定单一角色——弹窗里 textbox(标题) 与 spinbutton(金额) 并存，
    # 限定 spinbutton 会导致 textbox 目标（如商品标题）匹配失败后模糊落到任意 spinbutton（如分页"页"）
    uid = _resolve_uid(step, parser, cache)
    if not uid and step.get("value"):
        # 兜底：按可输入角色再试
        uid = _resolve_uid(step, parser, cache, prefer_role="textbox") or _resolve_uid(step, parser, cache, prefer_role="spinbutton")
    if uid:
        args["uid"] = uid
    return args

def _build_fill_form_args(action, step, parser, cache) -> Dict:
    elements = []
    fields = step.get("fields", [])
    for f in fields:
        elem = {"value": resolve_env_vars(f.get("value", ""))}
        uid = _resolve_uid(f, parser, cache)
        if uid:
            elem["uid"] = uid
        elements.append(elem)
    return {"elements": elements}

def _build_select_option_args(action, step, parser, cache) -> Dict:
    args = {}
    option = resolve_env_vars(step.get("option", ""))
    args["value"] = option

    # 修复 Bug G: 移除"找不到就取第一个控件"的危险 fallback（曾把品牌"华为"填进商品标题框）
    # 定位顺序: combobox 精确匹配 → 无角色精确匹配（依赖 find_uid 语义评分）
    uid = _resolve_uid(step, parser, cache, prefer_role="combobox")
    if not uid:
        uid = _resolve_uid(step, parser, cache)
    if uid:
        args["uid"] = uid
    # 未定位到: 不返回 uid，由 execute 的"未定位到目标元素"兜底（Bug A 修复），禁止乱填
    return args

def _build_upload_args(action, step, parser, cache) -> Dict:
    args = {"filePath": resolve_env_vars(step.get("path", ""))}
    uid = _resolve_uid(step, parser, cache)
    if uid:
        args["uid"] = uid
    return args

def _build_hover_args(action, step, parser, cache) -> Dict:
    args = {}
    uid = _resolve_uid(step, parser, cache)
    if uid:
        args["uid"] = uid
    return args

def _build_drag_args(action, step, parser, cache) -> Dict:
    args = {}
    from_uid = parser.find_uid(step.get("source", ""), cache)
    to_uid = _resolve_uid(step, parser, cache)
    if from_uid:
        args["from_uid"] = from_uid
    if to_uid:
        args["to_uid"] = to_uid
    return args

def _build_press_key_args(action, step, parser, cache) -> Dict:
    return {"key": step.get("key", "")}

def _build_type_text_args(action, step, parser, cache) -> Dict:
    args = {"text": resolve_env_vars(step.get("text", ""))}
    submit_key = step.get("submitKey")
    if submit_key:
        args["submitKey"] = submit_key
    return args

def _build_screenshot_args(action, step, parser, cache) -> Dict:
    args = {}
    name = step.get("name", "")
    if "{timestamp}" in name:
        name = name.replace("{timestamp}", time.strftime("%Y%m%d-%H%M%S"))
    if name:
        args["filePath"] = name
    if step.get("fullPage"):
        args["fullPage"] = True
    return args

def _build_wait_for_args(action, step, parser, cache) -> Dict:
    # 修复 Bug E: YAML 用 target 定位时也要传给 wait_for（text 兜底，避免空文本立即匹配）
    text = resolve_env_vars(step.get("text", step.get("target", "")))
    texts = step.get("texts", [text])
    timeout = step.get("timeout", 10000)
    return {"text": [resolve_env_vars(t) for t in texts], "timeout": timeout if timeout else 0}

def _build_scroll_args(action, step, parser, cache) -> Dict:
    direction = step.get("direction", "down")
    scripts = {
        "down": "() => window.scrollTo(0, document.body.scrollHeight)",
        "up": "() => window.scrollTo(0, 0)",
        "top": "() => window.scrollTo(0, 0)",
        "bottom": "() => window.scrollTo(0, document.body.scrollHeight)",
        "left": "() => window.scrollBy(-window.innerWidth, 0)",
        "right": "() => window.scrollBy(window.innerWidth, 0)",
    }
    return {"function": scripts.get(direction, "() => window.scrollTo(0, 0)")}

def _build_script_args(action, step, parser, cache) -> Dict:
    fn = step.get("function", step.get("script", step.get("value", "() => {}")))
    # script 值也过 env 展开：用例 JS 里可直接引用 ${RUN_TAG} 类动态变量
    # （如 pc-004 步骤16 按行文本 ${TPL_ITEM_NAME_2} 定位明细行）
    fn = resolve_env_vars(str(fn)).strip()
    # 用例 YAML 里常写裸语句块（const x = ...; return {...}），而 evaluate_script
    # 工具要求箭头函数体 —— 不以 "(" 或 "function" 开头的一律包成 () => { ... }，
    # 已是函数形式的原样透传。（实测 pc-006 步骤5：裸语句被原样下发 → 语法错误
    # → 步骤被跳过，blob 图片校验从未真正跑过）
    if not (fn.startswith("(") or fn.startswith("function") or fn.startswith("async")):
        fn = "() => {\n" + fn + "\n}"
    return {"function": fn}

def _build_checkbox_args(action, step, parser, cache) -> Dict:
    """checkbox 动作：勾选/取消 el-table 行复选框（evaluate_script 实现）。

    修复（run-20260929 pc-006 步骤 8 被跳过）：引擎此前没有 checkbox 动作，
    `action: checkbox` 直接被跳过 → 行未勾选 → handleBatchQrcode 的
    `if (!ids.value.length) return` 静默返回 → 步骤 9「导出成功」toast 断言必挂。

    语义：
      checked 缺省 True；target（可选）= 行内文本（如点位名称），
      优先操作包含该文本的行；没有 target / 匹配不到行时退回
      「第一个处于目标状态之外的可见行」（勾选场景 = 第一个未勾选行）。

    成功返回 "checkbox-ok: ..."；失败返回含 "error:" 的文本，
    交给 _check_result_has_error 走重试/失败分支（JSON 的 "error" 键带引号、
    匹配不到 "error:" 子串，所以这里必须用纯文本）。
    """
    desired = step.get("checked", True)
    if isinstance(desired, str):
        desired = desired.strip().lower() in ("true", "1", "yes", "on")
    target = resolve_env_vars(str(step.get("target", "") or ""))
    desired_js = "true" if desired else "false"
    target_js = json.dumps(target, ensure_ascii=False)
    fn = f"""() => {{
        const desired = {desired_js};
        const target = {target_js};
        const vis = el => el.offsetParent !== null;
        const norm = s => (s || '').replace(/\\s+/g, '');
        const boxes = [...document.querySelectorAll('.el-table__body-wrapper .el-checkbox')].filter(vis);
        if (!boxes.length) return 'checkbox-error: no visible row checkbox on page';
        let row = null;
        if (target) {{
            row = boxes.find(c => norm(c.closest('.el-table__row')?.textContent || '').includes(norm(target)));
            if (!row) return 'checkbox-error: no row containing target text: ' + target;
        }}
        if (!row) {{
            row = desired ? boxes.find(c => !c.classList.contains('is-checked'))
                          : boxes.find(c => c.classList.contains('is-checked'));
            if (!row) return 'checkbox-ok: already in desired state, no toggle needed';
        }}
        const before = row.classList.contains('is-checked');
        if (before !== desired) {{
            const input = row.querySelector('input.el-checkbox__original') || row.querySelector('input[type=checkbox]');
            const inner = row.querySelector('.el-checkbox__inner');
            (input || inner || row).click();
            // Vue 响应式渲染是异步微任务：click 同步返回后 classList 仍是旧值
            // （实测 pc-006 步骤8：首查 before=false,after=false 误报失败、
            // 重试时已 checked —— 状态其实第一次 click 就改成功了， selection
            // store 也更新了）。双 rAF 等 Vue flush 后再读，消除假阴性。
            const rows = boxes.length;
            return new Promise(resolve => {{
                requestAnimationFrame(() => requestAnimationFrame(() => {{
                    const after = row.classList.contains('is-checked');
                    resolve(after !== desired
                        ? 'checkbox-error: toggle did not reach desired state (before=' + before + ', after=' + after + ')'
                        : 'checkbox-ok: checked ' + before + ' -> ' + after + ' (rows=' + rows + ')');
                }}));
            }});
        }}
        return 'checkbox-ok: checked ' + before + ' -> ' + before + ' (rows=' + boxes.length + ')';
    }}"""
    return {"function": fn}


def _build_select_page_args(action, step, parser, cache) -> Dict:
    page_id = step.get("pageId", step.get("page_index", 0))
    return {"pageId": page_id}

def _build_close_page_args(action, step, parser, cache) -> Dict:
    # pageId 支持三种写法：
    #   整数        -> 关闭该索引的标签页（MCP 原生语义）
    #   "current"   -> 关闭当前选中页（默认）
    #   "last"      -> 关闭 id 最大的页，即最新打开的那个
    # 字符串模式无法在同步 builder 里解析，交给 ActionExecutor._resolve_page_id
    # 异步转成真实索引。
    # 为什么不能写死整数：chrome-devtools-mcp 的页面 id 由 nextPageId++ 单调分配
    # （0,1,2,...）且关闭后不复用，循环里每轮新建的页 id 都不同，写死必关错页。
    page_id = step.get("pageId", step.get("page_id", step.get("page_index", "current")))
    return {"pageId": page_id}


# ============================================================
# 内置 Actions 注册
# ============================================================

# toast 历史 hook：ElMessage / uni.showToast 仅 ~3s 生命期，而 toast_visible
# 断言在动作 + wait_after 之后才开始查 DOM —— 长 wait + 快请求时 toast 早已
# 关闭（实测 pc-006 步骤9：t≈0.5s「导出成功」弹出、t≈3.5s 自动关闭，而
# wait_after=4000ms 后 t=4.0s 才开始轮询 → LiveToast: '' 恒假失败；
# h5-003 登录 toast 同类竞态）。动作执行前幂等注入 MutationObserver +
# 300ms 兜底采样，把出现过的 toast 文本记入 window.__insp_toast_history__，
# 断言侧查「当前 DOM ∪ 历史」。页面刷新/新开 page 后 window 重置，hook 随之
# 清空，每步动作前重注（幂等守卫挡重复安装）。
_TOAST_HOOK_JS = (
    "() => {"
    # 每步动作前重置历史：断言只看「本步骤动作」产生的 toast，避免上一步的
    # 迟到 toast 污染断言（实测 pc-005 步骤13/19：步骤10 的「已导入 1 个巡检项」
    # toast 混进后续 toast_visible 断言的 LiveToast 文本）
    " window.__insp_toast_history__ = [];"
    " if (!window.__insp_toast_observer__) {"
    "  const SELS = '.el-message, .uni-toast, .uni-sample-toast, .uni-toast__content, .el-notification';"
    "  const vis = m => { const cs = getComputedStyle(m); return cs.display !== 'none' && cs.visibility !== 'hidden' && parseFloat(cs.opacity) !== 0; };"
    "  const rec = () => { try { document.querySelectorAll(SELS).forEach(m => {"
    # Element Plus message 关闭后 DOM 可能残留（实测 pc-002 步骤15/19：已关闭的
    # 「新增成功」message 仍被 innerText 读出）——离场中的隐藏 toast 不得录入历史
    "    if (!vis(m)) return;"
    "    const t = (m.innerText || '').trim();"
    "    if (t && window.__insp_toast_history__.indexOf(t) === -1) window.__insp_toast_history__.push(t);"
    "  }); } catch (e) {} };"
    "  try { new MutationObserver(rec).observe(document.documentElement, { childList: true, subtree: true }); } catch (e) {}"
    "  setInterval(rec, 300);"
    "  window.__insp_toast_observer__ = true;"
    " }"
    " return 'toast-hook: reset';"
    "}"
)

def register_builtin_actions():
    """注册所有内置 action 类型"""
    actions = [
        ("navigate", "new_page", _build_navigate_args, False),
        ("open_url", "navigate_page", _build_navigate_args, False),
        ("new_page", "new_page", _build_new_page_args, False),
        ("click", "click", _build_click_args, True),
        ("tap", "click", _build_click_args, True),
        ("fill", "fill", _build_fill_args, True),
        ("type", "fill", _build_fill_args, True),
        ("input", "fill", _build_fill_args, True),
        ("fill_form", "fill_form", _build_fill_form_args, True),
        ("select_option", "fill", _build_select_option_args, True),
        ("select", "fill", _build_select_option_args, True),
        ("choose", "fill", _build_select_option_args, True),
        ("upload_file", "upload_file", _build_upload_args, True),
        ("upload", "upload_file", _build_upload_args, True),
        ("el_upload", "el_upload", _build_upload_args, True),
        ("el_upload_file", "el_upload", _build_upload_args, True),
        ("el_date", "fill", _build_fill_args, True),
        ("el_date_picker", "fill", _build_fill_args, True),
        ("hover", "hover", _build_hover_args, True),
        ("drag_drop", "drag", _build_drag_args, True),
        ("press_key", "press_key", _build_press_key_args, False),
        ("key_press", "press_key", _build_press_key_args, False),
        ("type_text", "type_text", _build_type_text_args, True),
        ("screenshot", "take_screenshot", _build_screenshot_args, False),
        ("capture", "take_screenshot", _build_screenshot_args, False),
        ("wait_for", "wait_for", _build_wait_for_args, False),
        ("wait", "wait_for", _build_wait_for_args, False),
        ("scroll", "evaluate_script", _build_scroll_args, False),
        ("execute_script", "evaluate_script", _build_script_args, False),
        ("js", "evaluate_script", _build_script_args, False),
        # evaluate_script 同名注册：用例直接写 action: evaluate_script 时不再被跳过
        # （实测 pc-006 步骤5 曾因只注册了 execute_script/js 别名而 SKIPPED）
        ("evaluate_script", "evaluate_script", _build_script_args, False),
        ("checkbox", "evaluate_script", _build_checkbox_args, False),
        ("select_page", "select_page", _build_select_page_args, False),
        ("switch_page", "select_page", _build_select_page_args, False),
        ("close_page", "close_page", _build_close_page_args, False),
        ("close_tab", "close_page", _build_close_page_args, False),
    ]
    
    for name, tool, builder, needs_uid in actions:
        ActionRegistry.register(name, tool, builder, needs_uid)


# ============================================================
# 内置 Assertions 注册
# ============================================================

def assert_text_contains(assertion: Dict, snapshot_text: str, parser: 'SnapshotParser', cache: Dict) -> Dict:
    expected = resolve_env_vars(str(assertion.get("expected", "")))
    if snapshot_text and expected:
        passed = expected.lower() in snapshot_text.lower()
        detail = f"'{expected}' {'found' if passed else 'not found'} in snapshot"
    else:
        passed = False
        detail = "no snapshot or empty expected"
    return {"passed": passed, "detail": detail}

def assert_element_visible(assertion: Dict, snapshot_text: str, parser: 'SnapshotParser', cache: Dict) -> Dict:
    # target/expected 必须过 env 展开：pc-004 步骤16 实测 ${TPL_ITEM_NAME_2}
    # 以字面量进快照查找（visible 恒 FAIL），env 里的动态名称全部失效
    target = resolve_env_vars(str(assertion.get("target", assertion.get("expected", ""))))
    if target:
        uid = parser.find_uid(target, cache)
        passed = uid is not None
        detail = f"element '{target}' {'found' if passed else 'not found'}"
    else:
        passed = True
        detail = "no target specified"
    return {"passed": passed, "detail": detail}

def assert_element_hidden(assertion: Dict, snapshot_text: str, parser: 'SnapshotParser', cache: Dict) -> Dict:
    # 同 assert_element_visible：target 需 env 展开（pc-004 实测字面量恒 FAIL）
    target = resolve_env_vars(str(assertion.get("target", assertion.get("expected", ""))))
    # 「元素已消失」= 目标文本不在**当前**快照里。绝不能走 find_uid，两条实测死路：
    #   a) 首查时 parser 持有的还是**步骤起始快照**——js 删除元素后的重渲染尚未
    #      入快照（run-20260930-093048 步骤16：663→602 元素行已删，旧快照仍 Exact
    #      命中 81_469 → 恒 FAIL；空 cache 也救不了，因为搜的本来就是旧文本）；
    #   b) find_uid 模糊层无最低分阈值，'指示灯状态' 能 fuzzy 命中表头
    #      '选择所有行'（score=10），hidden 语义下任何模糊命中都是假阳性。
    # 改为对 snapshot_text 做归一化子串判定；首查快照若不新鲜，由外层
    # Hidden-Retry 轮询（重抓快照后复查）兜底改判。
    if not target:
        return {"passed": True, "detail": "no target specified"}
    _norm = lambda s: re.sub(r"\s+", "", s or "")
    passed = _norm(target) not in _norm(snapshot_text)
    detail = f"element '{target}' {'hidden' if passed else 'still visible in snapshot'}"
    return {"passed": passed, "detail": detail}

def assert_url_contains(assertion: Dict, snapshot_text: str, parser: 'SnapshotParser', cache: Dict) -> Dict:
    expected = resolve_env_vars(str(assertion.get("expected", "")))
    if snapshot_text and expected:
        passed = expected.lower() in snapshot_text.lower()
        detail = f"URL contains '{expected}': {passed}"
    else:
        passed = True
        detail = "skip (no snapshot)"
    return {"passed": passed, "detail": detail}

def assert_toast_visible(assertion: Dict, snapshot_text: str, parser: 'SnapshotParser', cache: Dict) -> Dict:
    expected = resolve_env_vars(str(assertion.get("expected", "")))
    if snapshot_text and expected:
        passed = expected.lower() in snapshot_text.lower()
        detail = f"Toast '{expected}' {'visible' if passed else 'not visible'}"
    else:
        passed = True
        detail = "skip (toast check)"
    return {"passed": passed, "detail": detail}

def assert_element_text(assertion: Dict, snapshot_text: str, parser: 'SnapshotParser', cache: Dict) -> Dict:
    expected = resolve_env_vars(str(assertion.get("expected", "")))
    if snapshot_text and expected:
        passed = expected.lower() in snapshot_text.lower()
        detail = f"Element text contains '{expected}': {passed}"
    else:
        passed = True
        detail = "skip (no snapshot)"
    return {"passed": passed, "detail": detail}

def assert_field_filled(assertion: Dict, snapshot_text: str, parser: 'SnapshotParser', cache: Dict) -> Dict:
    passed = True
    detail = "assume filled (cannot verify via MCP)"
    return {"passed": passed, "detail": detail}

def assert_network_called(assertion: Dict, snapshot_text: str, parser: 'SnapshotParser', cache: Dict) -> Dict:
    passed = True
    detail = "network check skipped (would need network_requests)"
    return {"passed": passed, "detail": detail}

def assert_element_count_greater_than(assertion: Dict, snapshot_text: str, parser: 'SnapshotParser', cache: Dict) -> Dict:
    passed = True
    detail = "count check skipped"
    return {"passed": passed, "detail": detail}

def assert_page_title(assertion: Dict, snapshot_text: str, parser: 'SnapshotParser', cache: Dict) -> Dict:
    expected = resolve_env_vars(str(assertion.get("expected", "")))
    if snapshot_text and expected:
        passed = expected.lower() in snapshot_text.lower()
        detail = f"Page title contains '{expected}': {passed}"
    else:
        passed = True
        detail = "skip (no snapshot)"
    return {"passed": passed, "detail": detail}

def assert_value_equals(assertion: Dict, snapshot_text: str, parser: 'SnapshotParser', cache: Dict) -> Dict:
    expected = resolve_env_vars(str(assertion.get("expected", "")))
    target = assertion.get("target", "")
    if target and expected:
        uid = parser.find_uid(target, cache)
        if uid and uid in parser.elements:
            elem = parser.elements[uid]
            passed = elem.value == expected or elem.text == expected
            detail = f"Value equals '{expected}': {passed} (actual: '{elem.value or elem.text}')"
        else:
            passed = False
            detail = f"Element '{target}' not found"
    else:
        passed = True
        detail = "skip (no target)"
    return {"passed": passed, "detail": detail}

def assert_element_enabled(assertion: Dict, snapshot_text: str, parser: 'SnapshotParser', cache: Dict) -> Dict:
    target = assertion.get("target", "")
    if target:
        uid = parser.find_uid(target, cache)
        if uid and uid in parser.elements:
            elem = parser.elements[uid]
            passed = elem.is_interactive
            detail = f"Element '{target}' enabled: {passed}"
        else:
            passed = False
            detail = f"Element '{target}' not found"
    else:
        passed = True
        detail = "no target specified"
    return {"passed": passed, "detail": detail}


def register_builtin_assertions():
    """注册所有内置断言类型"""
    assertions = [
        ("text_contains", assert_text_contains),
        ("element_visible", assert_element_visible),
        ("element_hidden", assert_element_hidden),
        ("url_contains", assert_url_contains),
        ("toast_visible", assert_toast_visible),
        ("element_text", assert_element_text),
        ("field_filled", assert_field_filled),
        ("network_called", assert_network_called),
        ("element_count_greater_than", assert_element_count_greater_than),
        ("page_title", assert_page_title),
        ("value_equals", assert_value_equals),
        ("element_enabled", assert_element_enabled),
    ]
    
    for name, validator in assertions:
        AssertionRegistry.register(name, validator)


# ============================================================
# Action 执行器 v2.0 — 核心引擎
# ============================================================

class ActionExecutor:
    """
    将 YAML action 映射到 MCP 工具调用
    
    v2.1 特性:
      - LLM 思维链集成：每步执行前后调用 AI 生成思考过程
      - 自动重试机制
      - 执行前快照确认
      - 智能错误恢复
      - 详细日志记录
      - 钩子支持
    """

    def __init__(self, session: ClientSession, parser: SnapshotParser,
                 cache: Dict[str, str], config: Dict[str, Any] = None,
                 think_engine: 'ThinkChainEngine' = None,
                 result_dir: str = None):
        self.session = session
        self.parser = parser
        self.cache = cache
        self.config = {**DEFAULT_CONFIG, **(config or {})}
        self.last_snapshot_text = ""
        self.execution_log: List[str] = []
        self.result_dir = result_dir or RESULT_BASE_DIR
        self.snapshot_dir = os.path.join(self.result_dir, "snapshots") if result_dir else RESULT_BASE_DIR
        
        think_enabled = self.config.get("llm_think_enabled", False)
        if think_engine and (think_enabled or think_engine.enabled):
            self.think_engine = think_engine
            log("  🧠 思维链引擎已连接", 2)
        else:
            self.think_engine = None

    async def _dismiss_password_dialog(self):
        """自动关闭 Chrome 密码泄露检测弹窗（"更改您的密码"提示框）
        
        Chrome 的 Password Leak Detection / Safe Browsing 功能会在检测到
        "不安全密码"时弹出模态对话框，阻塞后续操作。
        --chromeArg 参数无法完全禁用此功能，需要通过 JS 主动关闭。
        
        关闭策略（按优先级）:
        1. 点击弹窗的关闭按钮 (X) 或 确定按钮
        2. 按 Escape 键关闭
        3. 通过 JS 移除弹窗 DOM 元素
        """
        dismiss_js = """
        (() => {
            const results = [];
            
            const passwordKeywords = ['更改您的密码', '密码泄露', 'PasswordLeakDetection',
                                       'password-leak-detection', 'Change your password'];
            
            const selectors = [
                '[role="dialog"]',
                '[role="alertdialog"]',
                '.bubble-content',
                '.password-bubble',
                '.leak-detection-dialog',
                '#bubble-box',
                'cr-bubble',
                '.md-ripple',
                '[aria-label*="密码"]',
                '[aria-label*="password"]',
            ];
            
            let dialogFound = false;
            for (const sel of selectors) {
                const el = document.querySelector(sel);
                if (!el) continue;
                
                const text = el.textContent || '';
                const hasKeyword = passwordKeywords.some(k => text.includes(k));
                
                if (hasKeyword || sel.includes('password') || sel.includes('leak') || sel === 'cr-bubble') {
                    results.push({selector: sel, found: true, text: text.substring(0, 100)});
                    
                    const closeBtns = el.querySelectorAll(
                        '[aria-label="关闭"], [aria-label="Close"], .close-button, ' +
                        '.icon-close, button[id*="close"], [class*="close"]'
                    );
                    if (closeBtns.length > 0) {
                        closeBtns[0].click();
                        results.push({action: 'click_close_button'});
                        dialogFound = true;
                        break;
                    }
                    
                    const confirmBtns = el.querySelectorAll(
                        '[aria-label="确定"], [aria-label="OK"], ' +
                        'button[type="submit"], .confirm-button, .primary-button'
                    );
                    if (confirmBtns.length > 0) {
                        confirmBtns[0].click();
                        results.push({action: 'click_confirm_button'});
                        dialogFound = true;
                        break;
                    }
                    
                    el.style.display = 'none';
                    el.setAttribute('aria-hidden', 'true');
                    results.push({action: 'hide_element'});
                    dialogFound = true;
                    break;
                }
            }
            
            if (!dialogFound) {
                const allElements = document.querySelectorAll('*');
                for (const el of allElements) {
                    if (el.children.length > 5) continue; 
                    const text = (el.textContent || '').trim();
                    if ((text.includes('更改您的密码') || text.includes('密码泄露')) && 
                        text.length < 500) {
                        el.style.display = 'none';
                        results.push({
                            action: 'hide_by_text', 
                            tag: el.tagName,
                            text: text.substring(0, 80)
                        });
                        dialogFound = true;
                        break;
                    }
                }
            }
            
            return {dismissed: dialogFound, details: results};
        })()
        """
        try:
            result = await self.session.call_tool("evaluate_script", {"function": dismiss_js})
            if result and hasattr(result, 'content'):
                for c in result.content:
                    if hasattr(c, 'text'):
                        import json
                        try:
                            data = json.loads(c.text)
                            if data.get('dismissed'):
                                log(f"  🔒 已关闭密码泄露弹窗: {data.get('details', [])}", 2)
                        except (json.JSONDecodeError, TypeError):
                            pass
        except Exception as e:
            log(f"  🔒 密码弹窗检查完成 (无弹窗或已关闭)", 3)

    async def _disable_auto_save(self):
        """禁用被测应用表单页的自动保存/草稿保存机制
        
        某些 Vue/若依应用在表单页面会启动 setInterval 或 watch 定时器，
        在用户操作后自动触发"保存草稿"，导致页面跳转回列表页。
        
        本方法通过注入 JS 来：
        1. 劫持 XMLHttpRequest/fetch 的保存接口调用
        2. 隐藏或禁用"保存草稿"按钮
        3. 拦截 beforeunload 事件防止意外离开
        4. 阻止自动跳转到列表页
        """
        disable_js = """
        (() => {
            const results = {xhrIntercepted: false, buttonDisabled: false};
            
            const saveKeywords = ['saveDraft', 'save-draft', 'autoSave', 'auto-save',
                                   '/draft', '/save', '保存', '草稿', 'draft'];
            
            // 劫持 XMLHttpRequest，拦截保存草稿的 API 调用
            const originalOpen = XMLHttpRequest.prototype.open;
            const originalSend = XMLHttpRequest.prototype.send;
            
            XMLHttpRequest.prototype.open = function(method, url, ...args) {
                this._url = url || '';
                this._method = method || '';
                return originalOpen.call(this, method, url, ...args);
            };
            
            XMLHttpRequest.prototype.send = function(...args) {
                const url = this._url || '';
                const isSaveCall = saveKeywords.some(k => 
                    url.toLowerCase().includes(k.toLowerCase())
                );
                
                if (isSaveCall) {
                    results.xhrIntercepted = true;
                    results.interceptedUrl = url;
                    return;
                }
                return originalSend.call(this, ...args);
            };
            
            // 劫持 fetch API
            const originalFetch = window.fetch;
            window.fetch = function(url, options) {
                const urlStr = typeof url === 'string' ? url : (url && url.url ? url.url : '');
                const isSaveCall = saveKeywords.some(k => 
                    urlStr.toLowerCase().includes(k.toLowerCase())
                );
                
                if (isSaveCall) {
                    results.fetchIntercepted = true;
                    results.fetchUrl = urlStr;
                    return Promise.resolve(new Response(JSON.stringify({code: 200, msg: 'intercepted'}), 
                        {status: 200, headers: {'Content-Type': 'application/json'}}));
                }
                return originalFetch.call(window, url, options);
            };
            
            // 隐藏"保存草稿"按钮
            const allButtons = document.querySelectorAll('button');
            for (const btn of allButtons) {
                const text = (btn.textContent || '').trim();
                if (text === '保存草稿' || text === '保存' || text.includes('草稿')) {
                    btn.style.display = 'none';
                    btn.disabled = true;
                    btn.setAttribute('data-auto-save-disabled', 'true');
                    results.buttonDisabled = true;
                    results.hiddenButton = text;
                }
            }
            
            window.onbeforeunload = null;
            
            // 阻止自动跳转到列表页
            const originalAssign = window.location.assign.bind(window.location);
            const originalReplace = window.location.replace.bind(window.location);
            const listPagePatterns = ['/apply-list', '/list', 'apply-list'];
            
            window.location.assign = function(url) {
                if (listPagePatterns.some(p => url.includes(p))) {
                    results.navigationBlocked = url;
                    return;
                }
                return originalAssign(url);
            };
            
            window.location.replace = function(url) {
                if (listPagePatterns.some(p => url.includes(p))) {
                    results.replaceBlocked = url;
                    return;
                }
                return originalReplace(url);
            };
            
            window.__autoSaveDisabled = true;
            results.success = true;
            return results;
        })()
        """
        try:
            result = await self.session.call_tool("evaluate_script", {"function": disable_js})
            if result and hasattr(result, 'content'):
                for c in result.content:
                    if hasattr(c, 'text'):
                        import json
                        try:
                            data = json.loads(c.text)
                            parts = []
                            if data.get('xhrIntercepted'):
                                parts.append(f"XHR拦截({data.get('interceptedUrl', '')})")
                            if data.get('fetchIntercepted'):
                                parts.append(f"Fetch拦截({data.get('fetchUrl', '')})")
                            if data.get('buttonDisabled'):
                                parts.append(f"按钮隐藏({data.get('hiddenButton', '')})")
                            if data.get('success') and not parts:
                                parts.append("防护机制已注入")
                            
                            if parts:
                                log(f"  🛡️ 自动保存已禁用: {' | '.join(parts)}", 2)
                        except (json.JSONDecodeError, TypeError):
                            pass
        except Exception as e:
            log(f"  🛡️ 自动保存禁用脚本执行完成", 3)

    async def execute(self, step: Dict[str, Any], step_num: int,
                     testcase_config: Dict[str, Any] = None) -> StepResult:
        """执行单个测试步骤（含重试 + 思维链）"""
        start_time = time.time()
        action_type = step.get("action", "")
        desc = step.get("desc", f"步骤{step_num}")
        
        tc_config = testcase_config or {}
        max_retries = tc_config.get("max_retries", self.config["max_retries"])
        retry_delay = tc_config.get("retry_delay", self.config["retry_delay"])
        continue_on_error = tc_config.get("continue_on_error", self.config["continue_on_error"])

        log(f"\n{'='*60}", 1)
        log(f"[步骤{step_num}] {desc}", 1)
        log(f"  动作: {action_type} | 重试上限: {max_retries} | 继续执行: {continue_on_error}", 1)

        await self._dismiss_password_dialog()

        # 每步执行前强制刷新页面快照，避免使用陈旧 uid
        # （弹窗打开/DOM 变化后，上一步快照的 uid 可能已失效或指向错误元素）
        try:
            await self._take_snapshot()
            # uid 缓存只对当次快照有效，页面变化后必须清空，否则会复用失效的 uid
            if getattr(self, 'cache', None) is not None:
                self.cache.clear()
        except Exception as e:
            log(f"  ⚠️ 快照刷新异常（继续）: {e}", 3)

        # toast 历史 hook（幂等，失败静默——只是断言增强，不该影响动作本身）
        try:
            await self.session.call_tool("evaluate_script", {"function": _TOAST_HOOK_JS})
        except Exception:
            pass

        if not getattr(self, '_auto_save_disabled', False):
            try:
                url_result = await self.session.call_tool("evaluate_script", {
                    "function": "() => window.location.href"
                })
                current_url = ""
                if url_result and hasattr(url_result, 'content'):
                    for c in url_result.content:
                        if hasattr(c, 'text') and c.text.startswith('http'):
                            current_url = c.text
                            break

                form_url_patterns = ['/apply', '/add', '/edit', '/form', '/create']
                is_form_page = any(p in current_url for p in form_url_patterns)

                if is_form_page:
                    await self._disable_auto_save()
                    self._auto_save_disabled = True
            except Exception:
                pass

        if action_type == "assert_multiple":
            return await self._execute_assert_multiple(step, step_num, desc, start_time)

        if action_type in ("el_upload", "el_upload_file"):
            return await self._execute_el_upload(step, step_num, desc, start_time)

        if action_type in ("el_date", "el_date_picker"):
            return await self._execute_el_date(step, step_num, desc, start_time)

        if action_type == "verify_network":
            return await self._execute_verify_network(step, step_num, desc, start_time)

        mcp_entry = ActionRegistry.get(action_type)

        if not mcp_entry:
            log(f"  ⏭️ 未实现的动作类型: '{action_type}'", 1)
            log(f"  已注册: {ActionRegistry.list_actions()}", 2)
            return StepResult(
                step_num=step_num, desc=desc, action=action_type,
                status=StepStatus.SKIPPED, mcp_tool="(none)",
                output=f"Action '{action_type}' not implemented. Available: {ActionRegistry.list_actions()}",
                duration_ms=int((time.time() - start_time) * 1000),
            )

        mcp_tool_name, arg_builder = mcp_entry

        # ===== LLM 执行前思考 =====
        thinking_pre = ""
        llm_confidence = 0.0
        llm_suggestions = []
        
        if self.think_engine and self.think_engine.enabled:
            log("  🧠 调用 LLM 分析...", 2)
            pre_think_result = await self.think_engine.pre_execute_think(
                step, step_num, self.parser, self.cache, self.last_snapshot_text
            )
            thinking_pre = pre_think_result.get("thinking", "")
            llm_confidence = pre_think_result.get("confidence", 0.0)
            llm_suggestions = pre_think_result.get("suggestions", [])
            
            if thinking_pre:
                log(f"  💭 LLM 置信度: {llm_confidence:.0%}", 2)

        ActionRegistry.run_pre_hooks(action_type, {
            "step": step, "step_num": step_num, "parser": self.parser, "cache": self.cache,
        })

        if ActionRegistry.needs_uid(action_type):
            log("  📸 获取页面快照...", 2)
            await self._take_snapshot()
            await asyncio.sleep(0.3)

        last_result = None
        for attempt in range(max_retries + 1):
            if attempt > 0:
                log(f"  🔄 重试 ({attempt}/{max_retries})...", 1)
                await asyncio.sleep(retry_delay * attempt)
                
                if ActionRegistry.needs_uid(action_type):
                    await self._take_snapshot()
                    await asyncio.sleep(0.2)

                # 重试必须丢弃 uid 缓存。缓存命中只检查「uid 是否还在无障碍树里」，
                # 而树里的编号在页面重排后会**被复用**，于是同一个 target 文本每次重试
                # 都被映射回**那个已经失效的 uid**：实测 h5-001 步骤 13「提交巡检」，
                # 首点在 22_155 上失败（no longer exists），随后 3 次重试全部
                # `[Cache Hit] '提交巡检' -> 22_155`，13.6s 白烧完，一个快照都没真正用上。
                # 重试的全部意义就是**重新定位**，沿用旧 uid 等于没重试。
                self.cache.clear()

            try:
                mcp_args = arg_builder(action_type, step, self.parser, self.cache)
            except Exception as e:
                log(f"  ❌ 参数构建失败: {type(e).__name__}: {e}", 1)
                log(f"  📋 arg_builder: {arg_builder}", 2)
                log(f"  📋 action_type: {action_type}", 2)
                log(f"  📋 step: {json.dumps(step, ensure_ascii=False)[:200]}", 2)
                tb_lines = traceback.format_exc().splitlines()
                for tl in tb_lines[-8:]:
                    log(f"    {tl}", 3)
                last_result = StepResult(
                    step_num=step_num, desc=desc, action=action_type,
                    status=StepStatus.ERROR, mcp_tool=mcp_tool_name,
                    error=str(e), retry_count=attempt,
                    duration_ms=int((time.time() - start_time) * 1000),
                )
                continue

            if ActionRegistry.needs_uid(action_type) and "uid" in mcp_args:
                mcp_args["includeSnapshot"] = False

            # ===== 修复 Bug A: uid 定位失败时优雅失败，不调 MCP（避免 -32602 Required at uid）=====
            if ActionRegistry.needs_uid(action_type) and "uid" not in mcp_args:
                elapsed_ms = int((time.time() - start_time) * 1000)
                target_txt = step.get("target", step.get("option", step.get("desc", "")))
                err_msg = f"未定位到目标元素: target='{target_txt}'（快照中无匹配，请检查页面结构或 target 文案）"
                log(f"  ❌ {err_msg}", 1)
                last_result = StepResult(
                    step_num=step_num, desc=desc, action=action_type,
                    status=StepStatus.FAILED, mcp_tool="(locate)",
                    error=err_msg, retry_count=attempt,
                    duration_ms=elapsed_ms,
                    snapshot_before=self.last_snapshot_text,
                    snapshot_after=self.last_snapshot_text,
                    snapshot_path=self.last_snapshot_path,
                )
                continue

            # ===== close_page: 把字符串模式（current/last）异步解析成真实 pageId =====
            # 循环里「新建标签页 → 停留 → 关闭」时，新页 id 由 MCP 单调分配，
            # YAML 无法预知；若沿用固定整数会关掉错误的页。
            if action_type in ("close_page", "close_tab") and "pageId" in mcp_args:
                if not isinstance(mcp_args["pageId"], int):
                    _mode = mcp_args["pageId"]
                    _pid = await self._resolve_page_id(_mode)
                    if _pid is None:
                        elapsed_ms = int((time.time() - start_time) * 1000)
                        err_msg = (f"无法解析要关闭的标签页 (pageId={_mode!r})："
                                   f"可能只剩最后一个标签页（MCP 不允许关闭），"
                                   f"或 list_pages 未返回页面")
                        log(f"  ❌ {err_msg}", 1)
                        last_result = StepResult(
                            step_num=step_num, desc=desc, action=action_type,
                            status=StepStatus.FAILED, mcp_tool="list_pages",
                            error=err_msg, retry_count=attempt,
                            duration_ms=elapsed_ms,
                            snapshot_before=self.last_snapshot_text,
                            snapshot_after=self.last_snapshot_text,
                            snapshot_path=self.last_snapshot_path,
                        )
                        continue
                    mcp_args["pageId"] = _pid
                    log(f"  📄 标签页解析: {_mode} -> Page-{_pid}", 2)

            log(f"  🔧 MCP工具: {mcp_tool_name}", 2)
            log(f"  📝 参数: {_safe_json_dumps(mcp_args, ensure_ascii=False, indent=2)}", 2)

            readonly_picker_result = None
            if action_type in ("select_option", "select", "choose") and "uid" in mcp_args:
                uid = mcp_args.get("uid")
                elem = self.parser.elements.get(uid)
                # 修复 Bug G: el-select 的 combobox 统一走 JS picker（不再仅限 is_readonly），
                # 避免 fill 文本进 combobox 或误填到其他输入框
                if elem and (elem.is_readonly or elem.role == "combobox"):
                    log(f"  🔍 检测到选择器({uid}, role={elem.role})，使用JS操作Vue组件", 2)
                    readonly_picker_result = await self._execute_readonly_picker_select(
                        step, step_num, uid, mcp_args.get("value", ""))

            try:
                if readonly_picker_result is not None and isinstance(readonly_picker_result, list):
                    # 修复（Bug I）: picker 成功后**不再提前 return**。
                    # 旧实现直接构造 SUCCESS 并 return，跳过了 wait_after 与本步骤的全部断言 ——
                    # pc-003 step3 的 `element_text: ${ROOM_NAME}` 因此从未执行，
                    # 「下拉其实没选中」被当成成功（假阳性），直到 step7 提交才以
                    # 「所属机房ID不能为空」爆出来，把真实原因藏了两层。
                    elapsed_ms = int((time.time() - start_time) * 1000)
                    log(f"  ✅ 成功 ({elapsed_ms}ms) [readonly-picker]", 1)
                    content_str = "".join(
                        (it.get("text", "") if isinstance(it, dict) else str(it))
                        for it in readonly_picker_result
                    )
                    has_error = False
                    status = StepStatus.SUCCESS
                else:
                    if readonly_picker_result is not None:
                        result = readonly_picker_result
                    else:
                        result = await self.session.call_tool(mcp_tool_name, mcp_args)
                    content_str = self._extract_result_content(result)
                    elapsed_ms = int((time.time() - start_time) * 1000)

                    has_error = self._check_result_has_error(content_str)
                    status = StepStatus.FAILED if has_error else StepStatus.SUCCESS

                # ===== 修复 Bug C: 隐藏 input 组件（el-checkbox/el-switch/el-rate 等）点击降级 =====
                # Element Plus 的 checkbox/switch 实际 input 是 0x0+opacity:0，MCP 判"不可交互"，
                # 降级为 DOM 原生 click（点外层容器/label 同样触发切换）
                if has_error and action_type in ("click", "tap") and "did not become interactive" in (content_str or ""):
                    target_txt = step.get("target", "")
                    if target_txt:
                        log(f"  🔧 [降级] 元素不可交互，尝试 DOM 原生点击 target='{target_txt}'", 1)
                        js_t = json.dumps(target_txt)
                        js = f"""() => {{
                          const t = {js_t};
                          // 策略1: el-form-item 的 label 匹配 → 点内部可点组件（switch/checkbox/radio/rate/slider）
                          const items = [...document.querySelectorAll('.el-form-item')];
                          const item = items.find(i => (i.querySelector('.el-form-item__label')?.innerText || '').trim() === t);
                          if (item) {{
                            const el = item.querySelector('.el-switch, .el-checkbox, .el-radio, .el-rate, .el-slider, button');
                            if (el) {{ el.click(); return 'clicked-form-item: ' + el.className.slice(0, 40); }}
                          }}
                          // 策略2: 控件自身文本匹配（checkbox 文本/radio 文本）
                          const c = [...document.querySelectorAll('.el-checkbox, .el-switch, .el-radio')].find(el => el.innerText && el.innerText.includes(t));
                          if (c) {{ c.click(); return 'clicked-widget: ' + c.className.slice(0, 40); }}
                          // 策略3: 任意叶子文本元素
                          const leaf = [...document.querySelectorAll('span, label, div')].find(el => el.children.length === 0 && el.innerText && el.innerText.trim() === t);
                          if (leaf) {{ leaf.click(); return 'clicked-leaf: ' + leaf.tagName; }}
                          return 'not found: ' + t;
                        }}"""
                        try:
                            js_result = await self.session.call_tool("evaluate_script", {"function": js})
                            js_content = self._extract_result_content(js_result)
                            log(f"  🔧 [降级] DOM 点击结果: {js_content[:80]}", 1)
                            if js_content and "clicked" in js_content.lower():
                                has_error = False
                                status = StepStatus.SUCCESS
                                content_str = f"[dom-fallback] {js_content}"
                                icon, status_text = "✅", "成功(降级)"
                                log(f"  ✅ 降级成功 ({elapsed_ms}ms)", 1)
                        except Exception as e:
                            log(f"  ⚠️ 降级点击异常: {e}", 2)

                icon = "✅" if not has_error else "❌"
                status_text = "成功" if not has_error else "失败"
                log(f"  {icon} {status_text} ({elapsed_ms}ms)" + (f" [重试{attempt}次]" if attempt > 0 else ""), 1)
                
                if content_str:
                    truncated = content_str[:400] + "..." if len(content_str) > 400 else content_str
                    log(f"  📄 结果: {truncated}", 2)

                if has_error and attempt < max_retries:
                    last_result = StepResult(
                        step_num=step_num, desc=desc, action=action_type,
                        status=StepStatus.RETRIED, mcp_tool=mcp_tool_name,
                        mcp_args=mcp_args, output=content_str,
                        error=f"Retry {attempt}: {content_str[:200]}",
                        retry_count=attempt, duration_ms=elapsed_ms,
                    )
                    continue

                wait_cfg = step.get("wait_after")
                if wait_cfg:
                    await self._handle_wait(wait_cfg)

                assertions = self._collect_assertions(step)
                assertion_results = []
                if assertions:
                    log(f"\n  🔍 断言验证 ({len(assertions)} 项):", 1)

                    has_dom_assertions = any(
                        a.get("type") in ("element_visible", "element_hidden", "text_contains", "url_contains",
                                              "toast_visible", "element_text", "page_title")
                        for a in assertions
                    )
                    needs_render_wait = (
                        action_type in ("click", "navigate", "new_page", "open_url", "select_option")
                        and has_dom_assertions
                    )
                    if needs_render_wait:
                        await self._wait_for_assertion_render(action_type)

                    should_snapshot = (
                        action_type in ("navigate", "new_page") or
                        has_dom_assertions
                    )
                    
                    if should_snapshot:
                        await self._take_snapshot()

                    for assertion in assertions:
                        # 修复: toast_visible 断言改实时 DOM 抓取（toast 仅 3s 生命期，快照等待会错过窗口）
                        if assertion.get("type") == "toast_visible":
                            expected_t = resolve_env_vars(str(assertion.get("expected", "")))
                            # 修复: toast 渲染存在延迟，单次抓取偶发竞态（点击后立即查时 toast 未出现）。
                            # 改为轮询抓取：2.5s 内每 250ms 查一次 .el-message，任一时刻命中即 PASS。
                            live_toast = ""
                            poll_deadline = time.time() + 2.5
                            try:
                                while time.time() < poll_deadline:
                                    # 必须同时覆盖两套 UI 库的 toast 容器：
                                    #   · PC（plus-ui / Element Plus）→ .el-message
                                    #   · H5（RuoYi-App-Plus / uni-app）→ .uni-toast / .uni-sample-toast
                                    # 原实现只查 .el-message，而 uni-app 的 uni.showToast 根本不渲染
                                    # 这个类 —— 于是 h5 全部 toast_visible 断言恒 FAIL，detail 是空串
                                    # （实测 h5-001「巡检记录已提交」、h5-002「异常说明不能为空」
                                    # 「上传至少 1 张照片」），把「前端到底提示了什么」这条最关键的
                                    # 线索整个丢掉，排查只能去翻后端日志。
                                    #
                                    # 2026-09-29 再修：轮询窗口从「wait_after 结束后」才开始，与
                                    # toast 的 3s 生命期完全不重叠（长 wait + 快请求时 toast 早已
                                    # 关闭 → LiveToast '' 恒假失败）。故除当前 DOM 外合并查询
                                    # window.__insp_toast_history__（动作前由 _TOAST_HOOK_JS 录制
                                    # 的历史，见 execute 注入点），任一时刻出现过的 toast 都能命中。
                                    js_res = await self.session.call_tool("evaluate_script", {
                                        "function": (
                                            "() => { const sels = ['.el-message', '.uni-toast', "
                                            "'.uni-sample-toast', '.uni-toast__content', "
                                            "'.el-notification']; const out = []; "
                                            "for (const s of sels) { document.querySelectorAll(s)"
                                            ".forEach(m => { const cs = getComputedStyle(m); "
                                            "if (cs.display === 'none' || cs.visibility === 'hidden' "
                                            "|| parseFloat(cs.opacity) === 0) return; "
                                            "const t = (m.innerText || '').trim(); "
                                            "if (t) out.push(t); }); } "
                                            "const hist = window.__insp_toast_history__ || []; "
                                            "return [...new Set([...out, ...hist])].join(' | '); }"
                                        )
                                    })
                                    live_toast = self._extract_result_content(js_res) or ""
                                    # 剥掉 MCP 包裹前缀，否则 80 字截断全被
                                    # `Script ran on page and returned:` 吃掉，看不到真实 toast 文案
                                    live_toast = _strip_mcp_wrapper(live_toast)
                                    if expected_t in live_toast:
                                        break
                                    await asyncio.sleep(0.25)
                                ar = {"passed": expected_t in live_toast, "type": "toast_visible",
                                      "expected": expected_t, "detail": f"LiveToast: '{live_toast[:200]}'",
                                      "confidence": "high"}
                            except Exception as _e:
                                ar = {"passed": False, "type": "toast_visible", "expected": expected_t,
                                      "detail": f"live-check-error: {_e}", "confidence": "high"}
                        elif assertion.get("type") == "element_hidden":
                            # 修复: element_hidden 首查失败时不立即判负 —— 弹窗关闭/
                            # 元素隐藏伴随 Vue 重渲染与过渡动画（实测 pc-006 步骤7：
                            # 点击「关 闭」后 800ms 断言快照里弹窗还在，+1s 才真正消失）。
                            # 对齐 toast 的轮询策略：2.5s 内每 500ms 重抓快照复查，
                            # 任一时刻目标消失即 PASS。
                            ar = self._run_assertion(assertion)
                            if not ar["passed"]:
                                poll_deadline = time.time() + 2.5
                                while not ar["passed"] and time.time() < poll_deadline:
                                    await asyncio.sleep(0.5)
                                    await self._take_snapshot()
                                    ar = self._run_assertion(assertion)
                                if ar["passed"]:
                                    log("    [Hidden-Retry] 目标在轮询窗口内消失 → 改判 PASS", 1)
                        else:
                            ar = self._run_assertion(assertion)
                        assertion_results.append(ar)
                        icon = "✅" if ar["passed"] else "❌"
                        expected = resolve_env_vars(str(assertion.get("expected", "")))
                        log(f"    [{icon}] {assertion['type']}: 期望={expected} → "
                            f"{'PASS' if ar['passed'] else 'FAIL'} | {ar['detail']}", 1)

                    critical_fail = any(
                        not a["passed"] and a.get("confidence") == "high"
                        and a["type"] in ("text_contains", "url_contains", "element_visible", "toast_visible")
                        for a in assertion_results
                    )
                    if critical_fail:
                        status = StepStatus.FAILED_ASSERT
                        log("  ⛔ 关键断言失败!", 1)
                    elif any(not a["passed"] for a in assertion_results):
                        # 修复 Bug F: 断言失败如实标记，不再被吞为 SUCCESS
                        status = StepStatus.FAILED_ASSERT
                        log("  ⚠️ 断言失败（步骤标记 FAILED_ASSERT，流程继续）", 1)

                # ===== LLM 执行后反思 =====
                thinking_post = ""
                if self.think_engine and self.think_engine.enabled:
                    log("  🧠 调用 LLM 反思...", 2)
                    thinking_post = await self.think_engine.post_execute_reflect(
                        step, step_num,
                        StepResult(
                            step_num=step_num, desc=desc, action=action_type,
                            status=status, mcp_tool=mcp_tool_name, mcp_args=mcp_args,
                            output=content_str, assertions=assertion_results,
                            duration_ms=elapsed_ms, retry_count=attempt,
                        ),
                        thinking_pre
                    )

                step_result = StepResult(
                    step_num=step_num, desc=desc, action=action_type,
                    status=status, mcp_tool=mcp_tool_name, mcp_args=mcp_args,
                    output=content_str, assertions=assertion_results,
                    duration_ms=elapsed_ms, retry_count=attempt,
                    snapshot_before=self.last_snapshot_text[:500] if self.last_snapshot_text else "",
                    snapshot_path=self.last_snapshot_path or "",
                    thinking_pre=thinking_pre,
                    thinking_post=thinking_post,
                    llm_confidence=llm_confidence,
                    llm_suggestions=llm_suggestions,
                )

                # ===== 输出思维链内容 =====
                if thinking_pre or thinking_post:
                    think_output = (self.think_engine.format_thinking_output(step_result)
                                   if self.think_engine else "")
                    if think_output:
                        print(think_output)

                ActionRegistry.run_post_hooks(action_type, {
                    "step": step, "step_num": step_num, "parser": self.parser, "cache": self.cache,
                }, step_result)

                return step_result

            except Exception as e:
                elapsed_ms = int((time.time() - start_time) * 1000)
                err_msg = str(e)
                log(f"  ❌ 异常: {err_msg} ({elapsed_ms}ms)" + (f" [重试{attempt}次]" if attempt > 0 else ""), 1)
                
                last_result = StepResult(
                    step_num=step_num, desc=desc, action=action_type,
                    status=StepStatus.ERROR if attempt >= max_retries else StepStatus.RETRIED,
                    mcp_tool=mcp_tool_name, mcp_args=mcp_args if 'mcp_args' in locals() else {},
                    error=err_msg, retry_count=attempt, duration_ms=elapsed_ms,
                )

                if attempt < max_retries:
                    continue

        if last_result:
            return last_result

        return StepResult(
            step_num=step_num, desc=desc, action=action_type,
            status=StepStatus.ERROR, mcp_tool=mcp_tool_name,
            error="All retries exhausted", duration_ms=int((time.time() - start_time) * 1000),
            snapshot_path=self.last_snapshot_path or "",
        )

    async def _take_snapshot(self) -> str:
        """获取页面快照"""
        try:
            result = await self.session.call_tool("take_snapshot", {"verbose": True})
            snapshot_text = ""
            if result.content:
                for item in result.content:
                    if hasattr(item, 'text'):
                        snapshot_text += item.text + "\n"
                    else:
                        snapshot_text += str(item) + "\n"
            
            self.last_snapshot_text = snapshot_text
            self.parser.parse(snapshot_text)

            os.makedirs(self.snapshot_dir, exist_ok=True)
            snap_path = os.path.join(self.snapshot_dir, f"snap-{time.strftime('%Y%m%d-%H%M%S')}.txt")
            with open(snap_path, "w", encoding="utf-8") as f:
                f.write(snapshot_text)

            self.last_snapshot_path = snap_path
            log(f"    [Snapshot] {len(self.parser.elements)} 个元素 → {snap_path}", 3)
            return snapshot_text
        except Exception as e:
            log(f"    [Snapshot Error] {e}", 3)
            return ""

    async def _handle_wait(self, wait_cfg: Dict[str, Any]):
        """
        处理等待配置 - FastAI v2.0 优化版

        优化策略:
          - 默认等待时间缩短50%
          - 导航等待使用短轮询 + 自动切换新标签页
          - 最大等待时间限制
        """
        wait_type = wait_cfg.get("type", "time")

        if wait_type == "time":
            # duration 支持两种写法：
            #   写死整数   10000
            #   环境变量   "${DWELL_MS}"  （原实现直接做算术，字符串会 TypeError）
            raw_duration = resolve_env_vars(str(wait_cfg.get("duration", 1000)))
            try:
                duration = float(raw_duration) / 1000.0
            except (TypeError, ValueError):
                log(f"  ⚠️ wait_after.duration 无法解析({raw_duration!r})，回退 1s", 2)
                duration = 1.0
            # 上限从 10s 提到 _MAX_WAIT_AFTER_SEC：原 10s 截断会让 "停留 15 秒"
            # 这类需求被**静默**砍到 10s，用例作者完全看不出来。
            if duration > _MAX_WAIT_AFTER_SEC:
                log(f"  ⚠️ wait_after.duration={duration:.1f}s 超过上限，"
                    f"截断为 {_MAX_WAIT_AFTER_SEC:.0f}s", 1)
                duration = _MAX_WAIT_AFTER_SEC
            if duration > 0.2:
                log(f"  ⏳ 等待 {duration:.1f}s...", 2)
            await asyncio.sleep(duration)

        elif wait_type == "navigation":
            timeout = wait_cfg.get("timeout", 5000) / 1000.0
            timeout = min(timeout, 10.0)
            log(f"  ⏳ 智能等待导航 ({timeout:.1f}s)...", 2)
            await asyncio.sleep(timeout)

            # 导航等待后，检查是否有新标签页打开并自动切换
            try:
                await self._switch_to_latest_page()
            except Exception as e:
                log(f"  ⚠️ 标签页切换失败（继续执行）: {e}", 3)

    async def _switch_to_latest_page(self):
        """
        检测并切换到最新打开的标签页

        当 click 操作打开了新标签页（如步骤5点击资产评估系统），
        需要自动切换到新标签页才能正确执行后续操作。
        """
        list_result = await self.session.call_tool("list_pages", {})
        if not list_result or not hasattr(list_result, 'content'):
            return

        pages_text = ""
        for item in (list_result.content or []):
            if hasattr(item, 'text'):
                pages_text += item.text + "\n"

        lines = [l.strip() for l in pages_text.strip().split('\n') if l.strip()]
        if len(lines) < 2:
            return

        selected_page = None
        last_page_id = None

        for line in lines:
            if '[selected]' in line:
                selected_page = line
            parts = line.split(':', 1)
            if len(parts) >= 1:
                try:
                    pid = int(parts[0].strip())
                    if last_page_id is None or pid > last_page_id:
                        last_page_id = pid
                except ValueError:
                    pass

        if last_page_id and selected_page:
            sel_parts = selected_page.split(':', 1)
            try:
                sel_id = int(sel_parts[0].strip()) if sel_parts else None
                if sel_id != last_page_id:
                    log(f"  🔄 检测到新标签页，切换到 Page-{last_page_id}...", 2)
                    switch_result = await self.session.call_tool("select_page", {"pageId": last_page_id})
                    err = ""
                    if hasattr(switch_result, 'content') and switch_result.content:
                        for c in switch_result.content:
                            if hasattr(c, 'text'): err += c.text
                    if err and not self._check_result_has_error(err):
                        log(f"  ✅ 已切换到新标签页", 3)
            except (ValueError, IndexError):
                pass

    async def _resolve_page_id(self, mode: Any) -> Optional[int]:
        """把 close_page 的字符串模式（current / last）解析成真实 pageId。

        chrome-devtools-mcp 的 list_pages 输出每行为：``<id>: <url> [selected]``，
        id 由 nextPageId++ 单调分配（0,1,2,...），关闭后不复用。

        返回 None 表示不可关闭（含"只剩最后一个标签页"这种 MCP 硬限制），
        由调用方转成明确失败，而不是把 -32602 这种底层报错抛给用例。
        """
        if isinstance(mode, int):
            return mode
        mode = str(mode or "current").strip().lower()

        listed = await self._list_pages()
        pages = [(pid, selected) for pid, _url, selected in listed]

        if not pages:
            log("  ⚠️ list_pages 未解析到任何标签页", 2)
            return None
        if len(pages) == 1:
            log("  ⚠️ 只剩 1 个标签页，chrome-devtools-mcp 不允许关闭最后一个页", 2)
            return None

        if mode in ("current", "selected", "this", "active"):
            for pid, selected in pages:
                if selected:
                    return pid
            # 没有 [selected] 标记时退化为"最新打开的页"
            return max(p for p, _ in pages)
        if mode in ("last", "latest", "newest"):
            return max(p for p, _ in pages)

        try:
            return int(mode)
        except ValueError:
            log(f"  ⚠️ 无法识别的 pageId 模式: {mode!r}（可用 current/last/整数）", 2)
            return None

    async def _list_pages(self) -> List[Tuple[int, str, bool]]:
        """读取 list_pages，返回 [(id, url, is_selected), ...]（按 id 升序）。

        chrome-devtools-mcp 的输出行为 ``<id>: <url> [selected]``。
        """
        try:
            res = await self.session.call_tool("list_pages", {})
        except Exception as e:
            log(f"  ⚠️ list_pages 调用失败: {e}", 2)
            return []

        text = ""
        if res is not None and getattr(res, "content", None):
            for item in (res.content or []):
                if hasattr(item, "text"):
                    text += item.text + "\n"

        pages: List[Tuple[int, str, bool]] = []
        for line in text.splitlines():
            m = re.match(r"^\s*(\d+)\s*:\s*(.*)$", line)
            if not m:
                continue
            pid = int(m.group(1))
            rest = m.group(2)
            selected = "[selected]" in rest
            url = rest.replace("[selected]", "").strip()
            pages.append((pid, url, selected))
        return sorted(pages, key=lambda p: p[0])

    async def close_extra_pages(self, keep: str = "first") -> int:
        """关闭多余标签页，只留一个。返回实际关闭的数量。

        用途：循环里跑「新建标签页 → 停留 → 关闭」时，若某轮 `new_page`
        因为导航超时被判定失败，引擎会**重试**，而首次那个已经建出来的页
        不会被回收 —— 于是漏一个孤儿标签页（实测抖音 10 轮循环漏了 Page-3）。
        页面 id 从 0 起单调分配，所以"保留 id 最小的那个"= 保留最初的基底页。

        只做显式调用（走 teardown），不自动挂到每步后面，避免误伤
        「一个用例故意开多个标签页」的正常场景。
        """
        pages = await self._list_pages()
        if len(pages) <= 1:
            return 0

        keep_id = pages[0][0]
        if str(keep).lower() in ("last", "latest", "newest"):
            keep_id = pages[-1][0]

        closed = 0
        for pid, url, _ in pages:
            if pid == keep_id:
                continue
            try:
                await self.session.call_tool("close_page", {"pageId": pid})
                closed += 1
                log(f"  🧹 关闭孤儿标签页 Page-{pid} ({url[:60]})", 2)
            except Exception as e:
                log(f"  ⚠️ 关闭 Page-{pid} 失败: {e}", 2)
        return closed

    async def _wait_for_assertion_render(self, action_type: str):
        """步骤内部：action执行后、断言前的渲染等待（轻量版）
        
        针对 click/navigate 等触发DOM变更的操作，
        在断言验证前等待新元素出现，避免时序竞争。
        """
        start_time = time.time()
        # 修复: navigate 类动作（SPA 首次加载/路由按需编译可能 30-60s）等待更久，click 等 DOM 变更保持 3s
        max_wait = 60.0 if action_type in ("navigate", "new_page", "open_url") else 3.0
        stable_count = 0
        min_stable = 2

        await self._take_snapshot()
        last_count = len(self.parser.elements)
        last_text_len = len(self.last_snapshot_text or "")

        while time.time() - start_time < max_wait:
            # 检测全局加载遮罩（RuoYi 等框架的"正在加载系统资源"），出现则视为页面未就绪继续等
            snap_text = self.last_snapshot_text or ""
            if "正在加载系统资源" in snap_text or "加载中" in snap_text:
                log(f"  ⏳ 检测到全局加载遮罩，继续等待页面就绪", 3)
            await asyncio.sleep(0.3)
            await self._take_snapshot()

            curr_count = len(self.parser.elements)
            curr_text_len = len(self.last_snapshot_text or "")

            if (curr_count == last_count and curr_text_len == last_text_len
                    and curr_count >= 20):
                stable_count += 1
                if stable_count >= min_stable:
                    elapsed = time.time() - start_time
                    log(f"  ✅ 断言前渲染就绪 ({curr_count}元素, {elapsed:.1f}s)", 2)
                    return
            else:
                stable_count = 0

            last_count = curr_count
            last_text_len = curr_text_len

        elapsed = time.time() - start_time
        log(f"  ⏱️ 断言前渲染等待超时 ({elapsed:.1f}s), 继续断言", 2)

    async def _wait_for_render_complete(self, prev_action_type: str, prev_step_result):
        """
        等待上一步操作的页面渲染完成

        原则：每个步骤应该在上一步的页面完全渲染后才开始执行。
        利用 MCP take_snapshot 检测 DOM 元素数量是否稳定。

        策略:
          - 非导航操作(fill/type): 快速检查(<0.3s)，已渲染则跳过
          - 导航操作(click/navigate): 完整检查，含新标签页检测+DOM稳定轮询
          - SPA页面特征: 元素数<50 或 快照文本<200字符 = 未渲染完
        """
        NAVIGATION_ACTIONS = {"navigate", "click", "new_page", "open_url"}
        QUICK_CHECK_ACTIONS = {"fill", "type", "input", "select_option", "select", "choose"}

        if prev_action_type in QUICK_CHECK_ACTIONS:
            await asyncio.sleep(0.2)
            return

        if prev_action_type not in NAVIGATION_ACTIONS:
            await asyncio.sleep(0.15)
            return

        start_time = time.time()
        max_wait = 4.0
        stable_count = 0
        min_elements_threshold = 30
        last_element_count = 0
        last_snapshot_text_len = 0

        log("  🔄 等待页面渲染完成...", 2)

        while time.time() - start_time < max_wait:
            try:
                snap_result = await self.session.call_tool("take_snapshot", {"verbose": False})
                snap_text = ""
                if hasattr(snap_result, 'content') and snap_result.content:
                    for item in snap_result.content:
                        if hasattr(item, 'text'):
                            snap_text += item.text + "\n"

                element_count = len(snap_text.split('\n')) if snap_text else 0
                text_len = len(snap_text)

                is_rendered = (
                    element_count >= min_elements_threshold and
                    text_len >= 200 and
                    abs(element_count - last_element_count) < 5 and
                    abs(text_len - last_snapshot_text_len) < 100
                )

                if is_rendered and stable_count >= 1:
                    elapsed = time.time() - start_time
                    self.last_snapshot_text = snap_text
                    self.parser.parse(snap_text)
                    log(f"  ✅ 页面已渲染 ({element_count}元素, {elapsed:.1f}s)", 3)
                    try:
                        await self._switch_to_latest_page()
                    except Exception:
                        pass
                    return

                if is_rendered:
                    stable_count += 1
                else:
                    stable_count = 0

                last_element_count = element_count
                last_snapshot_text_len = text_len

            except Exception:
                pass

            await asyncio.sleep(min(0.5, max_wait - (time.time() - start_time)))

        elapsed = time.time() - start_time
        log(f"  ⏱️ 渲染等待超时 ({elapsed:.1f}s)，继续执行", 3)

    def _find_nearest_interactive_ancestor(self, uid: str, target_roles: set) -> Optional[str]:
        """从给定元素向上查找最近的具有目标role的交互祖先元素

        基于快照的缩进层级+行号邻近性模拟DOM树遍历：
        - 从当前元素的indent_level向上一层一层找
        - 限定在目标元素前后10行范围内，避免匹配到DOM树其他分支的无关元素
        - 返回最近(最高indent_level)且最接近的匹配元素UID

        适用场景：下拉选项的文本在子元素StaticText中，
        需要找到其父级listitem/option等可点击元素。
        """
        elem = self.parser.elements.get(uid)
        if not elem:
            return None
        target_indent = elem.indent_level
        if target_indent <= 0:
            return None

        elem_idx = self.parser.element_order.index(uid) if uid in self.parser.element_order else -1
        if elem_idx < 0:
            return None

        search_range = 15
        start_idx = max(0, elem_idx - search_range)
        end_idx = min(len(self.parser.element_order), elem_idx + search_range)
        nearby_uids = set(self.parser.element_order[start_idx:end_idx])

        best_uid = None
        best_indent = -1

        for cid in nearby_uids:
            if cid == uid:
                continue
            celem = self.parser.elements.get(cid)
            if not celem:
                continue
            if celem.role not in target_roles:
                continue
            if not celem.is_interactive:
                continue
            if 0 < celem.indent_level < target_indent:
                if celem.indent_level > best_indent:
                    best_indent = celem.indent_level
                    best_uid = cid

        return best_uid

    async def _execute_readonly_picker_select(self, step: Dict, step_num: int,
                                              picker_uid: str, option_value: str):
        """el-select 类选择器: click打开 → 在**当前可见**的下拉里点选项

        修复（Bug H，本次造数卡死的真凶）: 必须只在**可见**的 `.el-select-dropdown` 里找选项。
        页面上常同时存在多个下拉（列表搜索区 + 分页 + 弹窗各一组），Element Plus 只把当前打开的
        那个置为可见，其余 popper 虽在 DOM 里但 `display:none`。旧实现用
        `document.querySelectorAll('.el-select-dropdown__item')` 按**文档顺序**取第一个文本命中的，
        于是点到了搜索区那个**隐藏**下拉 → 写进的是搜索框的 v-model，弹窗必填项依旧「请选择…」
        → 提交被「所属机房ID不能为空」拦下，pc-003/004/005 全部造不出数据。

        实测铁证: 旧日志 `totalItems:14` = 全页 5 个下拉的项数之和 (2+3+4+2+3)，
        说明它把 5 个下拉的选项混在一起数了；改成只看可见下拉后 `totalItems:2`（弹窗机房下拉）。
        """
        log(f"  [Picker] Step1: 点击 uid={picker_uid} 打开下拉框", 2)

        js_code = f"""() => {{
            const target = {json.dumps(option_value, ensure_ascii=False)};
            const norm = s => (s || '').replace(/\\s+/g, '').trim();
            const vis = arr => arr.filter(el => el.offsetParent !== null);
            const zOf = d => {{
                const p = d.closest('.el-popper');
                const m = p ? /z-index:\\s*(\\d+)/.exec(p.getAttribute('style') || '') : null;
                return m ? parseInt(m[1], 10) : 0;
            }};
            const dds = vis([...document.querySelectorAll('.el-select-dropdown')]);
            if (!dds.length) return {{ok:false, error:'no visible dropdown', totalItems:0}};
            dds.sort((a, b) => zOf(b) - zOf(a));   // 取最上层那个（= 刚打开的那个）
            const dd = dds[0];
            const items = vis([...dd.querySelectorAll('.el-select-dropdown__item')]);
            let hit = items.find(it => norm(it.textContent) === norm(target));
            if (!hit) hit = items.find(it => norm(it.textContent).includes(norm(target)));
            if (!hit) return {{ok:false, error:'option not in visible dropdown',
                              totalItems:items.length,
                              allText:items.map(i => i.textContent.trim())}};
            hit.click();
            return {{ok:true, clicked:hit.textContent.trim(), totalItems:items.length,
                     visibleDropdowns:dds.length}};
        }}"""

        # 最多两次：首次点击后若下拉仍未展开（no visible dropdown），再点一次重试
        for attempt_i in range(2):
            if attempt_i > 0:
                log(f"  [Picker] 下拉未展开，重试点击 uid={picker_uid}", 1)
                await self.session.call_tool("click", {
                    "uid": picker_uid, "includeSnapshot": False,
                })
            else:
                await self.session.call_tool("click", {
                    "uid": picker_uid, "includeSnapshot": False,
                })
            await asyncio.sleep(1.2 if attempt_i == 0 else 0.9)

            log(f"  [Picker] Step2: 在「可见」下拉中查找并点击'{option_value}'选项...", 2)
            # 修复（run-20260929-191550 pc-005 步骤3）：选项由接口异步加载
            # （form.vue loadRooms → optionselectInspectRoom），点开面板瞬间可能
            # 还是空数组 —— 旧实现立即判「未找到选项」走 fill 兜底，而 fill 对
            # el-select 只塞过滤文本不点 option，Vue model 仍为空 → 提交被
            # 「所属机房不能为空」拦下，后续步骤全部级联（本轮 pc-005 掉到 72%）。
            # 现在：面板已开但 totalItems==0 时按 0.8s 轮询等选项到达（最多 4 次）。
            gave_up = False
            try:
                for poll_i in range(4):
                    result = await self.session.call_tool(
                        "evaluate_script", {"function": js_code})
                    content = self._extract_result_content(result)
                    log(f"  [Picker] JS结果(poll={poll_i}): {content[:160]}", 1)
                    js_payload = None
                    try:
                        js_payload = self._parse_json_from_mcp_response(content)
                    except Exception:
                        js_payload = None

                    if isinstance(js_payload, dict) and js_payload.get("ok") is True:
                        log(f"  [Picker] 已选中 '{js_payload.get('clicked')}'"
                            f"（可见下拉 {js_payload.get('visibleDropdowns')} 个 / 选项 {js_payload.get('totalItems')} 项）", 1)
                        await asyncio.sleep(0.5)
                        return [{"type": "text",
                                 "text": f"picker selected '{option_value}' on visible dropdown"}]

                    if isinstance(js_payload, dict) and js_payload.get("error") == "no visible dropdown":
                        break  # 面板没开 → 外层重试点击

                    if isinstance(js_payload, dict) and js_payload.get("totalItems", 0) == 0 and poll_i < 3:
                        await asyncio.sleep(0.8)  # 选项加载中 → 继续轮询
                        continue

                    # 选项列表非空但没有目标文本 → 真不存在，不再假成功
                    log(f"  ⚠️ [Picker] 可见下拉中未找到选项（items={js_payload.get('totalItems') if isinstance(js_payload, dict) else '?'}），走 MCP fill 兜底", 1)
                    gave_up = True
                    break
                if gave_up:
                    return None
            except Exception as e:
                log(f"  [Picker] JS失败: {e}", 1)
                return None

        log(f"  ⚠️ [Picker] 两次尝试后下拉仍未展开，走 MCP fill 兜底", 1)
        return None

    def _find_picker_option(self, option_value: str, picker_uid: str,
                             target_roles: set, pre_click_uids=None) -> Optional[str]:
        best_uid = None
        best_match_len = 0
        for uid, elem in self.parser.elements.items():
            if uid == picker_uid or (pre_click_uids and uid in pre_click_uids):
                continue
            if elem.role not in target_roles or not elem.is_interactive:
                continue
            if elem.text and option_value in elem.text:
                match_len = len(option_value)
                if match_len > best_match_len:
                    best_match_len = match_len
                    best_uid = uid
                    log(f"    [命中role] uid={uid} role={elem.role} text='{elem.text}'", 3)
        if best_uid:
            return best_uid
        text_matches = self.parser.find_by_text_contains(option_value)
        for me in text_matches:
            mu = me.uid
            if mu == picker_uid or (pre_click_uids and mu in pre_click_uids):
                continue
            if me.role in target_roles and me.is_interactive:
                log(f"    [命中text] uid={mu} role={me.role}", 2)
                return mu
            pu = self._find_nearest_interactive_ancestor(mu, target_roles)
            if pu and pu != picker_uid:
                log(f"    [命中祖先] uid={pu} 源自uid={mu}", 2)
                return pu
        return None

    async def _execute_el_upload(self, step: Dict, step_num: int,
                                  desc: str, start_time: float) -> StepResult:
        """Element UI el-upload 文件上传（增强版方法2 - 一步完成）

        内部自动执行三步操作:
          1. click 上传按钮
          2. execute_script 暴露隐藏的 input[type=file]
          3. upload_file 上传文件

        YAML 用法:
          - step: N
            action: el_upload
            target: 上传按钮文本或uid
            path: C:\\path\\to\\file.docx
            file_label: 核准申请文件    # 可选，用于定位文件输入框所在行
            _locator:
              uid: "60_370"              # 可选，上传按钮的uid
            wait_after:
              type: time
              duration: 3000
        """
        log(f"  📎 [el_upload] Element UI 文件上传开始", 1)

        target = step.get("target", "")
        file_path = resolve_env_vars(step.get("path", ""))
        file_label = step.get("file_label", step.get("row_label", ""))
        locator = step.get("_locator", {}) or {}
        button_uid = locator.get("uid")
        wait_after = step.get("wait_after", {})
        wait_duration = int(wait_after.get("duration", 2000)) if wait_after else 2000

        if not file_path:
            elapsed = int((time.time() - start_time) * 1000)
            return StepResult(
                step_num=step_num, desc=desc, action="el_upload",
                status=StepStatus.ERROR, mcp_tool="(el_upload)",
                error="Missing required parameter: 'path' (file path to upload)",
                duration_ms=elapsed,
            )

        log(f"  📎 [el_upload] 文件路径: {file_path}", 2)
        if file_label:
            log(f"  📎 [el_upload] 文件标签(行定位): {file_label}", 2)
        if button_uid:
            log(f"  📎 [el_upload] 按钮UID: {button_uid}", 2)

        sub_steps = []

        try:
            await self._take_snapshot()
            await asyncio.sleep(0.3)

            step_start_time = time.time()
            log(f"  📎 ═════════════════════ el_upload 开始 ═════════════════════", 1)
            log(f"  📎 📋 参数: target='{target}' | file_label='{file_label}'", 2)
            log(f"  📎 📁 文件: {os.path.basename(file_path)} (存在:{os.path.isfile(file_path)})", 2)
            log(f"  📎 🔖 UID: {button_uid or '(未指定)'} | 等待: {wait_duration}ms | 元素数: {len(self.parser.elements)}", 2)

            url_before = getattr(self, 'last_snapshot_url', '') or ''
            log(f"  📎 🌐 执行前URL: {url_before} | 耗时: {(time.time()-step_start_time)*1000:.0f}ms", 2)

            if url_before and ('/apply-list' in url_before or '/list' in url_before) and '/apply' not in url_before:
                log(f"  📎 ⚠️ ═════ 检测到已在列表页！尝试提前恢复表单 ═════", 1)
                try:
                    await self._take_snapshot()
                    new_btn_uid = None
                    for uid, elem in self.parser.elements.items():
                        elem_text = (elem.text or "") + (getattr(elem, 'description', '') or "")
                        if elem.role == "button" and "新增" in elem_text:
                            new_btn_uid = uid
                            break
                    if new_btn_uid:
                        log(f"  📎 🔧 找到'新增'按钮 uid={new_btn_uid}，点击打开新表单...", 2)
                        await self.session.call_tool("click", {"uid": new_btn_uid, "includeSnapshot": False})
                        await asyncio.sleep(2000 / 1000.0)
                        await self._take_snapshot()
                        url_before = getattr(self, 'last_snapshot_url', '') or ''
                        log(f"  📎 ✅ 表单页已恢复: {url_before}", 1)
                        sub_steps.append("🔧提前恢复表单: ✅")
                    else:
                        log(f"  📎 ⚠️ 未找到'新增'按钮，继续执行(可能失败)", 2)
                        sub_steps.append("🔧提前恢复: ❌未找到新增按钮")
                except Exception as pre_err:
                    log(f"  📎 ⚠️ 提前恢复异常: {pre_err}", 2)
                    sub_steps.append(f"🔧提前恢复异常: {pre_err}")

            sub_step_1 = f"[1/3] 点击上传按钮"
            log(f"  📎 ── {sub_step_1} ──", 2)

            click_uid = None
            if button_uid:
                if button_uid in self.parser.elements:
                    click_uid = button_uid
                    log(f"  📎 ✅ [P1-UID直击] 使用指定UID: {button_uid}", 2)
                else:
                    log(f"  📎 🔄 [UID漂移] '{button_uid}' 不在快照({len(self.parser.elements)}个元素)中，启动SmartMatch...", 2)
                    click_uid = self._find_upload_button_uid(target, button_uid, file_label)
                    if click_uid:
                        log(f"  📎 ✅ [P2-SmartMatch] 后缀匹配成功: {button_uid} → {click_uid} (耗时:{(time.time()-step_start_time)*1000:.0f}ms)", 1)
                    else:
                        log(f"  📎 ⚠️ [P2-SmartMatch] 未匹配，将尝试[P3-JS按行点击]", 2)
            else:
                click_uid = _resolve_uid(step, self.parser, self.cache, require_interactive=True)
                if click_uid:
                    elem = self.parser.elements.get(click_uid)
                    role = elem.role if elem else "?"
                    log(f"  📎 解析到UID: {click_uid} (role={role})", 3)
                    if role in ("radio", "checkbox"):
                        log(f"  📎 ⚠️ 匹配到{role}而非button，尝试排除非button元素...", 2)
                        click_uid = self._find_upload_button_uid(target, None, file_label)
                        if click_uid:
                            log(f"  📎 ✅ 重新匹配到UID: {click_uid}", 3)

            if not click_uid:
                if file_label:
                    log(f"  📎 🔍 [P3-JS按行] 尝试按file_label='{file_label}'定位上传按钮...", 2)
                    js_click_label = json.dumps(file_label, ensure_ascii=False).strip('"')
                    js_click_fn = (
                        "() => {"
                        " var label = '" + js_click_label.replace("'", "\\'") + "';"
                        " var rows = document.querySelectorAll('tr');"
                        " for (var i = 0; i < rows.length; i++) {"
                        "   if (rows[i].textContent.indexOf(label) !== -1) {"
                        "     var btn = rows[i].querySelector('button');"
                        "     if (!btn) {"
                        "       var cells = rows[i].querySelectorAll('td');"
                        "       for (var j = 0; j < cells.length; j++) {"
                        "         if (cells[j].textContent.indexOf('上传') !== -1) {"
                        "           btn = cells[j].querySelector('button');"
                        "           if (btn) break;"
                        "         }"
                        "       }"
                        "     }"
                        "     if (btn) { btn.click(); return JSON.stringify({js_click:true,label:label}); }"
                        "   }"
                        " }"
                        " return JSON.stringify({js_click:false,error:'row_not_found'});"
                        "}"
                    )
                    js_click_result = await self.session.call_tool("evaluate_script", {"function": js_click_fn})
                    js_click_content = self._extract_result_content(js_click_result)
                    log(f"  📎 [P3-JS按行] 结果: {js_click_content[:150] if js_click_content else 'N/A'} (耗时:{(time.time()-step_start_time)*1000:.0f}ms)", 2)

                    js_click_info = self._parse_json_from_mcp_response(js_click_content)
                    if isinstance(js_click_info, dict) and js_click_info.get("js_click"):
                        log(f"  📎 ✅ JS成功点击了 '{file_label}' 行的上传按钮", 2)
                        sub_steps.append(f"{sub_step_1}: ✅(JS按行)")
                        click_uid = None
                    else:
                        elapsed = int((time.time() - start_time) * 1000)
                        return StepResult(
                            step_num=step_num, desc=desc, action="el_upload",
                            status=StepStatus.ERROR, mcp_tool="(el_upload)",
                            error=f"Cannot find upload button for target='{target}' (UID stale, JS click also failed)",
                            duration_ms=elapsed,
                        )
                else:
                    elapsed = int((time.time() - start_time) * 1000)
                    return StepResult(
                        step_num=step_num, desc=desc, action="el_upload",
                        status=StepStatus.ERROR, mcp_tool="(el_upload)",
                        error=f"Cannot find upload button for target='{target}'",
                        duration_ms=elapsed,
                    )

            if click_uid:
                click_result = await self.session.call_tool("click", {
                    "uid": click_uid,
                    "includeSnapshot": False,
                })
                click_content = self._extract_result_content(click_result)
                log(f"  📎 ✅ [MCP-click] UID={click_uid} 结果: {click_content[:60] if click_content else 'OK'} (耗时:{(time.time()-step_start_time)*1000:.0f}ms)", 2)
            else:
                log(f"  📎 ✅ [JS-click] 已通过JS完成按钮点击 (耗时:{(time.time()-step_start_time)*1000:.0f}ms)", 2)
            sub_steps.append(f"{sub_step_1}: ✅")

            await asyncio.sleep(0.5)

            sub_step_2 = "[2/3] 暴露隐藏的文件输入框"
            log(f"  📎 ── {sub_step_2} ── | label='{file_label or target}'", 2)

            search_label = json.dumps(file_label or target, ensure_ascii=False).strip('"')
            expose_ts = str(int(time.time() * 1000))

            expose_fn = (
                "() => {"
                " var label = '" + search_label.replace("'", "\\'") + "';"
                " var ts = '" + expose_ts + "';"
                " var oldExposed = document.querySelectorAll('[data-el-upload-exposed]');"
                " for (var oi = 0; oi < oldExposed.length; oi++) {"
                "   oldExposed[oi].removeAttribute('data-el-upload-exposed');"
                "   oldExposed[oi].removeAttribute('aria-label');"
                "   oldExposed[oi].style.cssText = '';"
                "   oldExposed[oi].setAttribute('type','file');"
                " }"
                " var rows = document.querySelectorAll('tr');"
                " var fileInput = null;"
                " var foundByRow = false;"
                " for (var i = 0; i < rows.length; i++) {"
                "   if (label && rows[i].textContent.indexOf(label) !== -1) {"
                "     fileInput = rows[i].querySelector('input[type=file]');"
                "     if (!fileInput) {"
                "       fileInput = rows[i].closest('table') ? rows[i].closest('table').querySelector('input[type=file]') : null;"
                "     }"
                "     if (!fileInput) {"
                "       fileInput = rows[i].parentElement ? rows[i].parentElement.querySelector('input[type=file]') : null;"
                "     }"
                "     foundByRow = !!fileInput;"
                "     break;"
                "   }"
                " }"
                " if (!fileInput) {"
                "   var allInputs = document.querySelectorAll('input[type=file]');"
                "   if (allInputs.length > 1 && label) {"
                "     for (var ai = allInputs.length - 1; ai >= 0; ai--) {"
                "       var pEl = allInputs[ai].closest('tr') || allInputs[ai].parentElement;"
                "       if (pEl && pEl.textContent.indexOf(label) !== -1) {"
                "         fileInput = allInputs[ai];"
                "         foundByRow = true;"
                "         break;"
                "       }"
                "     }"
                "   }"
                "   if (!fileInput && allInputs.length > 0) {"
                "     fileInput = allInputs[allInputs.length - 1];"
                "   }"
                " }"
                " if (!fileInput) return JSON.stringify({error:'no_file_input_found',found:false});"
                " fileInput.style.cssText = 'position:fixed!important;top:50%!important;left:50%!important;transform:translate(-50%,-50%)!important;width:300px!important;height:40px!important;display:block!important;visibility:visible!important;opacity:1!important;z-index:2147483647!important;border:2px solid red!important;background:yellow!important;font-size:14px!important;padding:5px!important';"
                " fileInput.setAttribute('data-el-upload-exposed','true');"
                " fileInput.setAttribute('data-expose-ts',ts);"
                " fileInput.setAttribute('aria-label','exposed-upload-' + ts);"
                " fileInput.setAttribute('role','textbox');"
                " fileInput.setAttribute('tabindex','0');"
                " fileInput.removeAttribute('disabled');"
                " fileInput.removeAttribute('hidden');"
                " if (!fileInput.id) fileInput.id = 'exposed-file-input-' + ts;"
                " var r = fileInput.getBoundingClientRect();"
                " return JSON.stringify({found:true,id:fileInput.id,name:fileInput.name||'',exposed:true,ts:ts,w:r.width,h:r.height,foundByRow:foundByRow});"
                "}"
            )

            script_result = await self.session.call_tool("evaluate_script", {"function": expose_fn})
            script_content = self._extract_result_content(script_result)
            log(f"  📎 [expose] 结果: {script_content[:200] if script_content else 'N/A'} (耗时:{(time.time()-step_start_time)*1000:.0f}ms)", 2)

            expose_info = self._parse_json_from_mcp_response(script_content)

            mcp_error = self._check_result_has_error(script_content) if script_content else True
            js_success = isinstance(expose_info, dict) and expose_info.get("found")

            if not js_success and mcp_error:
                elapsed = int((time.time() - start_time) * 1000)
                return StepResult(
                    step_num=step_num, desc=desc, action="el_upload",
                    status=StepStatus.ERROR, mcp_tool="(el_upload)",
                    error=f"JS execution failed: {script_content[:200] if script_content else 'no response'}",
                    output=script_content,
                    duration_ms=elapsed,
                )

            if not js_success:
                log(f"  📎 ⚠️ [2/3] 无法解析JS返回值但MCP未报错，继续尝试上传...", 2)

            sub_steps.append(f"{sub_step_2}: ✅")

            await asyncio.sleep(0.3)

            await self._take_snapshot()

            sub_step_3 = "[3/3] 执行文件上传"
            log(f"  📎 ── {sub_step_3} ── | path={os.path.basename(file_path)}", 2)

            upload_args = {"filePath": file_path}

            exposed_uid = None
            best_match = None
            ts_marker = f"exposed-upload-{expose_ts}"
            for uid, elem in self.parser.elements.items():
                elem_text = ((elem.text or "") + " " + (elem.name or "") + " " + (getattr(elem, 'description', '') or "")).lower()
                if ts_marker.lower() in elem_text:
                    exposed_uid = uid
                    log(f"  📎 精确匹配到时间戳标记的input: uid={uid}", 3)
                    break
                if "exposed-file-input" in elem_text:
                    best_match = uid
                if elem.role == "textbox" and ("file" in (elem.name or "").lower() or "upload" in elem_text):
                    if not best_match:
                        best_match = uid

            if not exposed_uid and best_match:
                exposed_uid = best_match
                log(f"  📎 使用备选input: uid={best_match}（非精确匹配）", 3)

            if exposed_uid:
                upload_args["uid"] = exposed_uid
                log(f"  📎 上传目标UID: {exposed_uid}", 3)

            upload_args["includeSnapshot"] = False

            upload_result = await self.session.call_tool("upload_file", upload_args)
            upload_content = self._extract_result_content(upload_result)
            log(f"  📎 ✅ [upload] 结果: {upload_content[:120] if upload_content else 'OK'} (耗时:{(time.time()-step_start_time)*1000:.0f}ms)", 2)
            sub_steps.append(f"{sub_step_3}: ✅")

            if wait_duration > 0:
                log(f"  📎 ⏳ 等待 {wait_duration}ms 让页面处理文件...", 2)
                await asyncio.sleep(wait_duration / 1000.0)

            # 修复: 不再发送 Escape 关闭"OS级文件对话框"。
            # 原因: chrome-devtools-mcp 的 upload_file 走 CDP DOM.setFileInputFiles 注入文件，
            #       根本不打开 OS 文件对话框；而 Escape 会被 Element Plus el-dialog 捕获
            #       (close-on-press-escape 默认 true)，导致上传后整个新增弹窗被误关，
            #       后续"确 定"等步骤全部错位（曾把提交点成"搜索"按钮）。
            sub_step_4 = "[4/3] 跳过关闭文件对话框(Escape 会误关 el-dialog)"
            log(f"  📎 {sub_step_4}", 2)
            sub_steps.append(f"{sub_step_4}: ✅(skip, CDP注入无OS对话框)")

            url_after = getattr(self, 'last_snapshot_url', '') or ''
            total_elapsed = (time.time() - step_start_time) * 1000
            log(f"  📎 🌐 执行后URL: {url_after} | 总耗时: {total_elapsed:.0f}ms", 2)

            if url_before and url_after and url_before != url_after:
                log(f"  📎 ⚠️ ═════ URL变化检测 ═════", 1)
                log(f"  📎 ⚠️ 变化: {url_before}", 2)
                log(f"  📎 ⚠️ →   {url_after}", 2)
                if '/apply-list' in url_after or '/list' in url_after:
                    log(f"  📎 🔧 检测到列表页跳转，启动自动恢复...", 1)
                    try:
                        await self._take_snapshot()
                        new_btn_uid = None
                        for uid, elem in self.parser.elements.items():
                            elem_text = (elem.text or "") + (getattr(elem, 'description', '') or "")
                            if elem.role == "button" and "新增" in elem_text:
                                new_btn_uid = uid
                                break
                        if new_btn_uid:
                            log(f"  📎 🔧 找到'新增'按钮 uid={new_btn_uid}，点击恢复表单...", 2)
                            await self.session.call_tool("click", {"uid": new_btn_uid, "includeSnapshot": False})
                            await asyncio.sleep(1500 / 1000.0)
                            await self._take_snapshot()
                            restored_url = getattr(self, 'last_snapshot_url', '') or ''
                            if '/apply' in restored_url:
                                log(f"  📎 ✅ 表单页恢复成功: {restored_url} (总耗时:{(time.time()-step_start_time)*1000:.0f}ms)", 1)
                                sub_steps.append("🔧页面自动恢复: ✅")
                            else:
                                log(f"  📎 ⚠️ [el_upload] 恢复后URL: {restored_url}", 2)
                                sub_steps.append("🔧页面自动恢复: ⚠️")
                        else:
                            log(f"  📎 ⚠️ [el_upload] 未找到'新增'按钮，无法自动恢复", 2)
                            sub_steps.append("🔧页面恢复失败: ❌未找到新增按钮")
                    except Exception as restore_err:
                        log(f"  📎 ⚠️ [el_upload] 自动恢复异常: {restore_err}", 2)
                        sub_steps.append(f"🔧页面恢复异常: {restore_err}")

            elapsed = int((time.time() - start_time) * 1000)
            log(f"  📎 ═════════════════════ el_upload 完成 ═════════════════════", 1)
            log(f"  📎 📊 结果: ✅ 成功 | 文件: {os.path.basename(file_path)} | 总耗时: {elapsed}ms", 1)

            return StepResult(
                step_num=step_num, desc=desc, action="el_upload",
                status=StepStatus.SUCCESS, mcp_tool="(el_upload)",
                mcp_args={"target": target, "filePath": file_path},
                output=f"File uploaded successfully: {file_path}\nSub-steps: {' | '.join(sub_steps)}",
                duration_ms=elapsed,
                snapshot_before=self.last_snapshot_text,
                snapshot_after=self.last_snapshot_text,
                snapshot_path=self.last_snapshot_path,
            )

        except Exception as e:
            tb_lines = traceback.format_exc().splitlines()
            elapsed = int((time.time() - start_time) * 1000)
            log(f"  📎 [el_upload] ❌ 异常: {e}", 1)
            for tl in tb_lines[-6:]:
                log(f"    {tl}", 3)

            return StepResult(
                step_num=step_num, desc=desc, action="el_upload",
                status=StepStatus.ERROR, mcp_tool="(el_upload)",
                error=str(e),
                output=f"Failed at: {' | '.join(sub_steps)}",
                duration_ms=elapsed,
            )

    async def _execute_el_date(self, step: Dict, step_num: int,
                                desc: str, start_time: float) -> StepResult:
        """Element UI el-date-picker 日期选择器填写（一步完成）

        内部自动执行三步操作:
          1. click 日期输入框（打开日期选择面板）
          2. sleep 等待面板渲染
          3. fill 填入日期值

        YAML 用法:
          - step: N
            action: el_date
            target: 请选择评估基准日    # placeholder 或 label
            value: '2026-05-10'         # 日期字符串
            wait_after:
              type: time
              duration: 500             # 面板打开后等待时间(默认500ms)
        """
        log(f"  📅 [el_date] Element UI 日期选择器开始", 1)

        target = step.get("target", "")
        value = resolve_env_vars(step.get("value", ""))
        wait_after = step.get("wait_after", {})
        panel_wait = int(wait_after.get("duration", 500)) if wait_after else 500

        if not value:
            elapsed = int((time.time() - start_time) * 1000)
            return StepResult(
                step_num=step_num, desc=desc, action="el_date",
                status=StepStatus.ERROR, mcp_tool="(el_date)",
                error="Missing required parameter: 'value' (date value to fill)",
                duration_ms=elapsed,
            )

        log(f"  📅 [el_date] 目标: '{target}' | 值: '{value}' | 面板等待: {panel_wait}ms", 2)

        sub_steps = []

        try:
            sub_step_1 = "[1/3] 点击日期输入框"
            log(f"  📅 {sub_step_1}: target='{target}'", 2)

            click_uid = _resolve_uid(step, self.parser, self.cache, prefer_role="combobox")
            if not click_uid:
                click_uid = _resolve_uid(step, self.parser, self.cache)
            if not click_uid:
                elapsed = int((time.time() - start_time) * 1000)
                return StepResult(
                    step_num=step_num, desc=desc, action="el_date",
                    status=StepStatus.ERROR, mcp_tool="(el_date)",
                    error=f"Cannot find date input element for target='{target}'",
                    duration_ms=elapsed,
                )

            click_result = await self.session.call_tool("click", {"uid": click_uid, "includeSnapshot": False})
            click_content = self._extract_result_content(click_result)
            log(f"  📅 {sub_step_1} 结果: {click_content[:80] if click_content else 'OK'}", 2)
            sub_steps.append(f"{sub_step_1}: ✅")

            sub_step_2 = f"[2/3] 等待日期面板渲染 ({panel_wait}ms)"
            await asyncio.sleep(panel_wait / 1000.0)
            sub_steps.append(f"{sub_step_2}: ✅")

            await self._take_snapshot()

            sub_step_3 = "[3/3] 填入日期值"
            log(f"  📅 {sub_step_3}: value='{value}'", 2)

            fill_args = {"value": value}
            if click_uid:
                fill_args["uid"] = click_uid

            fill_result = await self.session.call_tool("fill", fill_args)
            fill_content = self._extract_result_content(fill_result)
            log(f"  📅 {sub_step_3} 结果: {fill_content[:120] if fill_content else 'OK'}", 2)
            sub_steps.append(f"{sub_step_3}: ✅")

            elapsed = int((time.time() - start_time) * 1000)
            log(f"  📅 [el_date] 完成 ({elapsed}ms)", 1)

            return StepResult(
                step_num=step_num, desc=desc, action="el_date",
                status=StepStatus.SUCCESS, mcp_tool="(el_date)",
                mcp_args={"target": target, "value": value},
                output=f"Date filled successfully: {value}\nSub-steps: {' | '.join(sub_steps)}",
                duration_ms=elapsed,
                snapshot_before=self.last_snapshot_text,
                snapshot_after=self.last_snapshot_text,
                snapshot_path=self.last_snapshot_path,
            )

        except Exception as e:
            tb_lines = traceback.format_exc().splitlines()
            elapsed = int((time.time() - start_time) * 1000)
            log(f"  📅 [el_date] ❌ 异常: {e}", 1)
            for tl in tb_lines[-6:]:
                log(f"    {tl}", 3)

            return StepResult(
                step_num=step_num, desc=desc, action="el_date",
                status=StepStatus.ERROR, mcp_tool="(el_date)",
                error=str(e),
                output=f"Failed at: {' | '.join(sub_steps)}",
                duration_ms=elapsed,
            )

    def _find_upload_button_uid(self, target: str, preferred_uid: Optional[str] = None,
                                  file_label: Optional[str] = None) -> Optional[str]:
        """上下文感知的上传按钮定位（三级策略）

        策略优先级:
          P1: UID后缀模糊匹配 (60_370 -> *_370)
          P2: file_label上下文定位 (找到"核准申请文件"行→取该行button"上传")
          P3: 智能文本匹配 (排除radio/checkbox，优先button角色)
        """
        log(f"    [SmartMatch] target='{target}' preferred_uid={preferred_uid} file_label={file_label}", 3)

        INTERACTIVE_ROLES = {"button", "link", "textbox", "combobox", "menuitem"}
        TEXT_ONLY_ROLES = {"strong", "statictext", "inline textbox", "heading",
                           "listitem", "paragraph", "label", "image"}

        if preferred_uid:
            uid_suffix = preferred_uid.split("_")[-1] if "_" in preferred_uid else preferred_uid
            p1_candidates = []
            for uid, elem in self.parser.elements.items():
                if uid.endswith("_" + uid_suffix) or uid == uid_suffix:
                    role = getattr(elem, 'role', '') or ''
                    text = (getattr(elem, 'text', '') or '')[:40]
                    log(f"    [SmartMatch-P1] UID后缀匹配: {uid} (role={role} text='{text}')", 3)
                    if role in INTERACTIVE_ROLES:
                        log(f"    [SmartMatch-P1] ✅ 找到交互元素: {uid}", 3)
                        return uid
                    elif role not in TEXT_ONLY_ROLES and role not in ("radio", "checkbox", "switch"):
                        p1_candidates.append((uid, role, text))

            if p1_candidates and not file_label:
                uid, role, text = p1_candidates[0]
                log(f"    [SmartMatch-P1] ⚠️ 使用非标准角色: {uid} (role={role})", 2)
                return uid

            if p1_candidates:
                log(f"    [SmartMatch-P1] 后缀匹配到非交互元素({len(p1_candidates)}个)，降级到P2...", 3)

        if file_label:
            label_uids = []
            for uid, elem in self.parser.elements.items():
                text = (elem.text or "") + (elem.name or "") + (getattr(elem, 'description', '') or "")
                if file_label.lower() in text.lower():
                    label_uids.append((uid, elem))

            if label_uids:
                log(f"    [SmartMatch-P2] file_label '{file_label}' 匹配到 {len(label_uids)} 个元素:", 3)
                for lu, le in label_uids:
                    log(f"      uid={lu} role={le.role} text={(le.text or '')[:30]}", 3)

                best_btn = self._find_nearest_button(label_uids, target)
                if best_btn:
                    return best_btn

        candidates = []
        for uid, elem in self.parser.elements.items():
            if elem.role in ("radio", "checkbox", "switch"):
                continue
            text = (elem.text or "") + (elem.name or "")
            is_interactive = elem.role in ("button", "link", "textbox", "combobox", "menuitem")
            if target and target.lower() in text.lower() and is_interactive:
                score = 0
                if text.strip().lower() == target.strip().lower():
                    score += 10
                elif target.lower() in text.lower():
                    score += 5
                if elem.role == "button":
                    score += 3
                candidates.append((score, uid, elem))

        candidates.sort(key=lambda x: x[0], reverse=True)
        if candidates:
            _, best_uid, best_elem = candidates[0]
            log(f"    [SmartMatch-P3] 最佳文本匹配: uid={best_uid} role={best_elem.role} text={best_elem.text[:30]}", 3)
            return best_uid

        log(f"    [SmartMatch] ❌ 未找到上传按钮", 2)
        return None

    def _find_nearest_button(self, anchor_elements: List[Tuple], target_text: str) -> Optional[str]:
        """在锚点元素附近查找最近的 button"""
        anchor_uids = {uid for uid, _ in anchor_elements}
        best_match = None
        best_distance = float('inf')

        for uid, elem in self.parser.elements.items():
            if elem.role != "button":
                continue
            text = (elem.text or "").strip()
            if target_text and target_text.lower() not in text.lower():
                continue

            try:
                uid_num = int(uid.split("_")[-1]) if "_" in uid else 0
            except ValueError:
                continue

            min_anchor_dist = float('inf')
            for auid, _ in anchor_elements:
                try:
                    auid_num = int(auid.split("_")[-1]) if "_" in auid else 0
                except ValueError:
                    continue
                dist = abs(uid_num - auid_num)
                if dist < min_anchor_dist:
                    min_anchor_dist = dist

            if min_anchor_dist < best_distance:
                best_distance = min_anchor_dist
                best_match = uid

        if best_match:
            log(f"    [NearestButton] 最近button: uid={best_match} 距离anchor={best_distance}", 3)
        return best_match

    async def _execute_verify_network(self, step: Dict, step_num: int,
                                      desc: str, start_time: float) -> StepResult:
        """verify_network 动作：校验浏览器网络请求（铁律3 UI+网络双重校验）

        通过 chrome-devtools-mcp 的 list_network_requests 检查当前页面导航内的
        网络请求，匹配 YAML 断言中的 url_pattern / method / response_code。

        YAML 用法:
          - step: 33
            desc: "校验新增接口"
            action: verify_network
            assertion:
              type: network_called
              url_pattern: "/api/presale/goods"
              method: POST
              response_code: 200
        """
        action_type = "verify_network"
        elapsed = int((time.time() - start_time) * 1000)
        # 兼容 assertion 在步骤内或步骤顶层
        assertion = step.get("assertion") or {}
        url_pattern = resolve_env_vars(str(assertion.get("url_pattern") or step.get("url_pattern") or ""))
        method = resolve_env_vars(str(assertion.get("method") or step.get("method") or ""))
        code = assertion.get("response_code") or step.get("response_code") or assertion.get("status_code")

        log(f"  🌐 [verify_network] 匹配 url~'{url_pattern}' method={method or '*'}"
            f" status={code or '*'}", 2)

        import json as _json

        try:
            js_res = await self.session.call_tool("list_network_requests", {
                "resourceTypes": ["fetch", "xhr"],
            })
            raw = self._extract_result_content(js_res) or ""
            requests = []
            # 优先尝试 JSON 数组
            try:
                data = _json.loads(raw)
                if isinstance(data, list):
                    requests = data
            except _json.JSONDecodeError:
                requests = []
            # 回退: chrome-devtools-mcp 返回 Markdown 行: "reqid=N METHOD URL [STATUS]"
            if not requests:
                import re as _re
                for line in raw.splitlines():
                    m = _re.match(r"reqid=\d+\s+(\S+)\s+(\S+)\s+\[(\d+)\]", line.strip())
                    if m:
                        requests.append({
                            "method": m.group(1), "url": m.group(2),
                            "status": int(m.group(3)),
                        })
        except Exception as e:
            log(f"  🌐 [verify_network] list_network_requests 调用失败: {e}", 1)
            return StepResult(
                step_num=step_num, desc=desc, action=action_type,
                status=StepStatus.FAILED, mcp_tool="list_network_requests",
                error=f"list_network_requests error: {e}",
                output="",
                duration_ms=elapsed,
            )

        from urllib.parse import urlparse

        def _norm(path_or_pattern: str) -> str:
            """去掉常见代理前缀（/dev-api、/prod-api、/api），便于前后端路径对齐"""
            p = path_or_pattern
            for prefix in ("/dev-api", "/prod-api", "/api"):
                if p.startswith(prefix):
                    p = p[len(prefix):]
                    break
            return p

        matched = []
        for req in requests:
            if not isinstance(req, dict):
                continue
            url = req.get("url", "") or ""
            try:
                path = urlparse(url).path or url
            except Exception:
                path = url
            path_norm = _norm(path)
            pattern_norm = _norm(url_pattern)
            if url_pattern and pattern_norm not in path_norm:
                continue
            if method:
                req_method = str(req.get("method", "")).upper()
                if req_method and req_method != method.upper():
                    continue
            if code is not None:
                req_status = req.get("status")
                if req_status is None:
                    req_status = req.get("statusCode")
                if req_status is not None and int(req_status) != int(code):
                    continue
            matched.append({
                "url": url, "method": req.get("method", ""),
                "status": req.get("status", req.get("statusCode", "")),
            })

        if matched:
            detail = " | ".join(
                f"{m['method']} {m['url'][:80]} -> {m['status']}" for m in matched[:5])
            log(f"  🌐 [verify_network] ✅ 匹配到 {len(matched)} 个请求: {detail}", 1)
            return StepResult(
                step_num=step_num, desc=desc, action=action_type,
                status=StepStatus.SUCCESS, mcp_tool="list_network_requests",
                output=f"Network matched {len(matched)}: {detail}",
                duration_ms=elapsed,
            )

        available = [f"{r.get('method', '?')} {str(r.get('url', ''))[:80]}"
                     for r in requests[:8] if isinstance(r, dict)]
        log(f"  🌐 [verify_network] ❌ 未匹配到请求 (url_pattern='{url_pattern}')", 1)
        log(f"     最近请求: {available}", 3)
        return StepResult(
            step_num=step_num, desc=desc, action=action_type,
            status=StepStatus.FAILED, mcp_tool="list_network_requests",
            error=f"No network request matched url_pattern='{url_pattern}'",
            output=f"Recent requests: {available}",
            duration_ms=elapsed,
        )

    async def _execute_assert_multiple(self, step: Dict, step_num: int,
                                       desc: str, start_time: float) -> StepResult:
        action_type = "assert_multiple"
        log(f"  📸 获取页面快照用于断言验证...", 2)
        await self._take_snapshot()
        await asyncio.sleep(0.3)

        assertions = self._collect_assertions(step)
        assertion_results = []
        if not assertions:
            return StepResult(
                step_num=step_num, desc=desc, action=action_type,
                status=StepStatus.SUCCESS, mcp_tool="(assert_multiple)",
                output="No assertions defined, auto-pass",
                duration_ms=int((time.time() - start_time) * 1000),
                snapshot_path=self.last_snapshot_path or "",
            )

        log(f"\n  🔍 断言验证 ({len(assertions)} 项):", 1)
        for assertion in assertions:
            ar = self._run_assertion(assertion)
            assertion_results.append(ar)
            icon = "✅" if ar["passed"] else "❌"
            expected = ar.get("expected", "")
            log(f"    [{icon}] {assertion['type']}: 期望={expected} → "
                f"{'PASS' if ar['passed'] else 'FAIL'} | {ar['detail']}", 1)

        all_pass = all(a["passed"] for a in assertion_results)
        critical_fail = any(
            not a["passed"] and a.get("confidence") == "high"
            and a["type"] in ("text_contains", "url_contains", "element_visible", "toast_visible")
            for a in assertion_results
        )

        if critical_fail:
            status = StepStatus.FAILED_ASSERT
            log("  ⛔ 关键断言失败!", 1)
        elif not all_pass:
            # 修复 Bug F: 断言失败如实标记，不再被吞为 SUCCESS
            status = StepStatus.FAILED_ASSERT
            log("  ⚠️ 断言失败（步骤标记 FAILED_ASSERT）", 1)
        else:
            status = StepStatus.SUCCESS
            log("  ✅ 所有断言通过", 1)

        elapsed_ms = int((time.time() - start_time) * 1000)
        detail_summary = "; ".join(
            f"{a['type']}={'PASS' if a['passed'] else 'FAIL'}" for a in assertion_results
        )
        return StepResult(
            step_num=step_num, desc=desc, action=action_type,
            status=status, mcp_tool="(assert_multiple)",
            output=detail_summary, assertions=assertion_results,
            duration_ms=elapsed_ms,
            snapshot_before=self.last_snapshot_text[:500] if self.last_snapshot_text else "",
            snapshot_path=self.last_snapshot_path or "",
        )

    def _collect_assertions(self, step: Dict) -> List[Dict]:
        """收集步骤中的所有断言"""
        assertions = []
        singular = step.get("assertion")
        if singular:
            assertions.append(singular)
        plural = step.get("assertions", [])
        if plural:
            assertions.extend(plural)
        also = step.get("also_assert")
        if also:
            if isinstance(also, list):
                assertions.extend(also)
            else:
                assertions.append(also)
        return assertions

    def _run_assertion(self, assertion: Dict) -> Dict:
        """执行单个断言"""
        assert_type = assertion.get("type", "unknown")
        expected = resolve_env_vars(str(assertion.get("expected", "")))

        validator = AssertionRegistry.get(assert_type)
        
        if validator:
            try:
                result = validator(assertion, self.last_snapshot_text, self.parser, self.cache)
                return {
                    "type": assert_type,
                    "expected": expected,
                    "passed": result["passed"],
                    "detail": result["detail"],
                    "confidence": assertion.get("confidence", "medium"),
                }
            except Exception as e:
                return {
                    "type": assert_type,
                    "expected": expected,
                    "passed": False,
                    "detail": f"Validator error: {e}",
                    "confidence": assertion.get("confidence", "medium"),
                }

        passed = True
        detail = f"Unknown assertion type: {assert_type}, auto-passed"

        return {"type": assert_type, "expected": expected, "passed": passed, "detail": detail}

    @staticmethod
    def _extract_result_content(result) -> str:
        content_parts = []
        if result.content:
            for item in result.content:
                if hasattr(item, 'text'):
                    content_parts.append(item.text)
                else:
                    content_parts.append(str(item))
        return "".join(content_parts)

    @staticmethod
    def _parse_json_from_mcp_response(text: str):
        """从 MCP 响应文本中提取 JSON 对象（最大容错）

        策略:
          1. 正则提取 markdown 代码块
          2. 多轮尝试 json.loads（包括二次解码）
          3. 正则提取 key:value 作为兜底
          4. 如果包含 found/exposed 等成功标记，返回 {"found": True}
        """
        if not text or not text.strip():
            return {}
        text = text.strip()

        import re

        code_block_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
        if code_block_match:
            text = code_block_match.group(1).strip()

        text_clean = text.replace('\n', ' ').replace('\r', '')

        def _try_parse(s):
            s = s.strip()
            if not s or len(s) < 3:
                return None
            for candidate in [s]:
                try:
                    result = json.loads(candidate)
                    return result
                except (json.JSONDecodeError, ValueError):
                    pass
                try:
                    cleaned = candidate.replace('\\n', ' ').replace('\\r', '').replace('\\t', ' ')
                    result = json.loads(cleaned)
                    return result
                except (json.JSONDecodeError, ValueError):
                    pass
            return None

        def _try_double_parse(s):
            first = _try_parse(s)
            if isinstance(first, dict):
                return first
            if isinstance(first, list):
                return {"_array": first}
            if isinstance(first, str):
                second = _try_parse(first)
                if isinstance(second, dict):
                    return second
                if isinstance(second, list):
                    return {"_array": second}
            return first

        result = _try_double_parse(text_clean)
        if isinstance(result, dict):
            return result

        start = text_clean.find('{')
        end = text_clean.rfind('}')
        if start != -1 and end != -1 and end > start:
            candidate = text_clean[start:end + 1]
            result = _try_double_parse(candidate)
            if isinstance(result, dict):
                return result

        start = text_clean.find('[')
        end = text_clean.rfind(']')
        if start != -1 and end != -1 and end > start:
            candidate = text_clean[start:end + 1]
            result = _try_parse(candidate)
            if isinstance(result, list):
                return {"_array": result}

        if re.search(r'"found"\s*:\s*true', text_clean) or \
           re.search(r'"exposed"\s*:\s*true', text_clean) or \
           re.search(r'found\s*:\s*true', text_clean):
            log(f"    [MCP-Parse] 通过正则检测到成功标记", 3)
            return {"found": True, "_parse_method": "regex_fallback"}

        log(f"    [MCP-Parse] ⚠️ 无法提取JSON对象 (len={len(text_clean)}, has_found={'found' in text_clean.lower()})", 2)
        return {}

    @staticmethod
    def _check_result_has_error(content: str) -> bool:
        """
        检测MCP操作结果是否包含错误
        
        FastAI v2.0 修复版：
          - 增强错误识别能力，减少假阳性
          - 覆盖更多 MCP 实际返回的错误格式
        """
        if not content:
            return False
        
        content_lower = content.lower()
        
        # 1️⃣ 严格匹配：明确的错误类型
        strict_errors = [
            "mcp error",
            "input validation error", 
            "invalid arguments",
            "elementclickinterceptederror",
            "elementnotinteractableerror",
            "staleelement",
            "target closed",
            "detached",
            "execution failed",
            "permission denied",
            "access denied",
            "not found on page",
        ]
        
        if any(err in content_lower for err in strict_errors):
            return True
        
        # 2️⃣ 宽松匹配：常见错误关键词（MCP实际返回的格式）
        loose_error_patterns = [
            "error:",                    # "Error: Failed to interact..."
            "failed to",                 # "Failed to interact..."
            "did not become",           # "did not become interactive"
            "not interactive",           # "not interactive within"
            "timeout",                   # "within the configured timeout"
            "could not",                # "Could not find element"
            "unable to",                 # "Unable to click"
            "no such",                   # "No such element"
            "cannot find",              # "Cannot find"
            "element not found",         # "Element not found"
            "interaction failed",        # "interaction failed"
            "click intercepted",         # "Click intercepted"
            "is not clickable",          # "is not clickable"
            "is not visible",            # "is not visible"
            "does not exist",            # "does not exist"
            "unexpected error",          # "Unexpected error"
            "operation failed",          # "Operation failed"
        ]
        
        if any(pattern in content_lower for pattern in loose_error_patterns):
            return True
        
        # 3️⃣ 特殊检测：MCP工具返回的标准错误前缀
        if content_lower.startswith("error:") or content_lower.startswith("err:"):
            return True
            
        # 4️⃣ 长度异常检测：如果结果内容很长且包含可疑词汇
        suspicious_words = ["exception", "traceback", "stack trace"]
        if len(content) > 200 and any(word in content_lower for word in suspicious_words):
            return True
        
        return False


# ============================================================
# 报告生成器 v2.0
# ============================================================

def _md_to_html(md: str) -> str:
    """轻量 Markdown → HTML 转换（支持标题/表格/粗体/代码块/图片/列表，无第三方依赖）"""
    import html as _html
    lines = md.split("\n")
    out = []
    in_code = False
    code_buf = []
    in_table = False
    table_rows = []

    def flush_table():
        nonlocal in_table, table_rows
        if not table_rows:
            return
        html_rows = []
        for ri, row in enumerate(table_rows):
            cells = [c.strip() for c in row.strip().strip("|").split("|")]
            tag = "th" if ri == 0 else "td"
            # 去掉 md 加粗标记
            clean = lambda s: s.replace("**", "").replace("`", "")
            html_rows.append("<tr>" + "".join(f"<{tag}>{_html.escape(clean(c))}</{tag}>" for c in cells) + "</tr>")
        out.append("<table border='1' cellspacing='0' cellpadding='6' style='border-collapse:collapse'>" + "".join(html_rows) + "</table>")
        table_rows = []
        in_table = False

    for line in lines:
        # 代码块
        if line.strip().startswith("```"):
            if in_code:
                out.append("<pre style='background:#f6f8fa;padding:10px;border-radius:4px;overflow-x:auto'>" + _html.escape("\n".join(code_buf)) + "</pre>")
                code_buf = []
                in_code = False
            else:
                flush_table()
                in_code = True
            continue
        if in_code:
            code_buf.append(line)
            continue

        # 表格分隔行（|---|）
        if re.match(r"^\|[\s:\-|]+\|$", line.strip()):
            continue
        if line.strip().startswith("|") and line.strip().endswith("|"):
            flush_table() if in_table and False else None
            # 新表格
            if not in_table:
                in_table = True
                table_rows = []
            if "|" in line:
                table_rows.append(line)
            continue
        else:
            flush_table()

        s = line.strip()
        if not s:
            continue
        if s == "---":
            out.append("<hr>")
        elif s.startswith("### "):
            out.append(f"<h3>{_html.escape(s[4:].replace('**',''))}</h3>")
        elif s.startswith("## "):
            out.append(f"<h2>{_html.escape(s[3:].replace('**',''))}</h2>")
        elif s.startswith("# "):
            out.append(f"<h1>{_html.escape(s[2:].replace('**',''))}</h1>")
        elif s.startswith("- "):
            # 图片或列表项
            img_m = re.match(r"^- !\[(.*?)\]\((.*?)\)$", s)
            if img_m:
                out.append(f"<p><img src='{_html.escape(img_m.group(2))}' alt='{_html.escape(img_m.group(1))}' style='max-width:100%'></p>")
            else:
                out.append(f"<li>{_html.escape(s[2:].replace('**',''))}</li>")
        else:
            text = _html.escape(s)
            # 加粗转换: **xxx** → <b>xxx</b>（先转义再替换，避免脚本注入）
            text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
            out.append(f"<p>{text}</p>")

    flush_table()
    if in_code and code_buf:
        out.append("<pre>" + _html.escape("\n".join(code_buf)) + "</pre>")

    return ("<!DOCTYPE html><html><head><meta charset='utf-8'><title>测试报告</title>"
            "<style>body{font-family:'Microsoft YaHei',sans-serif;margin:24px;line-height:1.6;color:#333}"
            "table{width:100%;margin:8px 0}h1{color:#409EFF}h2{border-bottom:2px solid #eee;padding-bottom:4px}"
            "h3{margin-top:20px}li{margin:2px 0}</style></head><body>"
            + "".join(out) + "</body></html>")


class ReportGenerator:

    @staticmethod
    def generate(all_results: List[Tuple[str, TestcaseResult]], output_dir: str) -> str:
        os.makedirs(output_dir, exist_ok=True)
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        report_path = os.path.join(output_dir, f"report-{timestamp}.md")

        with open(report_path, "w", encoding="utf-8") as rf:
            rf.write("# 测试执行总报告\n\n")
            rf.write(f"**生成时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            rf.write(f"**框架版本**: AI Test Framework v2.0\n\n")
            rf.write("---\n\n")

            rf.write("## 汇总概览\n\n")
            rf.write("| # | 用例ID | 标题 | 优先级 | 步骤 | 通过 | 失败 | 跳过 | 通过率 | 状态 |\n")
            rf.write("|---|--------|------|--------|------|------|------|------|--------|------|\n")

            total_p, total_f, total_s, total_sk = 0, 0, 0, 0
            for i, (_, r) in enumerate(all_results, 1):
                total_p += r.passed_count
                total_f += r.failed_count
                total_s += r.total_steps
                total_sk += r.skipped_count
                
                badge = {"PASS": "**PASS ✅**", "PARTIAL": "**PARTIAL ⚠️**",
                         "FAIL": "**FAIL ❌**"}.get(r.overall_status, r.overall_status)
                rf.write(f"| {i} | `{r.test_id}` | {r.title} | {r.priority} | "
                        f"{r.total_steps} | {r.passed_count} | {r.failed_count} | "
                        f"{r.skipped_count} | {r.pass_rate:.1f}% | {badge} |\n\n")

                rf.write(f"### {i}. {r.title}\n\n")
                rf.write(f"- **ID**: `{r.test_id}`\n")
                rf.write(f"- **文件**: `{os.path.basename(r.yaml_file)}`\n")
                rf.write(f"- **状态**: {badge} ({r.pass_rate:.1f}%)\n")
                rf.write(f"- **时间**: {r.timestamp}\n\n")

                rf.write("**步骤明细**:\n\n")
                rf.write("| # | 描述 | 动作 | 状态 | 重试 | 耗时 |\n")
                rf.write("|---|------|------|------|------|------|\n")
                for sr in r.steps:
                    icon = {StepStatus.SUCCESS: "✅", StepStatus.FAILED: "❌",
                           StepStatus.FAILED_ASSERT: "⚠️", StepStatus.SKIPPED: "⏭️",
                           StepStatus.ERROR: "💥", StepStatus.RETRIED: "🔄"}.get(sr.status, "?")
                    retry_info = f"x{sr.retry_count}" if sr.retry_count > 0 else "-"
                    rf.write(f"| {sr.step_num} | {sr.desc} | {sr.action} | "
                            f"{icon} {sr.status.value} | {retry_info} | {sr.duration_ms}ms |\n")

                if r.screenshots:
                    rf.write("\n**截图**:\n\n")
                    for ss in r.screenshots:
                        ss_name = os.path.basename(ss)
                        dest = os.path.join(output_dir, ss_name)
                        if os.path.exists(ss) and not os.path.exists(dest):
                            try:
                                shutil.copy2(ss, dest)
                            except Exception:
                                pass
                        rf.write(f"- ![]({ss_name})\n")
                rf.write("---\n\n")

            grand_total = total_s
            grand_executed = grand_total - total_sk
            grand_rate = (total_p / grand_executed * 100) if grand_executed > 0 else 0
            overall = "ALL PASS ✅" if total_f == 0 else ("PARTIAL ⚠️" if total_p > 0 else "ALL FAIL ❌")
            
            rf.write(f"\n## 总计\n\n")
            rf.write(f"| 指标 | 值 |\n|------|-----|\n")
            rf.write(f"| 用例数 | {len(all_results)} |\n| 总步骤 | {grand_total} |\n")
            rf.write(f"| 已执行 | {grand_executed} |\n| 跳过 | {total_sk} |\n")
            rf.write(f"| 通过 | {total_p} |\n| 失败 | {total_f} |\n")
            rf.write(f"| 通过率 | {grand_rate:.1f}% |\n| 状态 | **{overall}** |\n")

        for _, r in all_results:
            safe_id = r.test_id.replace("/", "-").replace("\\", "-")
            detail_path = os.path.join(output_dir, f"{safe_id}-detail.md")
            with open(detail_path, "w", encoding="utf-8") as df:
                df.write(f"# {r.title}\n\n")
                df.write(f"- **ID**: `{r.test_id}`\n")
                df.write(f"- **状态**: **{r.overall_status}** ({r.pass_rate:.1f}%)\n")
                df.write(f"- **时间**: {r.timestamp}\n")
                df.write(f"- **配置**: ```json\n{json.dumps(r.config, ensure_ascii=False, indent=2)}\n```\n\n")
                df.write("---\n\n")
                
                for sr in r.steps:
                    icon = {StepStatus.SUCCESS: "✅", StepStatus.FAILED: "❌",
                           StepStatus.FAILED_ASSERT: "⚠️", StepStatus.SKIPPED: "⏭️",
                           StepStatus.ERROR: "💥", StepStatus.RETRIED: "🔄"}.get(sr.status, "?")
                    df.write(f"### 步骤{sr.step_num}: {sr.desc} [{icon} {sr.status.value}]\n\n")
                    df.write(f"```\n动作: {sr.action}\n工具: {sr.mcp_tool}\n")
                    df.write(f"参数: {_safe_json_dumps(sr.mcp_args, ensure_ascii=False, indent=2)}\n")
                    if sr.output:
                        out = sr.output[:600] + "..." if len(sr.output) > 600 else sr.output
                        df.write(f"结果: {out}\n")
                    if sr.error:
                        df.write(f"错误: {sr.error}\n")
                    if sr.retry_count > 0:
                        df.write(f"重试次数: {sr.retry_count}\n")
                    if sr.assertions:
                        df.write(f"断言:\n")
                        for ar in sr.assertions:
                            ai = "✅" if ar["passed"] else "❌"
                            conf = ar.get("confidence", "medium")
                            df.write(f"  {ai} [{conf}] {ar['type']}: {ar.get('expected','')} → {ar.get('detail','')}\n")
                    if sr.snapshot_before:
                        snap_preview = sr.snapshot_before[:200] + "..." if len(sr.snapshot_before) > 200 else sr.snapshot_before
                        df.write(f"执行前快照预览:\n{snap_preview}\n")
                    if sr.snapshot_path:
                        df.write(f"快照文件: `{sr.snapshot_path}`\n")
                    
                    # ===== LLM 思维链输出 =====
                    if sr.thinking_pre or sr.thinking_post:
                        df.write(f"\n#### 🧠 LLM 思维链 (置信度: {sr.llm_confidence:.0%})\n\n")
                        if sr.thinking_pre:
                            df.write(f"**执行前思考:**\n\n```\n{sr.thinking_pre}\n```\n\n")
                        if sr.thinking_post:
                            df.write(f"**执行后反思:**\n\n```\n{sr.thinking_post}\n```\n\n")
                        if sr.llm_suggestions:
                            df.write(f"**AI 建议:**\n")
                            for i, s in enumerate(sr.llm_suggestions, 1):
                                df.write(f"  {i}. {s}\n")
                            df.write("\n")
                    
                    df.write("```\n\n")

        # ===== 修复: 同时输出 HTML 报告（testcase-agent 技能规范要求 HTML）=====
        try:
            html_path = os.path.join(output_dir, f"report-{timestamp}.html")
            with open(report_path, "r", encoding="utf-8") as _rf:
                _md_text = _rf.read()
            with open(html_path, "w", encoding="utf-8") as _hf:
                _hf.write(_md_to_html(_md_text))
            log(f"📊 HTML 报告: {html_path}", 1)
        except Exception as _e:
            log(f"  ⚠️ HTML 报告生成失败: {_e}", 2)

        return report_path


# ============================================================
# 测试用例发现器
# ============================================================

def collect_yaml_files(dir_path: str) -> List[str]:
    """递归收集目录下所有 YAML 用例，按路径排序（稳定执行顺序）"""
    found = []
    for root, dirs, files in os.walk(dir_path):
        # 跳过产物/依赖目录，避免误扫
        dirs[:] = sorted(d for d in dirs
                         if d not in ("__pycache__", "node_modules", "test-result", "snapshots"))
        for f in sorted(files):
            if f.endswith((".yaml", ".yml")):
                found.append(os.path.join(root, f))
    return sorted(found)


def resolve_dir_arg(arg: str) -> Optional[str]:
    """把命令行目录参数解析成真实目录路径。

    依次尝试：绝对路径 → 相对项目根 → 相对当前工作目录。
    都命中不了返回 None（由调用方回退到历史 tc* 约定）。
    """
    if os.path.isabs(arg):
        return arg if os.path.isdir(arg) else None
    for base in (PROJECT_ROOT, os.getcwd()):
        cand = os.path.join(base, arg)
        if os.path.isdir(cand):
            return cand
    return None


def discover_testcases(root_dir: str) -> Dict[str, List[Dict]]:
    """扫描根目录下的所有 YAML 测试用例（递归，兼容历史 tc* 约定）"""
    result = {}
    if not os.path.exists(root_dir):
        return result
    for entry in sorted(os.listdir(root_dir)):
        full_path = os.path.join(root_dir, entry)
        if not os.path.isdir(full_path):
            continue
        if entry in ("__pycache__", "node_modules", "test-result"):
            continue
        yamls = collect_yaml_files(full_path)
        if yamls:
            result[entry] = [{"dir": os.path.relpath(os.path.dirname(y), PROJECT_ROOT).replace("\\", "/"),
                              "filename": os.path.basename(y), "path": y}
                             for y in yamls]
    return result


# ============================================================
# 截图落盘（跨 MCP 版本安全）
# ============================================================

async def _take_screenshot_to(session, dest_path: str, full_page: bool = False):
    """截图并确保文件**真的**落在 dest_path 上。返回 (ok: bool, detail: str)。

    为什么需要这层：chrome-devtools-mcp 用「workspace roots」白名单校验 filePath，
    而 roots() 永远至少包含 `os.tmpdir()`。如果客户端（本引擎）没有协商 MCP roots
    能力，文件写入就被**限制在 OS 临时目录内**，写到项目 test-result/ 会直接报：
        Access denied: path ... is not within any of the configured workspace roots.
    （本地构建里连 --allow-unrestricted-paths 的解析都没有，所以那个开关靠不住。）

    老引擎拿到这个错误看都不看就打印 "✅ 截图: xxx.png" —— 实测全盘都找不到那个文件。
    这里改为：先写目标路径 → 被拒就写临时目录再复制过来。
    与 MCP 版本无关，也不需要动 MCP 启动参数。
    """
    dest_path = os.path.abspath(dest_path)
    try:
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    except Exception:
        pass

    async def _shot(path: str) -> str:
        res = await session.call_tool("take_screenshot", {
            "fullPage": bool(full_page), "filePath": path})
        text = ""
        if res is not None and getattr(res, "content", None):
            for item in (res.content or []):
                if hasattr(item, "text"):
                    text += item.text
        return text or ""

    text = await _shot(dest_path)
    if os.path.exists(dest_path):
        return True, f"{os.path.getsize(dest_path) / 1024.0:.0f} KB"

    denied = ("Access denied" in text) or ("workspace roots" in text)
    if denied:
        tmp_dir = os.path.join(tempfile.gettempdir(), "mcp-screenshots")
        try:
            os.makedirs(tmp_dir, exist_ok=True)
        except Exception as e:
            return False, f"MCP 拒绝目标路径，且临时目录创建失败: {e}"
        tmp_path = os.path.join(tmp_dir, os.path.basename(dest_path))
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
        text2 = await _shot(tmp_path)
        if os.path.exists(tmp_path):
            try:
                shutil.copy2(tmp_path, dest_path)
            except Exception as e:
                return False, f"临时目录截图成功但复制失败: {e}（临时文件: {tmp_path}）"
            return True, (f"{os.path.getsize(dest_path) / 1024.0:.0f} KB"
                          f"（经临时目录中转: {tmp_dir}）")
        return False, f"MCP 白名单拒绝 + 临时目录回退也失败: {text2.strip()[:150]}"

    return False, (f"文件未落盘，MCP 返回: {text.strip()[:180]}"
                   if text.strip() else "文件未落盘，且 MCP 未返回任何信息")


# ============================================================
# 主执行引擎 v2.0
# ============================================================

async def run_single_testcase(yaml_path: str, result_dir: str = None,
                             global_config: Dict[str, Any] = None) -> TestcaseResult:
    """执行单个 YAML 测试用例"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    parser = SnapshotParser()
    cache = {}
    config = {**DEFAULT_CONFIG, **(global_config or {})}

    log(f"📂 加载: {yaml_path}", 1)
    with open(yaml_path, "r", encoding="utf-8") as f:
        testcase = yaml.safe_load(f)

    base_dir = str(Path(yaml_path).parent)
    testcase = _resolve_includes(testcase, base_dir)
    # repeat 展开放在 _include 合并之后：先合并共享步骤，再整体复制循环体
    testcase = _expand_repeats(testcase)

    test_id = testcase.get("test_id", "UNKNOWN")
    title = testcase.get("title", "未命名")
    priority = testcase.get("priority", "P3")

    tc_config = testcase.get("config", {})
    config.update(tc_config)

    env_used = {}
    context_check = testcase.get("context_check", {})
    if context_check:
        creds = context_check.get("credentials", {})
        for var_name, var_val in creds.items():
            resolved = resolve_env_vars(var_val)
            original = os.environ.get(var_name)
            os.environ[var_name] = resolved
            env_used[var_name] = {"set_to": resolved, "was": original}
            log(f"  凭据: {var_name}={'已设置' if resolved else '未设置'}", 2)

    result = TestcaseResult(
        test_id=test_id, title=title, priority=priority,
        yaml_file=yaml_path, timestamp=timestamp,
        config=config, env_used=env_used,
    )

    steps = testcase.get("steps", [])
    on_fail_strategy = testcase.get("on_fail", "continue")
    if on_fail_strategy not in ("stop", "continue", "retry"):
        on_fail_strategy = "continue"

    log(f"📋 {len(steps)} 个步骤 | 失败策略: {on_fail_strategy}", 1)

    think_enabled = config.get("llm_think_enabled", False)
    think_engine = None
    
    if think_enabled and LLM_AVAILABLE:
        llm_cfg = {
            **LLM_CONFIG,
            "enabled": True,
            "think_mode": "deep" if config.get("llm_think_deep") else "auto",
        }
        think_engine = ThinkChainEngine(llm_cfg)
        if think_engine.enabled:
            log(f"  🧠 思维链已启用 (模式: {llm_cfg['think_mode']})", 1)
        else:
            log(f"  ⚠️ 思维链初始化失败，将使用规则模式", 1)
            think_engine = None
    else:
        log(f"  ⚡ 思维链已禁用 (快速模式)", 2)

    async with stdio_client(SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_resp = await session.list_tools()
            log(f"🔌 MCP 已连接 ({len(tools_resp.tools)} 工具)", 1)

            executor = ActionExecutor(session, parser, cache, config, think_engine, result_dir=result_dir)

            # ============================================================
            # FastAI v2.0: 智能登录管理（步骤1导航完成后才检测）
            # ============================================================
            login_status = None
            smart_skip_enabled = testcase.get("smart_skip", True)
            _login_checked = False

            for step_idx, step in enumerate(steps):
                step_num = step.get("step", step_idx + 1)

                # ===== 步骤1（navigate）始终执行，完成后检测登录状态 =====
                if step_idx == 0:
                    log(f"\n{'─'*50}", 1)
                    log(f"[{step_idx+1}/{len(steps)}] 开始执行步骤 {step_num}", 1)
                    sr = await executor.execute(step, step_num, tc_config)
                    result.steps.append(sr)

                    # 步骤1（navigate）完成后，等待SPA渲染再检测登录状态
                    if context_check and smart_skip_enabled and not _login_checked:
                        _login_checked = True
                        # SPA页面需要等待JavaScript渲染完成（否则快照为空）
                        render_wait = config.get("spa_render_wait", 3.0)
                        log(f"  ⏳ 等待SPA渲染 ({render_wait}s)...", 2)
                        await asyncio.sleep(render_wait)

                        try:
                            from login_manager import LoginManager
                            manager = LoginManager(snapshot_dir=executor.snapshot_dir)

                            required_user = context_check.get("credentials", {}).get("username", "${TEST_USER}")
                            login_status = await manager.check_and_ensure_login(
                                session=session,
                                parser=parser,
                                config=config,
                                required_user=required_user,
                                context_check=context_check
                            )

                            # ===== 补齐「自动登录」 =====
                            # LoginManager 只能**检测**登录态；action=="login" 表示「未登录，
                            # 应由调用方完成登录」，但引擎此前在这个分支里什么都不做。
                            # 后果：所有把登录态寄托在「上一条用例登录过」的用例
                            # （pc-002~pc-00x / h5-002 / h5-003）在 --isolated 隔离模式
                            # （每条用例一个全新临时用户目录）下必然跑在登录页上，
                            # 表现就是「步骤大量失败，但断言仍显示 PASS」。
                            #
                            # 保护：用例自身已经写了「填账号/密码 + 点登录」的动作时
                            # （pc-001 / h5-001），维持原行为，不做任何干预。
                            if (login_status and login_status.action == "login"
                                    and not _case_self_handles_login(steps)):
                                log(f"\n🔐 当前未登录，按 context_check 自动登录...", 1)
                                _auto_ok = await manager.perform_login(
                                    session=session,
                                    context_check=context_check,
                                    return_url=resolve_env_vars(str(steps[0].get("url", "") or "")),
                                )
                                if _auto_ok:
                                    login_status.action = "skip"
                                    login_status.reason = "已按 context_check 自动登录"
                                    login_status.steps_to_skip = []
                                else:
                                    login_status.reason = "自动登录失败，后续步骤可能全部落在登录页"

                            if login_status:
                                log(f"\n{'='*55}", 1)
                                log(f"🔐 登录状态检测结果", 1)
                                log(f"   操作: {login_status.action.upper()}", 2)
                                log(f"   当前用户: {login_status.current_user or '未登录'}", 2)
                                log(f"   原因: {login_status.reason}", 2)

                                if login_status.action == "skip":
                                    skip_nums = [steps[i].get("step", i+1) for i in login_status.steps_to_skip]
                                    log(f"   跳过步骤: {skip_nums}", 2)

                                if login_status.warning:
                                    log(f"   ⚠️ 注意: 此结果可能不准确，请人工确认", 2)

                                log(f"{'='*55}\n", 1)

                        except Exception as e:
                            log(f"⚠️ 登录管理器初始化失败: {e}，将执行完整流程", 2)
                            login_status = None

                    if sr.status in (StepStatus.FAILED, StepStatus.ERROR, StepStatus.FAILED_ASSERT):
                        if on_fail_strategy == "stop":
                            log(f"\n⛔ 步骤{step_num}失败，终止执行 (策略: stop)", 1)
                            break
                        else:
                            log(f"\n⚠️ 步骤{step_num}失败，继续执行 (策略: {on_fail_strategy})", 1)
                    continue

                # ===== 步骤2+：智能跳过判断 =====
                should_skip = (
                    login_status and
                    login_status.action == "skip" and
                    step_idx in login_status.steps_to_skip
                )

                if should_skip:
                    skipped_result = StepResult(
                        step_num=step_num,
                        desc=step.get("desc", "已跳过"),
                        action=step.get("action", "skipped"),
                        status=StepStatus.SKIPPED,
                        mcp_tool="smart_login_manager",
                        output=f"智能跳过: {login_status.reason}",
                        duration_ms=0,
                    )
                    result.steps.append(skipped_result)
                    continue
                
                log(f"\n{'─'*50}", 1)
                log(f"[{step_idx+1}/{len(steps)}] 开始执行步骤 {step_num}", 1)

                prev_action = steps[step_idx - 1].get("action", "") if step_idx > 0 else ""
                sr = await executor.execute(step, step_num, tc_config)
                result.steps.append(sr)

                if sr.status in (StepStatus.FAILED, StepStatus.ERROR, StepStatus.FAILED_ASSERT):
                    is_critical = (
                        step.get("assertion", {}).get("critical", False) or
                        step.get("critical", False)
                    )
                    if is_critical:
                        log(f"\n🛑 步骤{step_num}关键断言失败，立即终止执行", 1)
                        break
                    elif on_fail_strategy == "stop":
                        log(f"\n⛔ 步骤{step_num}失败，终止执行 (策略: stop)", 1)
                        break
                    elif on_fail_strategy == "retry":
                        log(f"\n⚠️ 步骤{step_num}失败，但继续执行 (策略: continue)", 1)
                    else:
                        log(f"\n⚠️ 步骤{step_num}失败，继续执行 (策略: {on_fail_strategy})", 1)

                # 等待当前步骤的页面渲染完成，再进入下一步
                if step_idx < len(steps) - 1:
                    current_action = step.get("action", "")
                    try:
                        await executor._wait_for_render_complete(current_action, sr)
                    except Exception as e:
                        log(f"  ⚠️ 渲染等待异常（继续）: {e}", 3)

            teardown = testcase.get("teardown", [])
            if teardown:
                log(f"\n🧹 后置清理 ({len(teardown)} 项)", 1)
                for td in teardown:
                    td_action = td.get("action", "")
                    if td_action == "screenshot":
                        name = td.get("name", f"result-{timestamp}.png").replace(
                            "{timestamp}", time.strftime("%Y%m%d-%H%M%S"))
                        if result_dir:
                            save_name = f"{test_id}-{name}"
                            save_path = os.path.join(result_dir, save_name)
                        else:
                            save_path = name
                        # MCP 的 filePath 允许绝对路径或相对 CWD 的路径。
                        # 传绝对路径可以避免"文件被写到 MCP 进程的 CWD、而用例
                        # 在结果目录里找不到"这类定位困难。
                        save_path = os.path.abspath(save_path)
                        try:
                            ok, detail = await _take_screenshot_to(
                                session, save_path, td.get("fullPage", False))
                            if ok:
                                result.screenshots.append(save_path)
                                log(f"  ✅ 截图: {save_name} ({detail})", 1)
                            else:
                                log(f"  ⚠️ 截图失败: {detail}", 1)
                        except Exception as e:
                            log(f"  ⚠️ 截图异常: {e}", 1)

                    elif td_action in ("close_extra_pages", "close_tabs", "cleanup_tabs"):
                        # 清理循环用例里因 new_page 重试而漏下的孤儿标签页。
                        # 原先 teardown 只认 screenshot，写别的 action 会被**静默忽略**，
                        # 用例作者以为清理跑过了，其实什么都没发生。
                        try:
                            closed = await executor.close_extra_pages(
                                td.get("keep", "first"))
                            if closed:
                                log(f"  🧹 关闭多余标签页: {closed} 个", 1)
                            else:
                                log(f"  ✅ 无多余标签页（仅剩 1 个）", 1)
                        except Exception as e:
                            log(f"  ⚠️ 清理标签页失败: {e}", 1)

                    elif td_action == "log":
                        # 修复：teardown 的 log 此前是**静默空操作**（只有 screenshot 有分支），
                        # 用例里写的收尾日志一条都不会出现。
                        msg = str(td.get("message", ""))
                        if "{current_url}" in msg:
                            try:
                                pages_now = await executor._list_pages()
                                cur = next((u for _p, u, s in pages_now if s),
                                           pages_now[0][1] if pages_now else "")
                            except Exception:
                                cur = ""
                            msg = msg.replace("{current_url}", cur or "?")
                        log(f"  📝 {msg}", 1)

                    else:
                        log(f"  ⚠️ 未知 teardown action: {td_action!r}（已忽略）", 1)

    for var_name, info in env_used.items():
        if info["was"] is not None:
            os.environ[var_name] = info["was"]
        else:
            os.environ.pop(var_name, None)

    return result


async def run_all(targets: List[Dict], env_overrides: Dict[str, str] = None,
                 global_config: Dict[str, Any] = None) -> List[TestcaseResult]:
    """批量执行多个测试用例"""
    if env_overrides:
        for k, v in env_overrides.items():
            os.environ[k] = v

    results = []
    run_ts = time.strftime("%Y%m%d-%H%M%S")

    # 结果目录跟随用例所在项目：从 YAML 路径向上找含 testcases 的目录作为项目根
    # 例: ruoyi-project/testcases/frontend/xx.yaml → ruoyi-project/test-result/
    # 例: testcases/tc2-zccz/xx.yaml             → 框架根 test-result/
    result_base = RESULT_BASE_DIR
    if targets:
        yaml_path = targets[0].get("path", "")
        if yaml_path:
            probe = os.path.dirname(os.path.abspath(yaml_path))
            while True:
                if os.path.basename(probe) == "testcases" or os.path.isdir(os.path.join(probe, "testcases")):
                    result_base = os.path.join(os.path.dirname(probe), "test-result")
                    break
                parent = os.path.dirname(probe)
                if parent == probe:
                    break
                probe = parent
    this_result_dir = os.path.join(result_base, f"run-{run_ts}")
    os.makedirs(this_result_dir, exist_ok=True)

    log(f"\n{'#'*60}", 1)
    log(f"# AI Test Framework v2.0", 1)
    log(f"# 开始执行 {len(targets)} 个用例", 1)
    log(f"# 结果 → {this_result_dir}/", 1)
    log(f"# 已注册 Actions: {len(ActionRegistry.list_actions())}", 1)
    log(f"# 已注册 Assertions: {len(AssertionRegistry.list_assertions())}", 1)
    log(f"{'#'*60}\n", 1)

    for idx, tc_info in enumerate(targets, 1):
        log(f"\n[{idx}/{len(targets)}] ===== {tc_info['filename']} =====\n", 1)

        tc_env = _load_testcase_env(tc_info["path"])

        try:
            r = await run_single_testcase(tc_info["path"], this_result_dir, global_config)
            results.append(r)
        except Exception as e:
            log(f"[FATAL] 执行异常: {e}\n", 1)
            traceback.print_exc()
            results.append(TestcaseResult(
                test_id="ERROR", title=tc_info["filename"], priority="?",
                yaml_file=tc_info["path"], timestamp=time.strftime('%Y-%m-%d %H:%M:%S'),
                steps=[StepResult(0, "初始化失败", "error", StepStatus.ERROR,
                                error=str(e), duration_ms=0)],
            ))
        finally:
            for key, old_val in tc_env.items():
                if old_val is not None:
                    os.environ[key] = old_val
                else:
                    os.environ.pop(key, None)

    elapsed = time.time() - (time.mktime(time.strptime(run_ts, "%Y%m%d-%H%M%S")))

    if results:
        log(f"\n{'='*60}", 1)
        log(f"# 完成，耗时 {elapsed:.0f}s", 1)
        log(f"{'='*60}\n", 1)

        report_path = ReportGenerator.generate(
            [(r.yaml_file, r) for r in results], this_result_dir)
        log(f"📊 报告: {report_path}", 1)
        log(f"📁 目录: {this_result_dir}/\n", 1)

        tp = sum(r.passed_count for r in results)
        tf = sum(r.failed_count for r in results)
        ts = sum(r.total_steps for r in results)
        tsk = sum(r.skipped_count for r in results)
        te = ts - tsk
        rate = (tp / te * 100) if te > 0 else 0
        status = "ALL PASS ✅" if tf == 0 else ("PARTIAL ⚠️" if tp > 0 else "ALL FAIL ❌")
        log(f"  用例: {len(results)} | 总步骤: {ts} | 已执行: {te} | 跳过: {tsk}")
        log(f"  通过: {tp} | 失败: {tf} | 通过率: {rate:.0f}% | 状态: {status}")

    return results


# ============================================================
# CLI 入口
# ============================================================

def print_usage():
    print("=" * 70)
    print("  AI Test Framework v2.1 - 通用 AI 测试框架 (含录制模式)")
    print("=" * 70)
    print()
    print("用法:")
    print(f"  python testcase-ai.py                          列出用例")
    print(f"  python testcase-ai.py --all                     全部运行（递归 testcases/ 下所有 YAML）")
    print(f"  python testcase-ai.py <目录>                     运行目录（递归，支持多级嵌套/绝对路径）")
    print(f"  python testcase-ai.py <yaml路径>                 运行单个文件")
    print(f"  python testcase-ai.py --continue                 失败后继续执行")
    print()
    print("目录参数示例:")
    print(f"  python testcase-ai.py testcases/ProjA/testcases/frontend/pc")
    print(f"  python testcase-ai.py D:/path/to/testcases/smoke")
    print()
    print("🎬 录制模式 (交互式操作录制):")
    print(f"  python testcase-ai.py --record                   录制到 testcases/recorded/")
    print(f"  python testcase-ai.py --record <路径>             录制到指定路径")
    print()
    print("思维链选项:")
    print(f"  python testcase-ai.py --think <yaml>              启用 LLM 思维链")
    print(f"  python testcase-ai.py --think-deep <yaml>         深度思维模式")
    print()
    print("LLM 配置 (环境变量):")
    print(f"  LLM_BASE_URL     API 地址 (默认: http://10.0.11.6:8005/v1)")
    print(f"  LLM_API_KEY      API 密钥")
    print(f"  LLM_MODEL        模型名称 (默认: gemma-4-26B-A4B-it)")
    print()
    print("测试环境变量:")
    print(f"  TEST_USER       用户名")
    print(f"  TEST_PASS       密码")
    print(f"  TEST_PROJECT_NAME  项目名称")
    print(f"  TEST_AMOUNT       金额")
    print()
    think_status = "✅ 可用" if LLM_AVAILABLE else "❌ 未安装 openai"
    print(f"框架能力:")
    print(f"  Actions ({len(ActionRegistry.list_actions())}): {', '.join(ActionRegistry.list_actions()[:10])}...")
    print(f"  Assertions ({len(AssertionRegistry.list_assertions())}): {', '.join(AssertionRegistry.list_assertions()[:10])}...")
    print(f"  LLM 思维链: {think_status}")
    print()

    dirs = discover_testcases(TESTCASES_ROOT)
    if not dirs:
        print(f"[INFO] {TESTCASES_ROOT} 中无 tc-* 目录")
        return
    print("可用测试用例:")
    for dn, files in dirs.items():
        print(f"\n  📁 {dn}/")
        for fi in files:
            print(f"     └─ {fi['filename']}")


# ============================================================
# Recorder Mode - delegated to tests/recorder.py (SRP extraction)
# ============================================================


if __name__ == "__main__":
    register_builtin_actions()
    register_builtin_assertions()

    args = sys.argv[1:]

    if not args:
        print_usage()
        sys.exit(0)

    # ===== 录制模式（优先于其他模式）=====
    if "--record" in args:
        args.remove("--record")
        output = args[0] if args else "testcases/recorded/testcase.yaml"
        if not output.endswith((".yaml", ".yml")):
            output = os.path.join(output, "testcase.yaml") if not output.endswith(".yaml") else output
        import importlib.util
        _spec = importlib.util.spec_from_file_location("recorder", os.path.join(os.path.dirname(__file__), "recorder.py"))
        _recorder = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_recorder)
        asyncio.run(_recorder.run_record_mode(output))
        sys.exit(0)

    targets = []
    global_config = {}

    # ===== 思维链参数解析 =====
    if "--think" in args:
        global_config["llm_think_enabled"] = True
        global_config["llm_think_deep"] = False
        args.remove("--think")
        log("🧠 LLM 思维链已启用 (标准模式)", 1)
    
    if "--think-deep" in args:
        global_config["llm_think_enabled"] = True
        global_config["llm_think_deep"] = True
        args.remove("--think-deep")
        log("🧠 LLM 思维链已启用 (深度模式)", 1)

    if "--all" in args or "-a" in args:
        all_files = collect_yaml_files(TESTCASES_ROOT)
        if not all_files:
            print(f"[ERROR] 未找到测试用例")
            sys.exit(1)
        for y in all_files:
            targets.append({
                "dir": os.path.relpath(os.path.dirname(y), PROJECT_ROOT).replace("\\", "/"),
                "filename": os.path.basename(y), "path": y})

    elif args[0].endswith((".yaml", ".yml")):
        p = args[0] if os.path.isabs(args[0]) else os.path.join(PROJECT_ROOT, args[0])
        if not os.path.exists(p):
            print(f"[ERROR] 文件不存在: {p}")
            sys.exit(1)
        targets = [{"dir": "", "filename": os.path.basename(p), "path": p}]

    else:
        # ① 优先按「真实存在的目录」解析：绝对路径 / 相对项目根 / 相对当前目录，递归收集 YAML
        dp = resolve_dir_arg(args[0])
        if dp is not None:
            yfs = collect_yaml_files(dp)
            if not yfs:
                print(f"[ERROR] 目录中无YAML: {dp}")
                sys.exit(1)
            rel = os.path.relpath(dp, PROJECT_ROOT).replace("\\", "/")
            if rel.startswith(".."):
                rel = dp
            targets = [{"dir": rel, "filename": os.path.basename(y), "path": y} for y in yfs]

        # ② 回退：历史约定 testcases/tc<name>（仅扫该目录顶层 YAML）
        else:
            dn = args[0]
            if not dn.startswith("tc"):
                dn = f"tc{dn}" if not dn.startswith("tc-") else dn
            dp2 = os.path.join(TESTCASES_ROOT, dn)
            if not os.path.exists(dp2):
                print(f"[ERROR] 目录不存在: {args[0]}")
                print(f"可用: {list(discover_testcases(TESTCASES_ROOT).keys())}")
                sys.exit(1)
            yfs = [os.path.join(dp2, f) for f in os.listdir(dp2)
                   if f.endswith((".yaml", ".yml"))]
            if not yfs:
                print(f"[ERROR] 目录中无YAML: {dp2}")
                sys.exit(1)
            targets = [{"dir": dn, "filename": os.path.basename(y), "path": y}
                       for y in sorted(yfs)]

    if "--continue" in args:
        global_config["continue_on_error"] = True
    if "--stop-on-error" in args:
        global_config["continue_on_error"] = False

    # 加载全局 .env 环境变量配置文件（各用例的 .env 会在执行时自动加载）
    _load_env_from_file()

    env = {}
    asyncio.run(run_all(targets, env, global_config))
