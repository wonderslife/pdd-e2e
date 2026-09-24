# 安卓测试环境自检 —— 运行汇总

- **运行 ID**：android-run-20260916-133304
- **时间**：2026-09-16 13:34:16
- **Appium 端点**：http://192.168.137.100:4723
- **目标设备**：emulator-5554
- **被测 App**：未配置（骨架自检模式）
- **shell 后端**：不可用（未找到 adb）
- **配置文件**：D:\APPPROJECTS\pdd-test-system\tests\android-env.yaml

## 关键参数

| 项 | 值 |
|---|---|
| newCommandTimeout | 300 |
| uiautomator2ServerInstallTimeout | 120000 |
| uiautomator2ServerLaunchTimeout | 120000 |
| uiautomator2ServerReadTimeout | 120000 |
| adbExecTimeout | 120000 |
| waitForIdleTimeout | 1000 |
| animationIdleTimeout | 2000 |
| disableWindowAnimation | True |
| systemPort | 8200 |

## 账号身份隔离（动态 IP + 设备标识）

- **代理机制**：`emulator`
- **独占 AVD**：True
- **强制出口 IP 唯一**：True
- **强制设备标识唯一**：True

| 账号 | AVD | 出口代理 | 期望出口 IP | 实测出口 IP | 系统代理状态 |
|---|---|---|---|---|---|
| inspector01 | emulator-5554 | http://192.168.137.100:3128 | 203.0.113.10 | ProxyError：HTTPSConnectionPool(host='myip.ipip.net', port=443): Max r… | — |
| inspector02 | emulator-5556 | http://192.168.137.100:3129 | 203.0.113.11 | ProxyError：HTTPSConnectionPool(host='myip.ipip.net', port=443): Max r… | — |

### 设备身份（声明 vs 实测）

| 账号 | 声明机型 | ANDROID_ID | 通话标识 | hook | 实测核对 |
|---|---|---|---|---|---|
| inspector01 | google Pixel 7（模板 pixel7） | 5f2a1c9d3e7b4086 | — | none | 未采集 |
| inspector02 | Xiaomi 2211133C（模板 xiaomi13） | — | imei | frida | 未采集 |

> 身份注入分两层：机型属性走 Magisk `resetprop`（`magisk-post-fs-data.sh`）或 `-writable-system` + `product/build.prop`（`build.prop.append`）；ANDROID_ID 属 `Settings.Secure`，需 `settings put` 且改完要 `pm clear` 被测 App。生成脚本：`python tests/test_android_env.py --provision-identity`

### 设备身份限制说明（不判失败）

- inspector02：声明了 imei，hook=frida —— 会生成对应 hook 脚本。注意：客户端 IMEI 由被测 App 所在进程读取，测试进程**无法代它断言**，需在 App 内或服务端日志侧确认，本文件只保证脚本已生成且参数自洽

## 运行产物

- `identity-egress.json`（1.1 KB）
- `session-capabilities.json`（0.6 KB）

## 过程记录

- [INFO] 未产出的观测产物（多为会话未建立所致）：['appium-status.json', 'boot-screenshot.png', 'boot-ui-hierarchy.xml']
- 产物目录：D:\APPPROJECTS\pdd-test-system\test-result\android-run-20260916-133304
- 账号身份档校验通过：2 个账号，proxy_mode=emulator，独占AVD=True
- 设备身份校验通过：2 个账号声明了身份，hook=frida,none
-   账号 inspector01 → google Pixel 7（模板 pixel7）
-   账号 inspector02 → Xiaomi 2211133C（模板 xiaomi13），通话标识声明：imei
- 通话标识走 hook 路线（1 个账号），脚本已生成。⚠️ 客户端 IMEI 由被测 App 所在进程读取，测试进程无法代它断言 —— 生效与否必须在 App 内或服务端日志侧确认

## 说明

本目录只记录环境自检的**环境信息与产物**，不记录用例通过/失败。
用例结论请看 pytest 输出，或生成 HTML 报告：

```bash
python tests/test_android_env.py \
  --html=test-result/android-report.html --self-contained-html
```
