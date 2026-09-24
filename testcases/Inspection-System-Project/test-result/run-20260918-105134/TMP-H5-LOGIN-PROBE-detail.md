# H5 登录后落点与 token 存储探针（临时诊断用）

- **ID**: `TMP-H5-LOGIN-PROBE`
- **状态**: **PARTIAL** (85.7%)
- **时间**: 2026-09-18 10:51:34
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


快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Inspection-System-Project\test-result\run-20260918-105134\snapshots\snap-20260918-105139.txt`
```

### 步骤2: 输入账号 [✅ success]

```
动作: fill
工具: fill
参数: {
  "value": "admin",
  "uid": "2_188",
  "includeSnapshot": false
}
结果: Successfully filled out the element
执行前快照预览:
## Latest page snapshot
uid=2_0 RootWebArea "登录" url="http://localhost:3002/#/pages/login/index"
  uid=2_1 ignored
    uid=2_2 generic
      uid=2_3 generic
        uid=2_4 ignored
          uid=2_5 i...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Inspection-System-Project\test-result\run-20260918-105134\snapshots\snap-20260918-105145.txt`
```

### 步骤3: 输入密码 [✅ success]

```
动作: fill
工具: fill
参数: {
  "value": "admin123",
  "uid": "2_197",
  "includeSnapshot": false
}
结果: Successfully filled out the element
执行前快照预览:
## Latest page snapshot
uid=2_0 RootWebArea "登录" url="http://localhost:3002/#/pages/login/index"
  uid=2_1 ignored
    uid=2_2 generic
      uid=2_3 generic
        uid=2_4 ignored
          uid=2_5 i...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Inspection-System-Project\test-result\run-20260918-105134\snapshots\snap-20260918-105146.txt`
```

### 步骤4: 点击「登 录」并等待 12s（登录接口实测耗时约 9s） [⚠️ failed_assert]

```
动作: click
工具: click
参数: {
  "uid": "2_201",
  "includeSnapshot": false
}
结果: Successfully clicked on the element
断言:
  ❌ [high] url_contains: /#/pages/index/index → URL contains '/#/pages/index/index': False
执行前快照预览:
## Latest page snapshot
uid=2_0 RootWebArea "若依移动端框架" url="http://localhost:3002/#/"
  uid=2_1 ignored
    uid=2_2 generic
      uid=2_3 generic
        uid=2_4 ignored
          uid=2_5 ignored
     ...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Inspection-System-Project\test-result\run-20260918-105134\snapshots\snap-20260918-105158.txt`
```

### 步骤5: 登录后读取 URL 与 localStorage [✅ success]

```
动作: execute_script
工具: evaluate_script
参数: {
  "function": "() => { const st = {}; try { for (let i = 0; i < localStorage.length; i++) { const k = localStorage.key(i); st[k] = String(localStorage.getItem(k)).slice(0, 60); } } catch (e) { st._err = String(e); } return JSON.stringify({ href: location.href, keys: Object.keys(st), ls: st }); }"
}
结果: Script ran on page and returned:
```json
"{\"href\":\"http://localhost:3002/#/\",\"keys\":[\"token\",\"eruda-entry-button\",\"eruda-dev-tools\",\"eruda-console\",\"eruda-resources\",\"user\",\"eruda-elements\",\"eruda-sources\",\"__DC_STAT_UUID\",\"storage_data\",\"App-Token\"],\"ls\":{\"token\":\"{\\\"tokenInfo\\\":{\\\"token\\\":\\\"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.\",\"eruda-entry-button\":\"{\\\"rememberPos\\\":true,\\\"pos\\\":{\\\"x\\\":1302,\\\"y\\\":569}}\",\"eruda-dev-tools\":\"{\\\"transparency\\\":1,\\\"displaySize\\\":80,\\\"theme\\\":\\\"System preferenc\",\"eruda-console\":\"...
执行前快照预览:
## Latest page snapshot
uid=2_0 RootWebArea "若依移动端框架" url="http://localhost:3002/#/"
  uid=20_0 ignored
    uid=20_1 generic
      uid=20_2 generic
        uid=20_3 ignored
          uid=20_4 ignored
...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Inspection-System-Project\test-result\run-20260918-105134\snapshots\snap-20260918-105202.txt`
```

### 步骤6: 新开标签进入「扫码巡检」页 [✅ success]

```
动作: navigate
工具: new_page
参数: {
  "url": "http://localhost:3002/#/pages/inspect/scan"
}
结果: ## Pages
1: about:blank
2: 若依移动端框架 (http://localhost:3002/#/)
3: 机房巡检 (http://localhost:3002/#/pages/inspect/scan) [selected]
断言:
  ✅ [high] url_contains: /#/pages/inspect/scan → URL contains '/#/pages/inspect/scan': True
执行前快照预览:
## Latest page snapshot
uid=22_0 RootWebArea "机房巡检" url="http://localhost:3002/#/pages/inspect/scan"
  uid=22_1 ignored
    uid=22_2 generic
      uid=22_3 generic
        uid=22_4 ignored
          u...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Inspection-System-Project\test-result\run-20260918-105134\snapshots\snap-20260918-105209.txt`
```

### 步骤7: 读取新标签的 URL 与 localStorage [✅ success]

```
动作: execute_script
工具: evaluate_script
参数: {
  "function": "() => { const st = {}; try { for (let i = 0; i < localStorage.length; i++) { const k = localStorage.key(i); st[k] = String(localStorage.getItem(k)).slice(0, 60); } } catch (e) { st._err = String(e); } return JSON.stringify({ href: location.href, keys: Object.keys(st), ls: st }); }"
}
结果: Script ran on page and returned:
```json
"{\"href\":\"http://localhost:3002/#/pages/inspect/scan\",\"keys\":[\"token\",\"eruda-entry-button\",\"eruda-dev-tools\",\"eruda-console\",\"eruda-resources\",\"user\",\"eruda-elements\",\"eruda-sources\",\"__DC_STAT_UUID\",\"storage_data\",\"App-Token\"],\"ls\":{\"token\":\"{\\\"tokenInfo\\\":{\\\"token\\\":\\\"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.\",\"eruda-entry-button\":\"{\\\"rememberPos\\\":true,\\\"pos\\\":{\\\"x\\\":1302,\\\"y\\\":569}}\",\"eruda-dev-tools\":\"{\\\"transparency\\\":1,\\\"displaySize\\\":80,\\\"theme\\\":\\\"System preferenc\",\"...
执行前快照预览:
## Latest page snapshot
uid=22_0 RootWebArea "机房巡检" url="http://localhost:3002/#/pages/inspect/scan"
  uid=34_0 ignored
    uid=34_1 generic
      uid=34_2 generic
        uid=34_3 ignored
          u...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Inspection-System-Project\test-result\run-20260918-105134\snapshots\snap-20260918-105213.txt`
```

