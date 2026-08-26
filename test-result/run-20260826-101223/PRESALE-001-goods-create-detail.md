# 商家创建预售商品正常流程（含演示控件+多选）

- **ID**: `PRESALE-001-goods-create`
- **状态**: **PASS** (100.0%)
- **时间**: 2026-08-26 10:12:23
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

### 步骤1: 打开登录页面 [✅ success]

```
动作: navigate
工具: new_page
参数: {
  "url": "http://localhost/login"
}
结果: ## Pages
1: about:blank
2: RuoYi-Vue-Plus后台管理系统 (http://localhost/login) [selected]
断言:
  ✅ [medium] text_contains: 登录 → '登录' found in snapshot
执行前快照预览:
## Latest page snapshot
uid=2_0 RootWebArea "RuoYi-Vue-Plus后台管理系统" url="http://localhost/login"
  uid=2_1 ignored
    uid=2_2 ignored
      uid=2_3 generic
        uid=2_4 ignored
          uid=2_5 ig...
快照文件: `D:\APPPROJECTS\pdd-test-system\test-result\run-20260826-101223\snapshots\snap-20260826-101230.txt`
```

### 步骤2: 等待登录页渲染完成（SPA 首次加载可能较慢） [✅ success]

```
动作: wait_for
工具: wait_for
参数: {
  "text": [
    "登 录"
  ],
  "timeout": 10000
}
结果: Element matching one of ["登 录"] found.
## Latest page snapshot
uid=2_0 RootWebArea "RuoYi-Vue-Plus后台管理系统" url="http://localhost/login"
  uid=2_8 StaticText "PLUS UI WORKSPACE"
  uid=2_10 heading "企业级后台管理系统" level="1"
  uid=2_13 StaticText "真正面向企业级的应用框架 组件化 模块化 轻耦合 高扩展 针对企业痛点 业界一流技术栈"
  uid=2_14 LineBreak "
"
  uid=2_15 StaticText "重写 RuoYi-Vue 所有功能 集成 Sa-Token、Mybatis-Plus、WarmFlow、SpringDoc、Hutool、OSS 定期同步。"
  uid=2_18 StaticText "技术栈全面升级"
  uid=2_20 StaticText "动态菜单"
  uid=2_22 StaticText "多主题布局"
  uid=2_24 StaticText "深浅色主题"
  uid=2_28 StaticText "动态权限控制"
  uid=2_30 StaticText "细粒度权限管理"
  u...
执行前快照预览:
## Latest page snapshot
uid=2_0 RootWebArea "RuoYi-Vue-Plus后台管理系统" url="http://localhost/login"
  uid=8_0 ignored
    uid=8_1 ignored
      uid=8_2 generic
        uid=8_3 ignored
          uid=8_4 ig...
快照文件: `D:\APPPROJECTS\pdd-test-system\test-result\run-20260826-101223\snapshots\snap-20260826-101234.txt`
```

### 步骤3: 输入用户名 [✅ success]

```
动作: fill
工具: fill
参数: {
  "value": "admin",
  "uid": "2_62",
  "includeSnapshot": false
}
结果: Successfully filled out the element
执行前快照预览:
## Latest page snapshot
uid=2_0 RootWebArea "RuoYi-Vue-Plus后台管理系统" url="http://localhost/login"
  uid=10_0 ignored
    uid=10_1 ignored
      uid=10_2 generic
        uid=10_3 ignored
          uid=10...
快照文件: `D:\APPPROJECTS\pdd-test-system\test-result\run-20260826-101223\snapshots\snap-20260826-101235.txt`
```

### 步骤4: 输入密码 [✅ success]

```
动作: fill
工具: fill
参数: {
  "value": "admin123",
  "uid": "2_73",
  "includeSnapshot": false
}
结果: Successfully filled out the element
执行前快照预览:
## Latest page snapshot
uid=2_0 RootWebArea "RuoYi-Vue-Plus后台管理系统" url="http://localhost/login"
  uid=10_0 ignored
    uid=10_1 ignored
      uid=10_2 generic
        uid=10_3 ignored
          uid=10...
快照文件: `D:\APPPROJECTS\pdd-test-system\test-result\run-20260826-101223\snapshots\snap-20260826-101236.txt`
```

### 步骤5: 点击登录按钮 [✅ success]

