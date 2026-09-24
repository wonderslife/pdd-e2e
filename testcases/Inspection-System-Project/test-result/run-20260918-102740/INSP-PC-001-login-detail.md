# PC 管理端登录并加载机房巡检菜单

- **ID**: `INSP-PC-001-login`
- **状态**: **PARTIAL** (57.1%)
- **时间**: 2026-09-18 10:27:40
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

### 步骤1: 打开 PC 管理端，进入登录页 [⚠️ failed_assert]

```
动作: navigate
工具: new_page
参数: {
  "url": "http://localhost:80/index"
}
结果: ## Pages
1: about:blank
2: RuoYi-Vue-Plus后台管理系统 (http://localhost/login?redirect=/index) [selected]
断言:
  ❌ [high] text_contains: 欢迎使用 → '欢迎使用' not found in snapshot
执行前快照预览:
## Latest page snapshot
uid=2_0 RootWebArea "RuoYi-Vue-Plus后台管理系统" url="http://localhost/login?redirect=/index"
  uid=2_1 ignored
    uid=2_2 ignored
      uid=2_3 generic
        uid=2_4 ignored
    ...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Inspection-System-Project\test-result\run-20260918-102740\snapshots\snap-20260918-102749.txt`
```

### 步骤2: 在登录表单的「账号」输入框中填入用户名 [✅ success]

```
动作: fill
工具: fill
参数: {
  "value": "admin",
  "uid": "2_62",
  "includeSnapshot": false
}
结果: Successfully filled out the element
断言:
  ✅ [medium] field_filled: 字段已填写 → assume filled (cannot verify via MCP)
执行前快照预览:
## Latest page snapshot
uid=2_0 RootWebArea "RuoYi-Vue-Plus后台管理系统" url="http://localhost/login?redirect=/index"
  uid=7_0 ignored
    uid=7_1 ignored
      uid=7_2 generic
        uid=7_3 ignored
    ...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Inspection-System-Project\test-result\run-20260918-102740\snapshots\snap-20260918-102752.txt`
```

### 步骤3: 在登录表单的「密码」输入框中填入密码 [✅ success]

```
动作: fill
工具: fill
参数: {
  "value": "admin123",
  "uid": "2_73",
  "includeSnapshot": false
}
结果: Successfully filled out the element
断言:
  ✅ [medium] field_filled: 字段已填写 → assume filled (cannot verify via MCP)
执行前快照预览:
## Latest page snapshot
uid=2_0 RootWebArea "RuoYi-Vue-Plus后台管理系统" url="http://localhost/login?redirect=/index"
  uid=7_0 ignored
    uid=7_1 ignored
      uid=7_2 generic
        uid=7_3 ignored
    ...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Inspection-System-Project\test-result\run-20260918-102740\snapshots\snap-20260918-102753.txt`
```

### 步骤4: 点击「登 录」按钮提交 [✅ success]

```
动作: click
工具: click
参数: {
  "uid": "2_49",
  "includeSnapshot": false
}
结果: Successfully clicked on the element
断言:
  ✅ [high] network_called:  → network check skipped (would need network_requests)
  ✅ [high] url_contains: /index → URL contains '/index': True
执行前快照预览:
## Latest page snapshot
uid=2_0 RootWebArea "RuoYi-Vue-Plus后台管理系统" url="http://localhost/login?redirect=/index"
  uid=7_0 ignored
    uid=7_1 ignored
      uid=7_2 generic
        uid=7_3 ignored
    ...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Inspection-System-Project\test-result\run-20260918-102740\snapshots\snap-20260918-102805.txt`
```

### 步骤5: 验证左侧菜单出现一级菜单「机房巡检」 [⚠️ failed_assert]

```
动作: assert_multiple
工具: (assert_multiple)
参数: {}
结果: element_visible=FAIL; element_visible=FAIL
断言:
  ❌ [high] element_visible:  → element '机房巡检' not found
  ❌ [medium] element_visible:  → element '首页' not found
执行前快照预览:
## Latest page snapshot
uid=2_0 RootWebArea "RuoYi-Vue-Plus后台管理系统" url="http://localhost/login?redirect=/index"
  uid=20_0 ignored
    uid=20_1 ignored
      uid=20_2 generic
        uid=20_3 ignored
...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Inspection-System-Project\test-result\run-20260918-102740\snapshots\snap-20260918-102807.txt`
```

### 步骤6: 展开「机房巡检」菜单，验证 7 个二级菜单全部可见 [❌ failed]

```
动作: click
工具: (locate)
参数: {}
错误: 未定位到目标元素: target='机房巡检'（快照中无匹配，请检查页面结构或 target 文案）
重试次数: 3
执行前快照预览:
## Latest page snapshot
uid=2_0 RootWebArea "RuoYi-Vue-Plus后台管理系统" url="http://localhost/login?redirect=/index"
  uid=20_0 ignored
    uid=20_1 ignored
      uid=20_2 generic
        uid=20_3 ignored
...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Inspection-System-Project\test-result\run-20260918-102740\snapshots\snap-20260918-102814.txt`
```

### 步骤7: 点击「机房管理」进入列表页，确认列表接口被调用 [✅ success]

```
动作: click
工具: click
参数: {
  "uid": "2_51",
  "includeSnapshot": false
}
结果: Successfully clicked on the element
断言:
  ✅ [high] network_called:  → network check skipped (would need network_requests)
  ✅ [high] element_visible:  → element '机房名称' found
执行前快照预览:
## Latest page snapshot
uid=2_0 RootWebArea "RuoYi-Vue-Plus后台管理系统" url="http://localhost/login?redirect=/index"
  uid=30_0 ignored
    uid=30_1 ignored
      uid=30_2 generic
        uid=30_3 ignored
...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Inspection-System-Project\test-result\run-20260918-102740\snapshots\snap-20260918-102819.txt`
```

