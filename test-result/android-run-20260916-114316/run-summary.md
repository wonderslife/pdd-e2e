# 安卓测试环境自检 —— 运行汇总

- **运行 ID**：android-run-20260916-114316
- **时间**：2026-09-16 11:43:22
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

- **代理机制**：`system`
- **独占 AVD**：True
- **强制出口 IP 唯一**：True
- **强制设备标识唯一**：True

| 账号 | AVD | 出口代理 | 期望出口 IP | 实测出口 IP | 系统代理状态 |
|---|---|---|---|---|---|
| inspector01 | emulator-5554 | http://127.0.0.1:3128 | 203.0.113.10 | ProxyError：HTTPSConnectionPool(host='api.ipify.org', port=443): Max retries exceeded with url: / (Caused by ProxyError('Unable to connect to proxy', ConnectTimeoutError(<HTTPSConnection(host='127.0.0.1', port=3128) at 0x28a4211f4d0>, 'Connection to 127.0.0.1 timed out. (connect timeout=2.0)'))) | — |
| inspector02 | emulator-5556 | http://127.0.0.1:3129 | 203.0.113.11 | ProxyError：HTTPSConnectionPool(host='api.ipify.org', port=443): Max retries exceeded with url: / (Caused by ProxyError('Unable to connect to proxy', ConnectTimeoutError(<HTTPSConnection(host='127.0.0.1', port=3129) at 0x28a420e3110>, 'Connection to 127.0.0.1 timed out. (connect timeout=2.0)'))) | — |

## 运行产物

- `identity-egress.json`（0.0 KB）

## 过程记录

- 账号身份档校验通过：2 个账号，proxy_mode=system，独占AVD=True

## 说明

本目录只记录环境自检的**环境信息与产物**，不记录用例通过/失败。
用例结论请看 pytest 输出，或生成 HTML 报告：

```bash
python tests/test_android_env.py \
  --html=test-result/android-report.html --self-contained-html
```