```
动作: click
工具: click
参数: {
  "uid": "2_86",
  "includeSnapshot": false
}
结果: Successfully clicked on the element
执行前快照预览:
## Latest page snapshot
uid=2_0 RootWebArea "RuoYi-Vue-Plus后台管理系统" url="http://localhost/login"
  uid=10_0 ignored
    uid=10_1 ignored
      uid=10_2 generic
        uid=10_3 ignored
          uid=10...
快照文件: `D:\APPPROJECTS\pdd-test-system\test-result\run-20260826-101223\snapshots\snap-20260826-101238.txt`
```

### 步骤6: 打开预售商品列表页 [✅ success]

```
动作: navigate
工具: new_page
参数: {
  "url": "http://localhost/presale/goods"
}
结果: ## Pages
1: about:blank
2: 首页 - RuoYi-Vue-Plus后台管理系统 (http://localhost/login)
3: RuoYi-Vue-Plus后台管理系统 (http://localhost/presale/goods) [selected]
断言:
  ✅ [medium] text_contains: 预售商品 → '预售商品' found in snapshot
执行前快照预览:
## Latest page snapshot
uid=20_0 RootWebArea "预售商品管理 - RuoYi-Vue-Plus后台管理系统" url="http://localhost/presale/goods"
  uid=20_1 ignored
    uid=20_2 ignored
      uid=20_3 generic
        uid=26_0 generi...
快照文件: `D:\APPPROJECTS\pdd-test-system\test-result\run-20260826-101223\snapshots\snap-20260826-101248.txt`
```

### 步骤7: 点击新增按钮 [✅ success]

```
动作: click
工具: click
参数: {
  "uid": "26_236",
  "includeSnapshot": false
}
结果: Successfully clicked on the element
执行前快照预览:
## Latest page snapshot
uid=20_0 RootWebArea "预售商品管理 - RuoYi-Vue-Plus后台管理系统" url="http://localhost/presale/goods"
  uid=36_0 ignored
    uid=36_1 ignored
      uid=36_2 generic
        uid=36_3 generi...
快照文件: `D:\APPPROJECTS\pdd-test-system\test-result\run-20260826-101223\snapshots\snap-20260826-101249.txt`
```

### 步骤8: 等待新增弹窗渲染完成 [✅ success]

```
动作: wait_for
工具: wait_for
参数: {
  "text": [
    "商品标题"
  ],
  "timeout": 10000
}
结果: Element matching one of ["商品标题"] found.
## Latest page snapshot
uid=20_0 RootWebArea "预售商品管理 - RuoYi-Vue-Plus后台管理系统" url="http://localhost/presale/goods"
  uid=26_3 link "RuoYi-Vue-Plus" url="http://localhost/"
    uid=26_5 heading "RuoYi-Vue-Plus" level="1"
  uid=26_11 menubar orientation="horizontal"
    uid=26_13 link "首页" url="http://localhost/index"
      uid=26_14 menuitem "首页"
    uid=26_19 menuitem "系统管理" expandable
    uid=26_42 menuitem "系统监控" expandable
    uid=26_56 menuitem "系统工具" expandable
    uid=26_66 menuitem "测试菜单" expandable
    uid=26_75 menuitem "预售管理" expandable expanded...
执行前快照预览:
## Latest page snapshot
uid=20_0 RootWebArea "预售商品管理 - RuoYi-Vue-Plus后台管理系统" url="http://localhost/presale/goods"
  uid=41_0 ignored
    uid=41_1 ignored
      uid=41_2 generic
        uid=41_3 generi...
快照文件: `D:\APPPROJECTS\pdd-test-system\test-result\run-20260826-101223\snapshots\snap-20260826-101252.txt`
```

### 步骤9: 输入商品标题 [✅ success]

```
动作: fill
工具: fill
参数: {
  "value": "E2E测试预售商品-定金20元",
  "uid": "38_8",
  "includeSnapshot": false
}
结果: Successfully filled out the element
执行前快照预览:
## Latest page snapshot
uid=20_0 RootWebArea "预售商品管理 - RuoYi-Vue-Plus后台管理系统" url="http://localhost/presale/goods"
  uid=43_0 ignored
    uid=43_1 ignored
      uid=43_2 generic
        uid=43_3 generi...
快照文件: `D:\APPPROJECTS\pdd-test-system\test-result\run-20260826-101223\snapshots\snap-20260826-101254.txt`
```

### 步骤10: 输入售价 [✅ success]

