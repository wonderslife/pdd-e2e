# PDD 测试系统（独立项目）

基于 `testcase-ai.py` 的 E2E 自动化测试系统，从 pdd-skills-v3 框架中独立拆分。
通过 Chrome DevTools MCP 驱动真实浏览器，执行 YAML 测试用例，生成 HTML/Markdown 报告。

## 目录结构

```
pdd-test-system/
├── tests/                     # 测试引擎（Python 包）
│   ├── testcase-ai.py         # 主入口（CLI）
│   ├── run_testcase.py        # 备用入口
│   ├── login_manager.py       # 登录状态智能检测
│   ├── recorder.py            # 操作录制
│   ├── framework/             # 核心模块（快照解析/定位/执行/断言）
│   └── .env.test              # 全局环境配置（凭据/LLM）
├── testcases/                 # 测试用例
│   ├── frontend/              # 前端 E2E 用例（PRESALE-*）
│   ├── api/                   # API 测试脚本
│   ├── examples/              # 示例用例
│   └── scripts/               # 批量运行脚本
├── run-test.cmd               # Windows 启动器（一键运行）
└── requirements.txt           # Python 依赖
```

## 环境要求

| 项 | 说明 |
|----|------|
| Python | 3.13+（venv：`C:\Users\name\.workbuddy\binaries\python\envs\pdd-test`） |
| Chrome | 已安装（`C:\Users\name\AppData\Local\Google\Chrome\Application\chrome.exe`） |
| chrome-devtools-mcp | 本地构建版 `D:\APPPROJECTS\chrome-devtools-mcp-main\...\build\src\bin\chrome-devtools-mcp.js`（引擎自动启动） |
| 被测系统 | http://localhost（RuoYi-Vue-Plus v6 前后端已启动） |

依赖安装（如用全新环境）：
```bash
python -m venv .venv
.venv\Scripts\pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
```

## 快速开始

```powershell
# 在项目根目录
.\run-test testcases\frontend\PRESALE-001-goods-create.yaml
```

或用完整命令：
```powershell
$env:CHROME_PATH = "C:\Users\name\AppData\Local\Google\Chrome\Application\chrome.exe"
"C:\Users\name\.workbuddy\binaries\python\envs\pdd-test\Scripts\python.exe" tests\testcase-ai.py testcases\frontend\PRESALE-001-goods-create.yaml
```

## 配置

### `tests/.env.test`（全局配置）

```ini
# 被测系统
BASE_URL=http://localhost
TEST_USER=admin
TEST_PASS=admin123
TEST_DISPLAY_NAME=admin

# LLM（DeepSeek，用于智能定位/思维链）
LLM_BASE_URL=https://api.deepseek.com
LLM_API_KEY=sk-xxx
LLM_MODEL=deepseek-v4-flash
```

### 用例级 .env

每个用例可带同名 `.env` 文件（如 `PRESALE-001-goods-create.env`），优先级高于全局配置。

## 用例编写规范（testcase-modeler 铁律）

1. 结构完整：`test_id/title/priority/tags/author/context_check/steps/teardown`
2. 登录步骤：`context_check` 检测登录态，未登录自动走 steps 里的登录步骤
3. 语义化定位：target 用页面可见文本（`商品标题`/`确 定`），禁 CSS/XPath
4. 敏感信息：一律 `${ENV_VAR}`，禁止明文密码
5. 特殊组件动作：`el_date`（日期）、`el_upload`（上传）、`select_option`（下拉）
6. 关键步骤断言：提交后 `toast_visible` + `verify_network` 双校验

## 测试报告

结果输出到 `test-result/run-{时间戳}/`（跟随用例所在目录）：
```
report-{ts}.html        # 浏览器直接打开
report-{ts}.md          # Markdown 汇总
{test_id}-detail.md     # 每步详细日志
snapshots/*.txt         # 每步页面快照
```

## 已修复的引擎问题（详见 docs/testcase-ai-fixes-summary-20260825.md）

- 15 个 bug：假通过（wait_for 空文本/断言被吞/toast 竞态）、定位错乱（uid 缓存/危险 fallback）、交互（隐藏 input/上传 Escape 误关弹窗）、时序（SPA 首载/加载遮罩）
- 4 项升级：verify_network 真实校验、HTML 报告、结果目录跟随项目、sys.path 修复

## 关联项目

- 被测后端: `D:\APPPROJECTS\RuoYi-Vue-Plus-v6.0.0`
- 被测前端: `D:\APPPROJECTS\plus-ui-v6.0.0-Vue`
- 原始框架: `D:\APPPROJECTS\pdd-skills-v3-main\pdd-skills-v3-main`（本系统已独立，不再依赖）
