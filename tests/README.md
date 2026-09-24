# AI Test Framework - 测试框架核心

本目录包含 AI 自动化测试框架的核心 Python 代码。

## 文件说明

| 文件 | 用途 |
|------|------|
| `testcase-ai.py` | 主执行入口，YAML 驱动的测试用例执行引擎 |
| `login_manager.py` | 登录状态管理器，智能检测/跳过/切换用户登录 |
| `.env.test` | 环境变量配置（用户名、密码、MCP 配置等） |
| `test_android_env.py` | **安卓端环境自检用例集**（pytest + 配置驱动，Appium/uiautomator2） |
| `device-templates.yaml` | **真机机型模板库**（30 款市面常见机型），供 `device.template` 引用 |

## 安卓端测试（test_android_env.py）

面向「Windows → VMware → Ubuntu Server → KVM → AVD」测试环境，用于验证环境各层是否就绪。
默认配置指向落地方案中的示例环境（Appium `192.168.137.100:4723`、`emulator-5554`）。

```bash
# 环境自检（Appium 未起时表现为 3 个根因失败 + 其余跳过，不会级联报错）
python tests/test_android_env.py

# 生成配置模板后按实际环境修改
python tests/test_android_env.py --init-config     # 写入 tests/android-env.yaml
python tests/test_android_env.py --print-config    # 只看解析后的最终配置

# 带 HTML 报告
python tests/test_android_env.py \
  --html=test-result/android-report.html --self-contained-html
```

用例分组（共 27 项，可用 `-k TestA` 等筛选）：

| 组 | 内容 |
|----|------|
| `TestA_AppiumService` | Appium 服务可达、/sessions 可用、本机 adb 能看到 AVD |
| `TestB_AppiumSession` | 会话可建、软件渲染所需的超时 capability 真的生效 |
| `TestC_DeviceBaseline` | 启动完成、CPU ABI 为 x86_64、渲染后端非宿主 GPU |
| `TestD_RuntimeTuning` | 三大动画已关、shell 通路可用 |
| `TestE_Observability` | 截图、UI 树、crash 缓冲区 |
| `TestF_AppUnderTest` | 被测 App 启动/前台/首屏（`app.package` 留空则整组跳过） |
| `TestG_RunReport` | 运行产物完整性 |
| `TestH_AccountIdentity` | **可选**：一个账号一个出口 IP + 设备标识互不相同 |
| `TestI_DeviceIdentity` | **可选**：设备身份声明是否生效 + 跨运行是否稳定 |

配置优先级：内置默认值 < `tests/android-env.yaml` < 环境变量（`APPIUM_HOST`、`ANDROID_UDID`、
`ANDROID_APP_PACKAGE`、`ADB_SERVER_SOCKET` 等）。运行产物写入
`test-result/android-run-<时间戳>/`（截图、UI 树、能力快照、`run-summary.md`）。

### 可选功能：动态 IP + 账号身份隔离

默认关闭（`identity.enabled: false`），不启用时 `TestH` / `TestI` 整组跳过，不影响上面的环境自检。
开启后强制两条规则：**一个账号一个出口 IP**、**每个账号的 AVD 设备标识互不相同**。
模型是 **账号 ↔ AVD ↔ 设备身份 ↔ 出口 IP 四者固定绑定**，不是「每次启动随机换一套」。

```bash
python tests/test_android_env.py --fingerprint-audit    # 只读：App 能读到哪些标识、跨账号是否相同
python tests/test_android_env.py --identity-plan        # 只读：各账号规划 + 启动命令 + 自洽性检查
python tests/test_android_env.py --provision-identity   # 生成设备身份注入脚本（不改设备）
python tests/test_android_env.py -k TestH               # 账号隔离：一账号一 IP、设备互不相同
python tests/test_android_env.py -k TestI               # 设备身份：声明是否生效、跨运行是否稳定
```

`--fingerprint-audit` 只依赖 adb（不需要 Appium，但 AVD 要运行着）。它逐账号采集
`getprop` 全量 + `settings` 侧标识，按四类输出对照表，直接回答
**「多账号登录同一个 App，App 能读出哪些字段、其中哪些是所有账号完全一样的」**：
逐账号唯一项（可用作隔离）、取决于 AVD 建法项、全实例相同且改不掉的项、可注入改变项。
判定依据是**跨账号是否相同**，而不是「能不能改」—— 只有前者才会让 App 认定多账号来自同一台设备。
报告同时写入 `test-result/fingerprint-audit.md`。

账号档配置（`tests/android-env.yaml`）：