```
动作: fill
工具: fill
参数: {
  "value": "100",
  "uid": "38_13",
  "includeSnapshot": false
}
结果: Successfully filled out the element
执行前快照预览:
## Latest page snapshot
uid=20_0 RootWebArea "预售商品管理 - RuoYi-Vue-Plus后台管理系统" url="http://localhost/presale/goods"
  uid=43_0 ignored
    uid=43_1 ignored
      uid=43_2 generic
        uid=43_3 generi...
快照文件: `D:\APPPROJECTS\pdd-test-system\test-result\run-20260826-101223\snapshots\snap-20260826-101255.txt`
```

### 步骤11: 输入定金金额 [✅ success]

```
动作: fill
工具: fill
参数: {
  "value": "20",
  "uid": "38_18",
  "includeSnapshot": false
}
结果: Successfully filled out the element
执行前快照预览:
## Latest page snapshot
uid=20_0 RootWebArea "预售商品管理 - RuoYi-Vue-Plus后台管理系统" url="http://localhost/presale/goods"
  uid=43_0 ignored
    uid=43_1 ignored
      uid=43_2 generic
        uid=43_3 generi...
快照文件: `D:\APPPROJECTS\pdd-test-system\test-result\run-20260826-101223\snapshots\snap-20260826-101256.txt`
```

### 步骤12: 输入尾款金额 [✅ success]

```
动作: fill
工具: fill
参数: {
  "value": "80",
  "uid": "38_23",
  "includeSnapshot": false
}
结果: Successfully filled out the element
执行前快照预览:
## Latest page snapshot
uid=20_0 RootWebArea "预售商品管理 - RuoYi-Vue-Plus后台管理系统" url="http://localhost/presale/goods"
  uid=43_0 ignored
    uid=43_1 ignored
      uid=43_2 generic
        uid=43_3 generi...
快照文件: `D:\APPPROJECTS\pdd-test-system\test-result\run-20260826-101223\snapshots\snap-20260826-101257.txt`
```

### 步骤13: 选择预售截止时间（7天后） [✅ success]

```
动作: el_date
工具: (el_date)
参数: {
  "target": "预售截止时间",
  "value": "2026-08-31 23:59:59"
}
结果: Date filled successfully: 2026-08-31 23:59:59
Sub-steps: [1/3] 点击日期输入框: ✅ | [2/3] 等待日期面板渲染 (800ms): ✅ | [3/3] 填入日期值: ✅
执行前快照预览:
## Latest page snapshot
uid=20_0 RootWebArea "预售商品管理 - RuoYi-Vue-Plus后台管理系统" url="http://localhost/presale/goods"
  uid=43_0 ignored
    uid=43_1 ignored
      uid=43_2 generic
        uid=43_3 generi...
快照文件: `D:\APPPROJECTS\pdd-test-system\test-result\run-20260826-101223\snapshots\snap-20260826-101259.txt`
```

### 步骤14: 输入限购数量 [✅ success]

```
动作: fill
工具: fill
参数: {
  "value": "5",
  "uid": "38_31",
  "includeSnapshot": false
}
结果: Successfully filled out the element
执行前快照预览:
## Latest page snapshot
uid=20_0 RootWebArea "预售商品管理 - RuoYi-Vue-Plus后台管理系统" url="http://localhost/presale/goods"
  uid=43_0 ignored
    uid=43_1 ignored
      uid=43_2 generic
        uid=43_3 generi...
快照文件: `D:\APPPROJECTS\pdd-test-system\test-result\run-20260826-101223\snapshots\snap-20260826-101300.txt`
```

### 步骤15: 输入库存 [✅ success]

```
动作: fill
工具: fill
参数: {
  "value": "10",
  "uid": "38_36",
  "includeSnapshot": false
}
结果: Successfully filled out the element
执行前快照预览:
## Latest page snapshot
uid=20_0 RootWebArea "预售商品管理 - RuoYi-Vue-Plus后台管理系统" url="http://localhost/presale/goods"
  uid=43_0 ignored
    uid=43_1 ignored
      uid=43_2 generic
        uid=43_3 generi...
快照文件: `D:\APPPROJECTS\pdd-test-system\test-result\run-20260826-101223\snapshots\snap-20260826-101301.txt`
```

### 步骤16: 输入密码框（el-input password，不入库） [✅ success]

