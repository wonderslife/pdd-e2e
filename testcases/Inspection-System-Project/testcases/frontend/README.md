# 机房巡检系统 · E2E 测试用例集

本目录存放机房巡检系统的端到端（E2E）测试用例，YAML 格式，由 `tests/testcase-ai.py` 引擎驱动，通过 Chrome DevTools MCP 在真实浏览器中回放。

覆盖范围：**PC 管理端 11 条 + H5 扫码端 3 条 = 14 条**，每条 YAML 配套一个同名 `.env`（测试数据全部走环境变量，不硬编码）。

---

## 目录结构

```
testcases/
└── Inspection-System-Project/
    ├── testcases/
    │   ├── frontend/                  # 本套用例（PC + H5）
    │   │   ├── pc/                    # PC 管理端（plus-ui v6），11 条
    │   │   │   ├── pc-001-login.yaml / .env
    │   │   │   ├── pc-002-room-crud.yaml / .env
    │   │   │   ├── pc-003-area-crud.yaml / .env
    │   │   │   ├── pc-004-template-detail.yaml / .env
    │   │   │   ├── pc-005-point-crud.yaml / .env
    │   │   │   ├── pc-006-point-qrcode.yaml / .env
    │   │   │   ├── pc-007-point-import.yaml / .env
    │   │   │   ├── pc-008-record-query-remark.yaml / .env
    │   │   │   ├── pc-009-record-supplement.yaml / .env
    │   │   │   ├── pc-010-abnormal-process.yaml / .env
    │   │   │   └── pc-011-stats.yaml / .env
    │   │   ├── h5/                    # H5 扫码端（RuoYi-App-Plus），3 条
    │   │   │   ├── h5-001-scan-normal.yaml / .env
    │   │   │   ├── h5-002-abnormal-submit.yaml / .env
    │   │   │   └── h5-003-duplicate-reject.yaml / .env
    │   │   ├── data/                  # 导入/上传用样例文件（可选，需自备）
    │   │   └── README.md              # 本文件
    │   ├── examples/                  # 引擎自带样例（login-flow 等）
    │   └── scripts/                   # 校验与批量运行脚本
    │       ├── validate-cases.py
    │       └── run-inspect-tests.ps1
    └── test-result/                   # 运行报告（自动生成，run-{时间戳}/）
```

> 目录约定：`testcases/<被测项目名>/testcases/...`，报告落在 `<被测项目名>/test-result/`。
> 引擎会从用例路径向上自动定位这两层，无需手动指定。

---

## 用例清单

### PC 管理端

| 用例 ID | 标题 | 优先级 | 核心断言 |
|---|---|---|---|
| INSP-PC-001 | PC 登录并加载机房巡检菜单 | P0 | 登录接口 200；7 个二级菜单全部可见 |
| INSP-PC-002 | 机房管理：增/查/改/删/导出 | P0 | 必填校验拦截；POST/PUT/DELETE 均 200 |
| INSP-PC-003 | 区域管理：新增（机房/父区域下拉） | P1 | 父区域下拉有数据且含「顶级」；列表关联名回填 |
| INSP-PC-004 | 巡检项模板：模板 + 明主子表 | P0 | 明细数 > 0；修改时明细回显 |
| INSP-PC-005 | 点位管理：从模板导入巡检项 | P0 | 不再提示「没有巡检项明细」；关联列有值 |
| INSP-PC-006 | 点位二维码：查看/下载/批量导出 | P0 | img 为 blob 且有 naturalWidth（非裂图） |
| INSP-PC-007 | 点位批量导入（Excel） | P1 | 下载模板 → 校验 → 确认导入，部分成功 |
| INSP-PC-008 | 记录查询/详情/追加备注/导出 | P0 | 关联列回填；空备注被拦截 |
| INSP-PC-009 | 巡检逾期补录 | P1 | 来源标记为「PC补录」 |
| INSP-PC-010 | 异常处理闭环 | P0 | 空处理说明被拦截；状态流转为「已处理」 |
| INSP-PC-011 | 统计报表：粒度/机房/排名 | P1 | 切粒度触发重查；排名表列完整 |

### H5 扫码端

| 用例 ID | 标题 | 优先级 | 核心断言 |
|---|---|---|---|
| INSP-H5-001 | 扫码巡检（全正常）闭环 | P0 | resolve → 逐项正常 → 提交成功 → 我的记录可见 |
| INSP-H5-002 | 异常项校验 + 进入异常池 | P0 | 「说明必填」「照片必传」双拦截；PC 异常池可见 |
| INSP-H5-003 | 同周期重复巡检拦截 | P1 | 提示「本周期已巡检」；不进入执行页 |

