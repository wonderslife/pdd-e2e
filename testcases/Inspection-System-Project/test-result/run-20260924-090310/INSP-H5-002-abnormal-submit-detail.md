# H5 扫码巡检：异常项校验（说明必填 + 照片必传）并进入异常池

- **ID**: `INSP-H5-002-abnormal-submit`
- **状态**: **PARTIAL** (62.5%)
- **时间**: 2026-09-24 09:04:18
- **配置**: ```json
{
  "max_retries": 3,
  "retry_delay": 1.0,
  "default_wait": 2.0,
  "snapshot_timeout": 10.0,
  "element_wait_timeout": 5.0,
  "continue_on_error": true,
  "screenshot_on_error": true,
  "verbose_logging": true,
  "llm_think_enabled": false,
  "llm_think_deep": false
}
```

---

### 步骤1: 打开 H5 并完成登录（若已有登录态会被自动跳过） [⚠️ failed_assert]

```
动作: navigate
工具: new_page
参数: {
  "url": "http://localhost:3002/#/pages/inspect/scan"
}
结果: ## Pages
1: about:blank
2: 登录 (http://localhost:3002/#/pages/login/index) [selected]
断言:
  ❌ [medium] text_contains: 扫码巡检 → '扫码巡检' not found in snapshot
执行前快照预览:
## Latest page snapshot
uid=2_0 RootWebArea "登录" url="http://localhost:3002/#/pages/login/index"
  uid=2_1 ignored
    uid=2_2 generic
      uid=2_3 generic
        uid=2_4 ignored
          uid=2_5 i...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Inspection-System-Project\test-result\run-20260924-090310\snapshots\snap-20260924-090427.txt`
```

### 步骤2: 进入「扫码巡检」页并手动输入点位 2 的编码 [✅ success]

```
动作: fill
工具: fill
参数: {
  "value": "RM-AT-01-P02",
  "uid": "8_227",
  "includeSnapshot": false
}
结果: Successfully filled out the element
断言:
  ✅ [medium] field_filled: 字段已填写 → assume filled (cannot verify via MCP)
执行前快照预览:
## Latest page snapshot
uid=2_0 RootWebArea "机房巡检" url="http://localhost:3002/#/pages/inspect/scan"
  uid=8_0 ignored
    uid=8_1 generic
      uid=8_2 generic
        uid=8_3 ignored
          uid=8_...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Inspection-System-Project\test-result\run-20260924-090310\snapshots\snap-20260924-090440.txt`
```

### 步骤3: 点击「查询」进入巡检执行页 [✅ success]

```
动作: click
工具: click
参数: {
  "uid": "8_231",
  "includeSnapshot": false
}
结果: Successfully clicked on the element
断言:
  ✅ [high] network_called:  → network check skipped (would need network_requests)
执行前快照预览:
## Latest page snapshot
uid=2_0 RootWebArea "机房巡检" url="http://localhost:3002/#/pages/inspect/scan"
  uid=8_0 ignored
    uid=8_1 generic
      uid=8_2 generic
        uid=8_3 ignored
          uid=8_...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Inspection-System-Project\test-result\run-20260924-090310\snapshots\snap-20260924-090441.txt`
```

### 步骤4: 确认进入「巡检执行」页并显示校验提示「判定为「异常」的巡检项必须填写说明并上传至少 1 张照片」 [✅ success]

```
动作: assert_multiple
工具: (assert_multiple)
参数: {}
结果: text_contains=PASS; text_contains=PASS
断言:
  ✅ [high] text_contains: 自动化测试点位-02 → '自动化测试点位-02' found in snapshot
  ✅ [medium] text_contains: 必须填写说明 → '必须填写说明' found in snapshot
执行前快照预览:
## Latest page snapshot
uid=2_0 RootWebArea "巡检执行" url="http://localhost:3002/#/pages/inspect/execute?pointId=2102924122776121345"
  uid=15_0 ignored
    uid=15_1 generic
      uid=15_2 generic
      ...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Inspection-System-Project\test-result\run-20260924-090310\snapshots\snap-20260924-090446.txt`
```

### 步骤5: 把第 1 个巡检项判定为「异常」 [✅ success]

```
动作: click
工具: click
参数: {
  "uid": "12_16",
  "includeSnapshot": false
}
结果: Successfully clicked on the element
断言:
  ✅ [high] element_visible:  → element '异常说明（必填）' found
执行前快照预览:
## Latest page snapshot
uid=2_0 RootWebArea "巡检执行" url="http://localhost:3002/#/pages/inspect/execute?pointId=2102924122776121345"
  uid=15_0 ignored
    uid=15_1 generic
      uid=15_2 generic
      ...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Inspection-System-Project\test-result\run-20260924-090310\snapshots\snap-20260924-090449.txt`