```
动作: fill
工具: fill
参数: {
  "value": "test123456",
  "uid": "38_39",
  "includeSnapshot": false
}
结果: Successfully filled out the element
执行前快照预览:
## Latest page snapshot
uid=20_0 RootWebArea "预售商品管理 - RuoYi-Vue-Plus后台管理系统" url="http://localhost/presale/goods"
  uid=43_0 ignored
    uid=43_1 ignored
      uid=43_2 generic
        uid=43_3 generi...
快照文件: `D:\APPPROJECTS\pdd-test-system\test-result\run-20260826-101223\snapshots\snap-20260826-101303.txt`
```

### 步骤17: 输入邮箱（el-input 带图标，不入库） [✅ success]

```
动作: fill
工具: fill
参数: {
  "value": "test@demo.com",
  "uid": "38_42",
  "includeSnapshot": false
}
结果: Successfully filled out the element
执行前快照预览:
## Latest page snapshot
uid=20_0 RootWebArea "预售商品管理 - RuoYi-Vue-Plus后台管理系统" url="http://localhost/presale/goods"
  uid=43_0 ignored
    uid=43_1 ignored
      uid=43_2 generic
        uid=43_3 generi...
快照文件: `D:\APPPROJECTS\pdd-test-system\test-result\run-20260826-101223\snapshots\snap-20260826-101304.txt`
```

### 步骤18: 输入手机号（el-input 限长，不入库） [✅ success]

```
动作: fill
工具: fill
参数: {
  "value": "13800138000",
  "uid": "38_45",
  "includeSnapshot": false
}
结果: Successfully filled out the element
执行前快照预览:
## Latest page snapshot
uid=20_0 RootWebArea "预售商品管理 - RuoYi-Vue-Plus后台管理系统" url="http://localhost/presale/goods"
  uid=43_0 ignored
    uid=43_1 ignored
      uid=43_2 generic
        uid=43_3 generi...
快照文件: `D:\APPPROJECTS\pdd-test-system\test-result\run-20260826-101223\snapshots\snap-20260826-101305.txt`
```

### 步骤19: 输入商品描述（el-input textarea，不入库） [✅ success]

```
动作: fill
工具: fill
参数: {
  "value": "E2E 文本域测试内容",
  "uid": "38_48",
  "includeSnapshot": false
}
结果: Successfully filled out the element
执行前快照预览:
## Latest page snapshot
uid=20_0 RootWebArea "预售商品管理 - RuoYi-Vue-Plus后台管理系统" url="http://localhost/presale/goods"
  uid=43_0 ignored
    uid=43_1 ignored
      uid=43_2 generic
        uid=43_3 generi...
快照文件: `D:\APPPROJECTS\pdd-test-system\test-result\run-20260826-101223\snapshots\snap-20260826-101306.txt`
```

### 步骤20: 选择商品分类（el-select 单选可搜索，不入库） [✅ success]

```
动作: select_option
工具: readonly_picker
参数: {
  "value": "数码家电",
  "uid": "38_52",
  "includeSnapshot": false
}
结果: {'type': 'text', 'text': "picker selected '数码家电' via DOM click"}
执行前快照预览:
## Latest page snapshot
uid=20_0 RootWebArea "预售商品管理 - RuoYi-Vue-Plus后台管理系统" url="http://localhost/presale/goods"
  uid=43_0 ignored
    uid=43_1 ignored
      uid=43_2 generic
        uid=43_3 generi...
快照文件: `D:\APPPROJECTS\pdd-test-system\test-result\run-20260826-101223\snapshots\snap-20260826-101307.txt`
```

### 步骤21: 选择品牌（el-select 单选，不入库） [✅ success]

```
动作: select_option
工具: readonly_picker
参数: {
  "value": "华为",
  "uid": "38_64",
  "includeSnapshot": false
}
结果: {'type': 'text', 'text': "picker selected '华为' via DOM click"}
执行前快照预览:
## Latest page snapshot
uid=20_0 RootWebArea "预售商品管理 - RuoYi-Vue-Plus后台管理系统" url="http://localhost/presale/goods"
  uid=43_0 ignored
    uid=43_1 ignored
      uid=43_2 generic
        uid=43_3 generi...
快照文件: `D:\APPPROJECTS\pdd-test-system\test-result\run-20260826-101223\snapshots\snap-20260826-101311.txt`
```

### 步骤22: 选择商品标签-第一个（el-select multiple 多选下拉，不入库） [✅ success]

