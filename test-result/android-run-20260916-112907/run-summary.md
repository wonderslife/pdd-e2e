# 安卓测试环境自检 —— 运行汇总

- **运行 ID**：android-run-20260916-112907
- **时间**：2026-09-16 11:29:07
- **Appium 端点**：http://192.168.137.100:4723
- **目标设备**：emulator-5554
- **被测 App**：未配置（骨架自检模式）
- **shell 后端**：未探测
- **配置文件**：未使用（全用内置默认值）

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

## 运行产物


## 说明

本目录只记录环境自检的**环境信息与产物**，不记录用例通过/失败。
用例结论请看 pytest 输出，或生成 HTML 报告：

```bash
python tests/test_android_env.py \
  --html=test-result/android-report.html --self-contained-html
```