```

### 步骤6: 不填异常说明、不上传照片，直接点「提交巡检」，验证被拦截 [✅ success]

```
动作: click
工具: click
参数: {
  "uid": "12_32",
  "includeSnapshot": false
}
结果: Successfully clicked on the element
断言:
  ✅ [high] toast_visible: 异常说明不能为空 → LiveToast: '第 1 项「机房温度」异常说明不能为空'
  ✅ [medium] element_visible:  → element '提交巡检' found
执行前快照预览:
## Latest page snapshot
uid=2_0 RootWebArea "巡检执行" url="http://localhost:3002/#/pages/inspect/execute?pointId=2102924122776121345"
  uid=26_0 ignored
    uid=26_1 generic
      uid=26_2 generic
      ...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Inspection-System-Project\test-result\run-20260924-090310\snapshots\snap-20260924-090453.txt`
```

### 步骤7: 填写该巡检项的「异常说明」 [✅ success]

```
动作: fill
工具: fill
参数: {
  "value": "机房温度 31.5℃，超过 18~27℃ 标准区间",
  "uid": "19_7",
  "includeSnapshot": false
}
结果: Successfully filled out the element
断言:
  ✅ [medium] field_filled: 字段已填写 → assume filled (cannot verify via MCP)
执行前快照预览:
## Latest page snapshot
uid=2_0 RootWebArea "巡检执行" url="http://localhost:3002/#/pages/inspect/execute?pointId=2102924122776121345"
  uid=36_0 ignored
    uid=36_1 generic
      uid=36_2 generic
      ...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Inspection-System-Project\test-result\run-20260924-090310\snapshots\snap-20260924-090455.txt`
```

### 步骤8: 填写该巡检项的「填写数值」 [✅ success]

```
动作: fill
工具: fill
参数: {
  "value": "31.5",
  "uid": "19_7",
  "includeSnapshot": false
}
结果: Successfully filled out the element
断言:
  ✅ [medium] field_filled: 字段已填写 → assume filled (cannot verify via MCP)
执行前快照预览:
## Latest page snapshot
uid=2_0 RootWebArea "巡检执行" url="http://localhost:3002/#/pages/inspect/execute?pointId=2102924122776121345"
  uid=36_0 ignored
    uid=36_1 generic
      uid=36_2 generic
      ...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Inspection-System-Project\test-result\run-20260924-090310\snapshots\snap-20260924-090456.txt`
```

### 步骤9: 再次点「提交巡检」，验证「异常必须上传至少 1 张照片」拦截 [✅ success]

```
动作: click
工具: click
参数: {
  "uid": "12_32",
  "includeSnapshot": false
}
结果: Successfully clicked on the element
断言:
  ✅ [high] toast_visible: 上传至少 1 张照片 → LiveToast: '第 1 项「机房温度」异常必须上传至少 1 张照片'
执行前快照预览:
## Latest page snapshot
uid=2_0 RootWebArea "巡检执行" url="http://localhost:3002/#/pages/inspect/execute?pointId=2102924122776121345"
  uid=36_0 ignored
    uid=36_1 generic
      uid=36_2 generic
      ...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Inspection-System-Project\test-result\run-20260924-090310\snapshots\snap-20260924-090500.txt`
```

### 步骤10: 点击该异常项的拍照占位，上传现场照片（若浏览器文件选择器无法自动触发，此步人工完成） [❌ failed]

```
动作: upload_file
工具: (locate)
参数: {}
错误: 未定位到目标元素: target='拍照'（快照中无匹配，请检查页面结构或 target 文案）
重试次数: 3
执行前快照预览:
## Latest page snapshot
uid=2_0 RootWebArea "巡检执行" url="http://localhost:3002/#/pages/inspect/execute?pointId=2102924122776121345"
  uid=50_0 ignored
    uid=50_1 generic
      uid=50_2 generic
      ...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Inspection-System-Project\test-result\run-20260924-090310\snapshots\snap-20260924-090508.txt`
```

### 步骤11: 填写「整体备注」 [✅ success]

```
动作: fill
工具: fill
参数: {
  "value": "自动化回归-H5异常提交",
  "uid": "12_30",
  "includeSnapshot": false
}
结果: Successfully filled out the element
断言:
  ✅ [medium] field_filled: 字段已填写 → assume filled (cannot verify via MCP)
执行前快照预览:
## Latest page snapshot
uid=2_0 RootWebArea "巡检执行" url="http://localhost:3002/#/pages/inspect/execute?pointId=2102924122776121345"
  uid=50_0 ignored
    uid=50_1 generic
      uid=50_2 generic
      ...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Inspection-System-Project\test-result\run-20260924-090310\snapshots\snap-20260924-090509.txt`