```
动作: select_option
工具: readonly_picker
参数: {
  "value": "预售",
  "uid": "38_56",
  "includeSnapshot": false
}
结果: {'type': 'text', 'text': "picker selected '预售' via DOM click"}
执行前快照预览:
## Latest page snapshot
uid=20_0 RootWebArea "预售商品管理 - RuoYi-Vue-Plus后台管理系统" url="http://localhost/presale/goods"
  uid=43_0 ignored
    uid=43_1 ignored
      uid=43_2 generic
        uid=43_3 generi...
快照文件: `D:\APPPROJECTS\pdd-test-system\test-result\run-20260826-101223\snapshots\snap-20260826-101315.txt`
```

### 步骤23: 选择商品标签-第二个（el-select multiple 多选验证，不入库） [✅ success]

```
动作: select_option
工具: readonly_picker
参数: {
  "value": "限量",
  "uid": "38_56",
  "includeSnapshot": false
}
结果: {'type': 'text', 'text': "picker selected '限量' via DOM click"}
执行前快照预览:
## Latest page snapshot
uid=20_0 RootWebArea "预售商品管理 - RuoYi-Vue-Plus后台管理系统" url="http://localhost/presale/goods"
  uid=43_0 ignored
    uid=43_1 ignored
      uid=43_2 generic
        uid=43_3 generi...
快照文件: `D:\APPPROJECTS\pdd-test-system\test-result\run-20260826-101223\snapshots\snap-20260826-101318.txt`
```

### 步骤24: 选择配送方式（el-radio，不入库） [✅ success]

```
动作: click
工具: click
参数: {
  "uid": "38_67",
  "includeSnapshot": false
}
结果: Successfully clicked on the element
执行前快照预览:
## Latest page snapshot
uid=20_0 RootWebArea "预售商品管理 - RuoYi-Vue-Plus后台管理系统" url="http://localhost/presale/goods"
  uid=43_0 ignored
    uid=43_1 ignored
      uid=43_2 generic
        uid=43_3 generi...
快照文件: `D:\APPPROJECTS\pdd-test-system\test-result\run-20260826-101223\snapshots\snap-20260826-101322.txt`
```

### 步骤25: 勾选服务保障-第一个（el-checkbox，不入库） [✅ success]

```
动作: click
工具: click
参数: {
  "uid": "38_76",
  "includeSnapshot": false
}
结果: [dom-fallback] Script ran on page and returned:
```json
"clicked-widget: el-checkbox el-checkbox--default"
```
执行前快照预览:
## Latest page snapshot
uid=20_0 RootWebArea "预售商品管理 - RuoYi-Vue-Plus后台管理系统" url="http://localhost/presale/goods"
  uid=78_0 ignored
    uid=78_1 ignored
      uid=78_2 generic
        uid=78_3 generi...
快照文件: `D:\APPPROJECTS\pdd-test-system\test-result\run-20260826-101223\snapshots\snap-20260826-101325.txt`
```

### 步骤26: 勾选服务保障-第二个（el-checkbox 多选验证，不入库） [✅ success]

```
动作: click
工具: click
参数: {
  "uid": "38_74",
  "includeSnapshot": false
}
结果: [dom-fallback] Script ran on page and returned:
```json
"clicked-widget: el-checkbox el-checkbox--default"
```
执行前快照预览:
## Latest page snapshot
uid=20_0 RootWebArea "预售商品管理 - RuoYi-Vue-Plus后台管理系统" url="http://localhost/presale/goods"
  uid=83_0 ignored
    uid=83_1 ignored
      uid=83_2 generic
        uid=83_3 generi...
快照文件: `D:\APPPROJECTS\pdd-test-system\test-result\run-20260826-101223\snapshots\snap-20260826-101332.txt`
```

### 步骤27: 切换上架状态（el-switch，不入库） [✅ success]

```
动作: click
工具: click
参数: {
  "uid": "38_82",
  "includeSnapshot": false
}
结果: [dom-fallback] Script ran on page and returned:
```json
"clicked-form-item: el-switch el-switch--default is-checked"
```
执行前快照预览:
## Latest page snapshot
uid=20_0 RootWebArea "预售商品管理 - RuoYi-Vue-Plus后台管理系统" url="http://localhost/presale/goods"
  uid=88_0 ignored
    uid=88_1 ignored
      uid=88_2 generic
        uid=88_3 generi...
快照文件: `D:\APPPROJECTS\pdd-test-system\test-result\run-20260826-101223\snapshots\snap-20260826-101340.txt`
```

