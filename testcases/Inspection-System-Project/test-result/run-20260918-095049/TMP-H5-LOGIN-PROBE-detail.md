# 临时探针：H5 登录输入值与登录结果

- **ID**: `TMP-H5-LOGIN-PROBE`
- **状态**: **PASS** (100.0%)
- **时间**: 2026-09-18 09:50:49
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

### 步骤1: 打开 H5 登录页 [✅ success]

```
动作: navigate
工具: new_page
参数: {
  "url": "http://localhost:3002/#/pages/login/index"
}
结果: ## Pages
1: about:blank
2: 登录 (http://localhost:3002/#/pages/login/index) [selected]
执行前快照预览:
## Latest page snapshot
uid=1_0 RootWebArea url="about:blank"
  uid=1_1 ignored
    uid=1_2 ignored


快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Inspection-System-Project\test-result\run-20260918-095049\snapshots\snap-20260918-095053.txt`
```

### 步骤2: 输入账号 [✅ success]

```
动作: fill
工具: fill
参数: {
  "value": "admin",
  "uid": "2_5",
  "includeSnapshot": false
}
结果: Successfully filled out the element
执行前快照预览:
## Latest page snapshot
uid=2_0 RootWebArea "登录" url="http://localhost:3002/#/pages/login/index"
  uid=3_0 ignored
    uid=3_1 generic
      uid=3_2 generic
        uid=3_3 ignored
          uid=3_4 i...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Inspection-System-Project\test-result\run-20260918-095049\snapshots\snap-20260918-095102.txt`
```

### 步骤3: 输入密码 [✅ success]

```
动作: fill
工具: fill
参数: {
  "value": "admin123",
  "uid": "2_7",
  "includeSnapshot": false
}
结果: Successfully filled out the element
执行前快照预览:
## Latest page snapshot
uid=2_0 RootWebArea "登录" url="http://localhost:3002/#/pages/login/index"
  uid=3_0 ignored
    uid=3_1 generic
      uid=3_2 generic
        uid=3_3 ignored
          uid=3_4 i...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Inspection-System-Project\test-result\run-20260918-095049\snapshots\snap-20260918-095103.txt`
```

### 步骤4: 读取两个输入框的真实 value（探针核心） [✅ success]

```
动作: execute_script
工具: evaluate_script
参数: {
  "function": "() => { const ins = Array.from(document.querySelectorAll(\"input\")); return \"PROBE_INPUTS=\" + JSON.stringify(ins.map(i => ({type: i.type, value: i.value}))); }"
}
结果: Script ran on page and returned:
```json
"PROBE_INPUTS=[{\"type\":\"text\",\"value\":\"admin\"},{\"type\":\"password\",\"value\":\"admin123\"}]"
```
执行前快照预览:
## Latest page snapshot
uid=2_0 RootWebArea "登录" url="http://localhost:3002/#/pages/login/index"
  uid=3_0 ignored
    uid=3_1 generic
      uid=3_2 generic
        uid=3_3 ignored
          uid=3_4 i...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Inspection-System-Project\test-result\run-20260918-095049\snapshots\snap-20260918-095105.txt`
```

### 步骤5: 点击「登 录」 [✅ success]

```
动作: click
工具: click
参数: {
  "uid": "2_8",
  "includeSnapshot": false
}
结果: Successfully clicked on the element
执行前快照预览:
## Latest page snapshot
uid=2_0 RootWebArea "登录" url="http://localhost:3002/#/pages/login/index"
  uid=3_0 ignored
    uid=3_1 generic
      uid=3_2 generic
        uid=3_3 ignored
          uid=3_4 i...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Inspection-System-Project\test-result\run-20260918-095049\snapshots\snap-20260918-095105.txt`
```

### 步骤6: 读取点击后的 URL 与本地存储键 [✅ success]

```
动作: execute_script
工具: evaluate_script
参数: {
  "function": "() => { const keys = Object.keys(localStorage); const dump = {}; keys.forEach(k => dump[k] = String(localStorage.getItem(k)).slice(0,60)); return \"PROBE_AFTER_CLICK url=\" + location.href + \" localStorage=\" + JSON.stringify(dump); }"
}
结果: Script ran on page and returned:
```json
"PROBE_AFTER_CLICK url=http://localhost:3002/#/ localStorage={\"token\":\"{\\\"tokenInfo\\\":{\\\"token\\\":\\\"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.\",\"eruda-entry-button\":\"{\\\"rememberPos\\\":true,\\\"pos\\\":{\\\"x\\\":1302,\\\"y\\\":569}}\",\"eruda-dev-tools\":\"{\\\"transparency\\\":1,\\\"displaySize\\\":80,\\\"theme\\\":\\\"System preferenc\",\"eruda-console\":\"{\\\"asyncRender\\\":true,\\\"catchGlobalErr\\\":true,\\\"jsExecution\\\":true\",\"eruda-resources\":\"{\\\"hideErudaSetting\\\":true,\\\"observeElement\\\":true}\",\"user\":\"{\\\"use...
执行前快照预览:
## Latest page snapshot
uid=2_0 RootWebArea "若依移动端框架" url="http://localhost:3002/#/"
  uid=18_0 ignored
    uid=18_1 generic
      uid=18_2 generic
        uid=18_3 ignored
          uid=18_4 ignored
...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Inspection-System-Project\test-result\run-20260918-095049\snapshots\snap-20260918-095114.txt`
```