```yaml
identity:
  enabled: true
  proxy_mode: system     # system=运行时下发系统代理 / emulator=启动参数 -http-proxy / none=不切 IP
  enforce_unique_egress: true
  enforce_unique_device: true
  allow_shared_avd: false
  clear_proxy_after: true
  device_identity:
    enabled: true
    enforce_consistency: true   # fingerprint 三段必须与 brand/device/name 自洽
    baseline_check: true        # 跨运行比对，身份漂移即失败
    provision_dir: test-result/identity-provision
accounts:
  - name: inspector01
    proxy: "http://192.168.137.100:3128"
    expected_egress_ip: "203.0.113.10"
    device:
      template: pixel7                  # 内置 3 个：pixel7 / xiaomi13 / samsung_s23
                                        # 另可引用 device-templates.yaml 里的 30 款真机（见下节）
      # android_id 建议留空 —— API>=26 时改它不一定生效，见下方限制说明
      android_id: "5f2a1c9d3e7b4086"
  - name: inspector02
    proxy: "http://192.168.137.100:3129"
    expected_egress_ip: "203.0.113.11"
    device:
      template: xiaomi13
      hook: frida                       # 声明 IMEI/MEID 时必须配，否则该声明无法生效
      imei: "490154203237518"
```

`udid` / `console_port` / `system_port` / `emu_uuid` 留空会自动派生（`emulator-5554`、`5554+2i`、
`8200+i`、按账号名派生的稳定 UUID）。`--identity-plan` 会给出每个账号完整的 AVD 启动命令，
含 `-http-proxy`、`-gpu software`、`-feature -Vulkan`、`-prop qemu.uuid=`（`-prop` 只接受 `qemu.*` 前缀）。

**两种出口 IP 机制的取舍（官方明确二者互斥）**：

| 机制 | 配置值 | 作用层 | 覆盖范围 | 换 IP 代价 |
|---|---|---|---|---|
| Android 系统代理 | `system` | 应用层 | 浏览器与**多数** App | 无需重启 AVD |
| Emulator 代理 | `emulator` | 网络层 | **全部 TCP** | 必须重启 AVD |

### 设备身份：能改什么、改不动什么

| 层级 | 能改的标识 | 手段 | 前置条件 | 代价 |
|---|---|---|---|---|
| L0 启动参数 | `qemu.uuid`（**只有 `qemu.*` 前缀被接受**） | `-prop qemu.uuid=<uuid>` | 无 | 重启 AVD |
| L1 天然唯一 | `ro.serialno`、`ANDROID_ID` | 逐账号独占 AVD + 独占端口 | 无 | 建 AVD 时一次性 |
| L2 机型指纹 | `ro.product.*`、`ro.build.fingerprint` | Magisk `resetprop`（`--provision-identity` 生成） | AVD 需 root（rootAVD） | 重启 AVD |
| L3 通话标识 | IMEI / MEID / IMSI | Frida / LSPosed hook `TelephonyManager` | L2 + hook 框架 | 重启 App 进程 |

关键约束：官方文档写明 `-prop` 只接受**被标记为 `qemu_prop` 的属性名**（`qemu.*` / `emu.*`）。
`ro.product.model`、`ro.build.fingerprint`、`persist.radio.imei` 都不在其中，**不可能靠启动参数改**。

`--provision-identity` 会为每个声明了 `device` 的账号生成 5 个文件：

| 文件 | 用途 |
|---|---|
| `magisk-post-fs-data.sh` | **首选**。Magisk 模块脚本，`post-fs-data` 在 zygote 之前跑，App 起来读到的就是新值 |
| `build.prop.append` | 备选（不装 Magisk）。走 `-writable-system`，注意型号实际来自 **product** 分区 |
| `frida-identity.js` | 唯一能伪造 IMEI/MEID/IMSI 的路线；覆盖 `getDeviceId`/`getImei`/`getMeid` + `Build.*` + `SystemProperties.get` |
| `apply.sh` | 逐条执行的核验脚本：按 API 级别分支处理 ANDROID_ID 并回读，不做隐藏动作 |
| `ssaid-patch.sh` | **只读**核验脚本：读 App 实际看到的 ANDROID_ID（SSAID），并打印改值步骤。确需固定值时才用 |

**限制（已在代码里做成硬校验，不会静默失败）**：

- **只支持 HTTP 代理**。Android 系统代理与 `-http-proxy` 都不支持 SOCKS，配 `socks5://` 会直接报错
  并给出 redsocks/transocks 的替代路径。
- **`system` 模式下代理不能带凭据**。`global http_proxy` 只接受 `host:port`，会静默丢弃鉴权信息，
  因此带 `user:pass@` 配 `system` 模式会被判为配置错误，提示改用 `emulator` 模式。