---

## 推荐执行顺序（含数据依赖）

```
①  pc-001-login              （登录冒烟，无依赖）
②  pc-002-room-crud          （产出：测试机房）        ← 串行执行请止于「导出」，不要删机房
③  pc-003-area-crud          （产出：顶级/子区域，依赖 ②）
④  pc-004-template-detail    （产出：模板 + 明细，无依赖）★模板明细数必须 > 0
⑤  pc-005-point-crud         （产出：点位 01 + 巡检项，依赖 ②③④）★模板导入回归点
⑥  pc-006-point-qrcode       （依赖 ⑤）★blob 取值回归点
⑦  pc-007-point-import       （可选，需样例 Excel）
⑧  h5-001-scan-normal        （产出：巡检记录，依赖 ⑤）
⑨  h5-003-duplicate-reject   （依赖 ⑧：必须已有本周期记录）
⑩  h5-002-abnormal-submit    （产出：异常项，需另一个点位 02）
⑪  pc-008-record-query-remark（依赖 ⑧）
⑫  pc-009-record-supplement  （依赖 ⑤）
⑬  pc-010-abnormal-process   （依赖 ⑩）★异常处理回归点
⑭  pc-011-stats              （依赖 ⑧⑩，数据越多越有意义）
```

**最小回归集（每次改动后建议跑）**：`pc-001 → pc-004 → pc-005 → pc-006 → h5-001 → pc-010`
（正好覆盖本迭代修复的 4 处回归：模板明细、二维码 blob、关联字段回填、异常处理）

---

## 前置条件

| 项 | 要求 |
|---|---|
| 后端 | RuoYi-Vue-Plus v6 已启动在 `localhost:8080`，且已执行 `insp_schema.sql` / `insp_dict.sql` / `insp_menu.sql` |
| PC 前端 | 已启动或构建，默认 `http://localhost:80`（`VITE_APP_PORT=80`，代理 `/dev-api → localhost:8080`） |
| H5 前端 | 已启动，默认 `http://localhost:3002`（见 `RuoYi-App-Plus/env/.env`） |
| **验证码** | 建议在「系统管理 > 参数设置」将 `sys.account.captchaEnabled` 设为 `false`，否则用例会被登录页验证码卡住 |
| 账号权限 | 用例使用超管账号（`role_key=superadmin`），已具备 `inspect:*:*` 全部权限 |
| 浏览器 | Chrome + Chrome DevTools MCP；H5 用例建议切移动视图 `390x844` |

---

## 测试数据准备

1. **样例 Excel（pc-007 用）**：先在「点位管理 > 批量导入」里点「下载模板」，按模板表头填 2 行——1 行合法、1 行故意留空点位编码，另存为
   `testcases/inspect/data/point-import-sample.xlsx`。
2. **样例照片（h5-002 用）**：任意 JPG 放到 `testcases/inspect/data/site-photo.jpg`，用于异常项现场照片上传。
3. **点位与周期**：H5 用例会锁定点位本周期状态。重复执行前，需要
   - 换用新的点位编码，或
   - 清理 `insp_record` 中该点位本周期的记录，或
   - 直接改点位 `cycle_type` 为 `custom` 且 `cycle_value=0` 以便反复测试

---

## 执行方式

> 全程在**测试系统根目录**执行：`cd D:\APPPROJECTS\pdd-test-system`

### ① 环境准备（一次性，已完成可跳过）

引擎跑在专用虚拟环境里，依赖已装好：
`C:\Users\name\.workbuddy\binaries\python\envs\pdd-test\Scripts\python.exe`（python 3.13.14 / pyyaml 6.0.3 / mcp / openai / pymysql）。

若换新机器，按 `requirements.txt` 装：
```powershell
python -m venv .venv
.venv\Scripts\pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
```

### ② 静态校验（秒级，不需要浏览器）

先校验 YAML 语法、必填字段、step 编号、`.env` 配对与 `${VAR}` 是否都有定义：

```powershell
"C:\Users\name\.workbuddy\binaries\python\envs\pdd-test\Scripts\python.exe" `
  testcases\Inspection-System-Project\testcases\scripts\validate-cases.py `
  testcases\Inspection-System-Project\testcases\frontend
```

### ③ 执行用例

**推荐：`run-test.cmd` 一键启动器**（自动设 `CHROME_PATH`、自动用 pdd-test 环境）：