```

### 步骤12: 点击「提交巡检」提交（此时说明与照片均满足，应成功） [⚠️ failed_assert]

```
动作: click
工具: click
参数: {
  "uid": "12_32",
  "includeSnapshot": false
}
结果: Successfully clicked on the element
断言:
  ✅ [high] network_called:  → network check skipped (would need network_requests)
  ❌ [high] toast_visible: 巡检记录已提交 → LiveToast: '第 1 项「机房温度」异常必须上传至少 1 张照片'
执行前快照预览:
## Latest page snapshot
uid=2_0 RootWebArea "巡检执行" url="http://localhost:3002/#/pages/inspect/execute?pointId=2102924122776121345"
  uid=50_0 ignored
    uid=50_1 generic
      uid=50_2 generic
      ...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Inspection-System-Project\test-result\run-20260924-090310\snapshots\snap-20260924-090515.txt`
```

### 步骤13: 切到 PC 管理端「机房巡检 > 异常处理」，验证新异常项已入池（待处理） [✅ success]

```
动作: navigate
工具: new_page
参数: {
  "url": "http://localhost:80/inspect/abnormal"
}
结果: ## Pages
1: about:blank
2: 巡检执行 (http://localhost:3002/#/pages/inspect/execute?pointId=2102924122776121345)
3: RuoYi-Vue-Plus后台管理系统 (http://localhost/login?redirect=/inspect/abnormal) [selected]
断言:
  ✅ [high] network_called:  → network check skipped (would need network_requests)
执行前快照预览:
## Latest page snapshot
uid=67_0 RootWebArea "RuoYi-Vue-Plus后台管理系统" url="http://localhost/login?redirect=/inspect/abnormal"
  uid=67_1 ignored
    uid=67_2 ignored
      uid=67_3 generic
        uid=6...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Inspection-System-Project\test-result\run-20260924-090310\snapshots\snap-20260924-090524.txt`
```

### 步骤14: 「处理状态」选择「待处理」并搜索 [⚠️ failed_assert]

```
动作: select_option
工具: fill
参数: {
  "value": "待处理",
  "uid": "67_50",
  "includeSnapshot": false
}
结果: Error: Failed to interact with the element with uid 67_50. The element did not become interactive within the configured timeout.
重试次数: 3
断言:
  ❌ [medium] element_text: 待处理 → Element text contains '待处理': False
执行前快照预览:
## Latest page snapshot
uid=67_0 RootWebArea "RuoYi-Vue-Plus后台管理系统" url="http://localhost/login?redirect=/inspect/abnormal"
  uid=71_0 ignored
    uid=71_1 ignored
      uid=71_2 generic
        uid=7...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Inspection-System-Project\test-result\run-20260924-090310\snapshots\snap-20260924-090553.txt`
```

### 步骤15: 点击「搜索」，校验刚提交的异常项出现在列表中（点位名 + 异常说明） [⚠️ failed_assert]

```
动作: click
工具: click
参数: {
  "uid": "67_50",
  "includeSnapshot": false
}
结果: Successfully clicked on the element
断言:
  ❌ [high] text_contains: 自动化测试点位-02 → '自动化测试点位-02' not found in snapshot
  ❌ [medium] text_contains: 机房温度 31.5℃，超过 18~27℃ 标准区间 → '机房温度 31.5℃，超过 18~27℃ 标准区间' not found in snapshot
执行前快照预览:
## Latest page snapshot
uid=67_0 RootWebArea "RuoYi-Vue-Plus后台管理系统" url="http://localhost/login?redirect=/inspect/abnormal"
  uid=71_0 ignored
    uid=71_1 ignored
      uid=71_2 generic
        uid=7...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Inspection-System-Project\test-result\run-20260924-090310\snapshots\snap-20260924-090557.txt`
```

### 步骤16: 打开该异常项「详情」，确认现场照片可预览 [⚠️ failed_assert]

```
动作: click
工具: click
参数: {
  "uid": "67_50",
  "includeSnapshot": false
}
结果: Successfully clicked on the element
断言:
  ❌ [high] element_visible:  → element '异常说明' not found
执行前快照预览:
## Latest page snapshot
uid=67_0 RootWebArea "RuoYi-Vue-Plus后台管理系统" url="http://localhost/login?redirect=/inspect/abnormal"
  uid=89_0 ignored
    uid=89_1 ignored
      uid=89_2 generic
        uid=8...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Inspection-System-Project\test-result\run-20260924-090310\snapshots\snap-20260924-090601.txt`
```

