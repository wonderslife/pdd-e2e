# 安卓测试环境自检 —— 运行汇总

- **运行 ID**：android-run-20260916-133232
- **时间**：2026-09-16 13:32:33
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
| badmix | emulator-5554 | http://192.168.137.100:3128 | — | 未测 | — |
| nohook | emulator-5556 | http://192.168.137.100:3129 | — | 未测 | — |

### 设备身份（声明 vs 实测）

| 账号 | 声明机型 | ANDROID_ID | 通话标识 | hook | 实测核对 |
|---|---|---|---|---|---|
| badmix | samsung SM-S9110 | — | imei | none | 未采集 |
| nohook | google Pixel 7（模板 pixel7） | — | imei | none | 未采集 |

> 身份注入分两层：机型属性走 Magisk `resetprop`（`magisk-post-fs-data.sh`）或 `-writable-system` + `product/build.prop`（`build.prop.append`）；ANDROID_ID 属 `Settings.Secure`，需 `settings put` 且改完要 `pm clear` 被测 App。生成脚本：`python tests/test_android_env.py --provision-identity`

### 设备身份限制说明（不判失败）

- badmix：声明了 imei，但 device.hook=none —— **原生模拟器改不了 IMEI/MEID**（modem 二进制硬编码），该声明不会生效。两条路：① 设 device.hook: frida（本文件会生成 hook 脚本，可做到但仅对注入的进程有效）；② 改用第三方模拟器多开器或真机
- nohook：声明了 imei，但 device.hook=none —— **原生模拟器改不了 IMEI/MEID**（modem 二进制硬编码），该声明不会生效。两条路：① 设 device.hook: frida（本文件会生成 hook 脚本，可做到但仅对注入的进程有效）；② 改用第三方模拟器多开器或真机

### 账号档配置问题

- ⚠️ badmix: fingerprint 里的品牌段 'google' 与 ro.product.brand='samsung' 不一致 —— 混搭不同厂商的字段是伪造的典型特征
- ⚠️ badmix: fingerprint 的 product 段 'panther' 与 ro.product.device='dm3q' / ro.product.name='dm3qxxx' 都不匹配 —— 同一台设备这四者必须一致
- ⚠️ badmix: fingerprint 的 device 段 'panther' 与 ro.product.device='dm3q' / ro.product.name='dm3qxxx' 都不匹配 —— 同一台设备这四者必须一致
- ⚠️ badmix: imei='490154203237519' 未通过 Luhn 校验 —— 风控系统的第一道校验就是它，填一个校验位正确的号（用真机号段或按 Luhn 反算最后一位）

## 运行产物


## 说明

本目录只记录环境自检的**环境信息与产物**，不记录用例通过/失败。
用例结论请看 pytest 输出，或生成 HTML 报告：

```bash
python tests/test_android_env.py \
  --html=test-result/android-report.html --self-contained-html
```