### 步骤28: 点击商品评分（el-rate，不入库） [✅ success]

```
动作: click
工具: click
参数: {
  "uid": "38_93",
  "includeSnapshot": false
}
结果: Successfully clicked on the element
执行前快照预览:
## Latest page snapshot
uid=20_0 RootWebArea "预售商品管理 - RuoYi-Vue-Plus后台管理系统" url="http://localhost/presale/goods"
  uid=93_0 ignored
    uid=93_1 ignored
      uid=93_2 generic
        uid=93_3 generi...
快照文件: `D:\APPPROJECTS\pdd-test-system\test-result\run-20260826-101223\snapshots\snap-20260826-101347.txt`
```

### 步骤29: 选择上架日期（el-date-picker date，不入库） [✅ success]

```
动作: el_date
工具: (el_date)
参数: {
  "target": "上架日期",
  "value": "2026-08-25"
}
结果: Date filled successfully: 2026-08-25
Sub-steps: [1/3] 点击日期输入框: ✅ | [2/3] 等待日期面板渲染 (800ms): ✅ | [3/3] 填入日期值: ✅
执行前快照预览:
## Latest page snapshot
uid=20_0 RootWebArea "预售商品管理 - RuoYi-Vue-Plus后台管理系统" url="http://localhost/presale/goods"
  uid=98_0 ignored
    uid=98_1 ignored
      uid=98_2 generic
        uid=98_3 generi...
快照文件: `D:\APPPROJECTS\pdd-test-system\test-result\run-20260826-101223\snapshots\snap-20260826-101351.txt`
```

### 步骤30: 选择每日开售时间（el-time-picker，不入库） [✅ success]

```
动作: el_date
工具: (el_date)
参数: {
  "target": "每日开售时间",
  "value": "09:30:00"
}
结果: Date filled successfully: 09:30:00
Sub-steps: [1/3] 点击日期输入框: ✅ | [2/3] 等待日期面板渲染 (800ms): ✅ | [3/3] 填入日期值: ✅
执行前快照预览:
## Latest page snapshot
uid=20_0 RootWebArea "预售商品管理 - RuoYi-Vue-Plus后台管理系统" url="http://localhost/presale/goods"
  uid=98_0 ignored
    uid=98_1 ignored
      uid=98_2 generic
        uid=98_3 generi...
快照文件: `D:\APPPROJECTS\pdd-test-system\test-result\run-20260826-101223\snapshots\snap-20260826-101353.txt`
```

### 步骤31: 选择预售开始时间（el-date-picker datetime，不入库） [✅ success]

```
动作: el_date
工具: (el_date)
参数: {
  "target": "预售开始时间",
  "value": "2026-08-25 00:00:00"
}
结果: Date filled successfully: 2026-08-25 00:00:00
Sub-steps: [1/3] 点击日期输入框: ✅ | [2/3] 等待日期面板渲染 (800ms): ✅ | [3/3] 填入日期值: ✅
执行前快照预览:
## Latest page snapshot
uid=20_0 RootWebArea "预售商品管理 - RuoYi-Vue-Plus后台管理系统" url="http://localhost/presale/goods"
  uid=98_0 ignored
    uid=98_1 ignored
      uid=98_2 generic
        uid=98_3 generi...
快照文件: `D:\APPPROJECTS\pdd-test-system\test-result\run-20260826-101223\snapshots\snap-20260826-101355.txt`
```

### 步骤32: 上传商品主图（ImageUpload/el-upload，不入库） [✅ success]

```
动作: el_upload
工具: (el_upload)
参数: {
  "target": "商品主图",
  "filePath": "D:\\APPPROJECTS\\pdd-test-system\\testcases\\frontend\\assets\\test-upload.png"
}
结果: File uploaded successfully: D:\APPPROJECTS\pdd-test-system\testcases\frontend\assets\test-upload.png
Sub-steps: [1/3] 点击上传按钮: ✅ | [2/3] 暴露隐藏的文件输入框: ✅ | [3/3] 执行文件上传: ✅ | [4/3] 跳过关闭文件对话框(Escape 会误关 el-dialog): ✅(skip, CDP注入无OS对话框)
执行前快照预览:
## Latest page snapshot
uid=20_0 RootWebArea "预售商品管理 - RuoYi-Vue-Plus后台管理系统" url="http://localhost/presale/goods"
  uid=98_0 ignored
    uid=98_1 ignored
      uid=98_2 generic
        uid=98_3 generi...
快照文件: `D:\APPPROJECTS\pdd-test-system\test-result\run-20260826-101223\snapshots\snap-20260826-101358.txt`
```