```powershell
cd D:\APPPROJECTS\pdd-test-system

# A. 跑「一个目录」下的全部用例（递归子目录）—— 最常用
.\run-test testcases\Inspection-System-Project\testcases\frontend\pc

# B. 递归跑整个 frontend（pc + h5，共 14 条）
.\run-test testcases\Inspection-System-Project\testcases\frontend

# C. 只跑单条
.\run-test testcases\Inspection-System-Project\testcases\frontend\pc\pc-001-login.yaml

# D. 绝对路径也可以
.\run-test D:\APPPROJECTS\pdd-test-system\testcases\Inspection-System-Project\testcases\frontend\h5

# E. 调试用：加思维链（每步输出 AI 分析，仅单条时建议开）
.\run-test testcases\Inspection-System-Project\testcases\frontend\pc\pc-006-point-qrcode.yaml --think
```

> **目录模式按路径排序执行**，`frontend/` 下会先跑 h5 再跑 pc——而 h5 用例依赖 pc-005 造出的点位数据。
> 所以**巡检套件请用下面的依赖顺序脚本**，不要直接用目录模式跑 `frontend`。

**按依赖顺序批量执行（巡检套件专用）：**

```powershell
$s = "testcases\Inspection-System-Project\testcases\scripts\run-inspect-tests.ps1"

pwsh $s                              # 全量 14 条，顺序正确
pwsh $s -SkipH5                      # 只跑 PC 11 条
pwsh $s -Only pc-004                 # 只跑匹配的用例
pwsh $s -SkipValidate                # 跳过前置静态校验
```

报告输出到 `testcases\Inspection-System-Project\test-result\run-{时间戳}\`：
`report-{ts}.html`（浏览器直接打开）、`report-{ts}.md`、`{test_id}-detail.md`（逐步日志）、`snapshots/*.txt`。

### ④ 执行前提（务必先确认）

```powershell
# 这几个端口都得通，否则用例会卡在第一步导航
# 3306 MySQL / 6379 Redis / 8080 后端 / 80 PC前端 / 3002 H5
```

| 服务 | 启动方式 |
|---|---|
| MySQL + Redis | 本机服务（当前未启动） |
| 后端 8080 | IDEA 运行 `ruoyi-admin` 的 `RuoYiApplication`，或 `java -jar ruoyi-admin\target\ruoyi-admin.jar` |
| PC 前端 80 | `cd D:\APPPROJECTS\plus-ui-v6.0.0-Vue && npm run dev` |
| H5 3002 | `cd D:\APPPROJECTS\RuoYi-App-Plus && npm run dev:h5`（仅 H5 用例需要） |

---

## 待确认项（执行前请核对）

| 项 | 当前默认值 | 需确认 |
|---|---|---|
| PC 访问地址 | `http://localhost:80` | 是否为实际端口/域名 |
| H5 访问地址 | `http://localhost:3002` | 同上 |
| 登录账号 | `admin / admin123` | 是否为实际测试账号（不建议用超管跑常规回归） |
| 验证码 | 要求关闭 | 若无法关闭需人工介入 |
| 模板/机房等测试数据名 | `自动化测试机房-01` 等 | 若库中已重名请调整 `.env` |

---

## 已知限制

- **H5 真机扫码**：`uni.scanCode` 在浏览器中不可用，用例统一走「手动输入点位编码」通道——与扫码共用同一个 `/inspect/scan/resolve` 接口，业务等价。
- **H5 拍照**：浏览器中由 `input[type=file]` 承载，自动触发文件选择器在部分环境不稳定，`h5-002` 步骤 10 可能需人工点选一次。
- **同文案控件定位**：部分页面搜索区与弹窗表单的 placeholder 文案相同（如「请输入机房名称」）。引擎优先精确文本匹配，其次用步骤 `desc` 作为二次线索。
  - ⚠️ **不要写 `locator.uid_cache_key`**：该字段只有录制器（`recorder.py`）会输出，**执行引擎从不读取**，写了等于没写。官方示例文档 `examples/yaml-format-guide.md` 把它描述成「P0 最高优先级」，与实际实现不符。
- **H5 表单控件（uni-app 特性）**：uni-app / uView 的 H5 产物把 `placeholder` 渲染成**独立的文本节点**，输入框自身不带任何文本——
  ```html
  StaticText "请输入密码"      ← target 文本只能匹配到这里
  textbox                     ← 真正的输入框，无文本
  ```
  引擎已内置「紧邻文本 → 输入框」的回退（`_nearby_text`，仅对 `fill` 类动作生效），所以 `target: "请输入密码"` 这种写法可以直接用，**不需要**额外配 locator。
  注意：两个控件的占位符之间**只隔一个图标节点**时，回退半径必须为 1，否则账号框会把密码框的占位符也算成自己的标签，导致两个值填进同一个框（2026-09-18 已修复）。