- **机型字段不许混搭**。`fingerprint` 的 `brand/product/device` 三段必须与 `ro.product.brand`、
  `ro.product.device`、`ro.product.name` 对得上，混搭会被判配置错误 —— 这是伪造的典型特征。
- **IMEI 必须过 Luhn 校验**。位数不是 14/15 或校验位不对都会被拦下。
- **IMEI / MEID 在原生模拟器上改不了**（除非配 `hook`）。它们是模拟器二进制内硬编码的
  （`android_modem.c` 的 `+CGSN` 应答，实测 `000000000000000`），`adb`、`config.ini`、`-prop`
  都改不了，`fastboot oem writeimei` 也不可用（模拟器无 fastboot）；GSM 模拟器上 `getMeid()` 返回 null。
  声明了 IMEI 却没配 `hook` 时 `TestI.test_27` 会**直接判失败**并给出三条替代路径，不静默放过。
  另外：即使配了 hook，客户端 IMEI 由被测 App 所在进程读取，测试进程**无法代它断言**，
  必须在 App 内或服务端日志侧确认。
- **「IMEI 所有账号都一样」通常不构成风险，因为多数 App 根本读不到**（Android 10 起）：
  `targetSdk ≥ 29` 调用即抛 `SecurityException`；`targetSdk ≤ 28` 且持 `READ_PHONE_STATE`
  只得到 `null` 或占位符数据；第三方 App 无法声明 `READ_PRIVILEGED_PHONE_STATE`。
  **只有 device owner / profile owner 应用与持运营商特权（carrier privileges）的应用**
  才真的读得到 —— 只有这两种情况才必须上 hook。到底哪些字段逐账号相同，
  别靠推测，跑 `--fingerprint-audit` 实测。
- **不允许身份漂移**。`TestI.test_26` 与 `test-result/identity-baseline.json` 比对，
  同一账号两次跑出来不是同一台设备就判失败。改过 AVD/镜像/注入脚本后删掉该文件重建基线。
- **号码不许跨账号重复**。`android_id` / `imei` / `meid` / `imsi` 撞车直接判冲突；机型允许重复。
- **`ANDROID_ID` 在 API ≥ 26 上不能靠 `settings put` 改**。Android 8.0 起它按
  「**应用签名密钥 + 用户 + 设备**」作用域，App 实际读到的值在
  `/data/system/users/<uid>/settings_ssaid.xml`（SSAID），
  而 `settings get/put secure android_id` 读写的是 Settings 库里**另一个值** ——
  只回读 settings 会得到「看起来改了、App 其实没变」的假通过。
  因此：
  - **推荐做法是不改**。逐账号独占 AVD 时 `ANDROID_ID` 本就会随机生成、天然不同；
  - 确需固定值：改 SSAID 文件（需 root + 恢复 `chown`/`restorecon` + 重启），见 `ssaid-patch.sh`；
  - 能读到 SSAID 时（AVD 已 root）`TestI.test_25` **硬断言 App 实际读到的值**；
    读不到时只断言 settings 层，并把「App 侧未验证」写入 `run-summary.md` 的
    **未验证事项**段 —— 不会因为 settings 回读一致就宣告成功。
  - 顺带一句：SSAID 在卸载/重装后**不会**重新生成（签名密钥不变的前提下），
    所以「卸载重装换台设备」这个思路在这里不成立。
- **埋点类 SDK 的设备 ID 是"生成一次、持久化"的**。阿里云 QuickTracking 的设备 ID
  由 `androidid` 等输入派生后存本地，只有卸载或清数据才重建。
  所以顺序必须是「**先定身份与代理，再首次启动被测 App**」；
  顺序反了（先跑一次再改身份）后台看到的仍是旧设备，改完要用 `pm clear <包名>` 重来。
  详见桌面文档《7.阿里云埋点SDK采集项与账号隔离评估》。

业务若强依赖 IMEI 且不想上 hook：改用第三方模拟器多开器（可改 IMEI/机型/ANDROID_ID）或真机。

### 机型模板库：30 款真机，开箱可用

`device.template` 的取值有两个来源，合并后共 **33 个名字**：

| 来源 | 位置 | 数量 | 说明 |
|---|---|---|---|
| 内置 | `test_android_env.py` 的 `DEVICE_TEMPLATES` | 3 | `pixel7` / `xiaomi13` / `samsung_s23` |
| 外部 | `tests/device-templates.yaml` | 30 | 市面常见机型，按 `template:` 名引用 |

外部文件**不存在时行为完全不变**（内置 3 个照常可用）；文件损坏或缺 `pyyaml` 只打一行告警、不抛异常。
加载时按 `DEVICE_SHORT_KEYS` 过滤，只认 `brand/manufacturer/model/name/device/board/fingerprint`
七个短名（`android/source/basis/capture/note` 等元数据不参与注入）。