### 步骤33: 确认弹窗仍打开（防止弹窗意外关闭后错点其他按钮） [✅ success]

```
动作: wait_for
工具: wait_for
参数: {
  "text": [
    "确 定"
  ],
  "timeout": 10000
}
结果: Element matching one of ["确 定"] found.
## Latest page snapshot
uid=20_0 RootWebArea "预售商品管理 - RuoYi-Vue-Plus后台管理系统" url="http://localhost/presale/goods"
  uid=26_3 link "RuoYi-Vue-Plus" url="http://localhost/"
    uid=26_5 heading "RuoYi-Vue-Plus" level="1"
  uid=26_11 menubar orientation="horizontal"
    uid=26_13 link "首页" url="http://localhost/index"
      uid=26_14 menuitem "首页"
    uid=26_19 menuitem "系统管理" expandable
    uid=26_42 menuitem "系统监控" expandable
    uid=26_56 menuitem "系统工具" expandable
    uid=26_66 menuitem "测试菜单" expandable
    uid=26_75 menuitem "预售管理" expandable expanded
...
执行前快照预览:
## Latest page snapshot
uid=20_0 RootWebArea "预售商品管理 - RuoYi-Vue-Plus后台管理系统" url="http://localhost/presale/goods"
  uid=98_0 ignored
    uid=98_1 ignored
      uid=98_2 generic
        uid=98_3 generi...
快照文件: `D:\APPPROJECTS\pdd-test-system\test-result\run-20260826-101223\snapshots\snap-20260826-101401.txt`
```

### 步骤34: 提交表单 [✅ success]

```
动作: click
工具: click
参数: {
  "uid": "38_114",
  "includeSnapshot": false
}
结果: Successfully clicked on the element
断言:
  ✅ [high] toast_visible: 新增成功 → LiveToast: 'Script ran on page and returned:
```json
"新增成功"
```'
执行前快照预览:
## Latest page snapshot
uid=20_0 RootWebArea "预售商品管理 - RuoYi-Vue-Plus后台管理系统" url="http://localhost/presale/goods"
  uid=109_0 ignored
    uid=109_1 ignored
      uid=109_2 generic
        uid=109_3 ge...
快照文件: `D:\APPPROJECTS\pdd-test-system\test-result\run-20260826-101223\snapshots\snap-20260826-101404.txt`
```

### 步骤35: 校验网络请求成功（铁律3：UI+网络双重校验） [✅ success]

```
动作: verify_network
工具: list_network_requests
参数: {}
结果: Network matched 1: POST http://localhost/dev-api/presale/goods -> 200
```

### 步骤36: 确认列表出现新商品 [✅ success]

```
动作: wait_for
工具: wait_for
参数: {
  "text": [
    "E2E测试预售商品-定金20元"
  ],
  "timeout": 10000
}
结果: Element matching one of ["E2E测试预售商品-定金20元"] found.
## Latest page snapshot
uid=20_0 RootWebArea "预售商品管理 - RuoYi-Vue-Plus后台管理系统" url="http://localhost/presale/goods"
  uid=26_3 link "RuoYi-Vue-Plus" url="http://localhost/"
    uid=26_5 heading "RuoYi-Vue-Plus" level="1"
  uid=26_11 menubar orientation="horizontal"
    uid=26_13 link "首页" url="http://localhost/index"
      uid=26_14 menuitem "首页"
    uid=26_19 menuitem "系统管理" expandable
    uid=26_42 menuitem "系统监控" expandable
    uid=26_56 menuitem "系统工具" expandable
    uid=26_66 menuitem "测试菜单" expandable
    uid=26_75 menuitem "预售管理" expandab...
断言:
  ✅ [medium] text_contains: E2E测试预售商品-定金20元 → 'E2E测试预售商品-定金20元' found in snapshot
执行前快照预览:
## Latest page snapshot
uid=20_0 RootWebArea "预售商品管理 - RuoYi-Vue-Plus后台管理系统" url="http://localhost/presale/goods"
  uid=122_0 ignored
    uid=122_1 ignored
      uid=122_2 generic
        uid=122_3 ge...
快照文件: `D:\APPPROJECTS\pdd-test-system\test-result\run-20260826-101223\snapshots\snap-20260826-101409.txt`
```