覆盖（实测计数）：Redmi 10 款、Xiaomi 5 款、OnePlus 4 款、OPPO 2 款、samsung 2 款、google 2 款、
POCO 1 款、realme 1 款、HUAWEI 1 款、HONOR 1 款，另有 1 款（`redmi_note8`）的 `brand` 真机值就是
**小写 `xiaomi`** —— 不是笔误，`ro.product.brand` 大小写本身是设备特征，别去「规范化」它。共 30 款，
Android 8.1 → 15。

同类细节：小米系 `ro.product.model` **不全是型号代码** —— 红米 K30 Pro 填 `Redmi K30 Pro`、
红米 Note 8 填 `Redmi Note 8`，而红米 K40 填 `M2012K11AC`。模板一律按真机原文填。

取值分两档，文件里每条都用 `source` 标出，**不把拼装值冒充真机值**：

| 档 | 含义 | 条数 |
|---|---|---|
| `certified` | 来自真机认证指纹库（MagiskHidePropsConf `prints.sh`）或官方 OTA 原文，逐字未改 | 23 |
| `assembled` | 当代机型（2023-2024）按同代真机 ROM 原文替换 `product`/`device` 段拼装，`basis` 注明依据 | 7 |

三条硬约束（照抄值即可自动满足，手改时注意）：

1. `fingerprint` 五段必须与 `brand`/`device`/`name` 自洽 —— 否则 `check_device_consistency` 判配置错误；
2. 声明了 6 个 `ro.product.*` 中任一字段就**必须给 fingerprint**，只给一半会被拦下；
3. 号码类字段（`android_id` / `imei` / `meid` / `imsi`）**不跨账号重复**，重复即判冲突；
   机型（`model` / `fingerprint`）**允许重复** —— 两个账号用同款手机是正常场景，代码里明确放行。

`board` 取值按品牌惯例：小米/红米用设备代号（本库里是 `alioth`/`ginkgo`/`sweet`/`dandelion` 这类），
三星用 `a52q`/`o1s`，Pixel 用 `redfin`/`oriole`，一加 8/8T/9 直接用型号名（`OnePlus8`），
一加 12 EEA 版用平台名（`pineapple`），OPPO/realme 用型号（`OP4C2DL1`/`RMX1931L1`），
华为/荣耀用代号（`HWLYA`/`HWJSN-H`）—— 以上都是文件里实测存在的取值。
**30 条全部填了 `board`，一个不空** —— 留空会让 AVD 保留模拟器自己的 `Build.BOARD`，
反而把模拟器特征暴露给 App；其中 2 条（`redmi_note13pro5g` / `redmi_note12pro`）的 board
是依据本库 8 条认证小米系条目「board == device 代号」的一致惯例补的，`note` 里已注明，抓到真机可覆盖。

文件末尾另有 `pending:` 段 3 条（vivo X90 / iQOO 12 / 荣耀 100）—— vivo/iQOO 与独立后的荣耀
在两个公共指纹库里都**没有收录**，故指纹留空、附采集命令，**不计入 30 条**。要补全就在真机上跑：

```bash
adb shell getprop | grep -E 'ro\.product|ro\.build\.fingerprint'
```

把输出贴进对应条目即可（字段名与模板一致，直接对齐）。

> 合规边界：以上功能用于**自有或已获授权** App 在自建测试环境中的多账号验证。
> 不得用于绕过第三方平台风控、批量注册或刷量。

## 快速开始

```bash
# 1. 配置环境变量（编辑 .env.test）
vim .env.test

# 2. 执行测试用例
python testcase-ai.py ../testcases/login-flow.yaml

# 3. 查看结果
# 结果自动输出到 ../test-result/run-时间戳/
```

## 核心能力

- **YAML 驱动**: 用声明式 YAML 编写测试步骤，无需写代码
- **MCP 浏览器自动化**: 通过 Chrome DevTools MCP 控制浏览器
- **智能登录管理**: 自动检测已登录状态，支持用户切换
- **多层级错误检测**: 4 层错误识别，避免假阳性报告
- **SPA 渲染等待**: 自动检测页面渲染完成，处理新标签页切换
- **本地 LLM 集成**: 可选接入本地模型进行元素语义匹配

## 架构概览

```
tests/
├── testcase-ai.py      # 主引擎 (ActionExecutor + 断言系统)
├── login_manager.py    # 登录管理 (LoginManager)
└── .env.test           # 运行时配置
```

## 依赖

- Python 3.10+
- `mcp` 包 (Model Context Protocol 客户端)
- Chrome DevTools MCP Server (`npx chrome-devtools-mcp`)
