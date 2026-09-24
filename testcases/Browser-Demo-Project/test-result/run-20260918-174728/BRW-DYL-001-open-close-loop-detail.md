# 浏览器稳定性 - 抖音视频页 打开/停留/关闭 循环 10 次

- **ID**: `BRW-DYL-001-open-close-loop`
- **状态**: **PASS** (100.0%)
- **时间**: 2026-09-18 17:47:28
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

### 步骤1: [第 1/10 轮] 打开视频页（新标签页）并停留 [✅ success]

```
动作: navigate
工具: new_page
参数: {
  "url": "https://www.douyin.com/video/6611776156595129614",
  "timeout": 30000
}
结果: ## Pages
1: about:blank
2: https://www.douyin.com/video/6611776156595129614 [selected]
断言:
  ✅ [high] url_contains: douyin.com → URL contains 'douyin.com': True
  ✅ [medium] url_contains: 6611776156595129614 → URL contains '6611776156595129614': True
  ✅ [medium] page_title: 抖音 → Page title contains '抖音': True
执行前快照预览:
## Latest page snapshot
uid=2_0 RootWebArea "火柴人超炫手翻画 - 抖音" url="https://www.douyin.com/video/6611776156595129614"
  uid=2_1 ignored
    uid=2_2 generic
      uid=2_3 button "开启读屏标签"
        uid=2_4 S...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Browser-Demo-Project\test-result\run-20260918-174728\snapshots\snap-20260918-174754.txt`
```

### 步骤2: [第 1/10 轮] 关闭该标签页 [✅ success]

```
动作: close_page
工具: close_page
参数: {
  "pageId": 2
}
结果: Note: the previously selected page was closed. Page 1 is now selected.
## Pages
1: about:blank [selected]
执行前快照预览:
## Latest page snapshot
uid=2_0 RootWebArea "火柴人超炫手翻画 - 抖音" url="https://www.douyin.com/video/6611776156595129614"
  uid=2_1 ignored
    uid=2_2 generic
      uid=2_3 button "开启读屏标签"
        uid=2_4 S...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Browser-Demo-Project\test-result\run-20260918-174728\snapshots\snap-20260918-174754.txt`
```

### 步骤3: [第 2/10 轮] 打开视频页（新标签页）并停留 [✅ success]

```
动作: navigate
工具: new_page
参数: {
  "url": "https://www.douyin.com/video/6611776156595129614",
  "timeout": 30000
}
结果: ## Pages
1: about:blank
3: 火柴人超炫手翻画 - 抖音 (https://www.douyin.com/video/6611776156595129614) [selected]
断言:
  ✅ [high] url_contains: douyin.com → URL contains 'douyin.com': True
  ✅ [medium] url_contains: 6611776156595129614 → URL contains '6611776156595129614': True
  ✅ [medium] page_title: 抖音 → Page title contains '抖音': True
执行前快照预览:
## Latest page snapshot
uid=9_0 RootWebArea "火柴人超炫手翻画 - 抖音" url="https://www.douyin.com/video/6611776156595129614"
  uid=9_1 ignored
    uid=9_2 generic
      uid=9_3 button "开启读屏标签"
        uid=9_4 S...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Browser-Demo-Project\test-result\run-20260918-174728\snapshots\snap-20260918-174818.txt`
```

### 步骤4: [第 2/10 轮] 关闭该标签页 [✅ success]

```
动作: close_page
工具: close_page
参数: {
  "pageId": 3
}
结果: Note: the previously selected page was closed. Page 1 is now selected.
## Pages
1: about:blank [selected]
执行前快照预览:
## Latest page snapshot
uid=9_0 RootWebArea "火柴人超炫手翻画 - 抖音" url="https://www.douyin.com/video/6611776156595129614"
  uid=17_0 ignored
    uid=17_1 generic
      uid=9_3 button "开启读屏标签"
        uid=17_...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Browser-Demo-Project\test-result\run-20260918-174728\snapshots\snap-20260918-174819.txt`
```

### 步骤5: [第 3/10 轮] 打开视频页（新标签页）并停留 [✅ success]

```
动作: navigate
工具: new_page
参数: {
  "url": "https://www.douyin.com/video/6611776156595129614",
  "timeout": 30000
}
结果: ## Pages
1: about:blank
4: https://www.douyin.com/video/6611776156595129614 [selected]
断言:
  ✅ [high] url_contains: douyin.com → URL contains 'douyin.com': True
  ✅ [medium] url_contains: 6611776156595129614 → URL contains '6611776156595129614': True
  ✅ [medium] page_title: 抖音 → Page title contains '抖音': True
执行前快照预览:
## Latest page snapshot
uid=19_0 RootWebArea "火柴人超炫手翻画 - 抖音" url="https://www.douyin.com/video/6611776156595129614"
  uid=19_1 ignored
    uid=19_2 generic
      uid=19_3 button "开启读屏标签"
        uid=1...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Browser-Demo-Project\test-result\run-20260918-174728\snapshots\snap-20260918-174834.txt`
```

### 步骤6: [第 3/10 轮] 关闭该标签页 [✅ success]

```
动作: close_page
工具: close_page
参数: {
  "pageId": 4
}
结果: Note: the previously selected page was closed. Page 1 is now selected.
## Pages
1: about:blank [selected]
执行前快照预览:
## Latest page snapshot
uid=19_0 RootWebArea "火柴人超炫手翻画 - 抖音" url="https://www.douyin.com/video/6611776156595129614"
  uid=27_0 ignored
    uid=27_1 generic
      uid=19_3 button "开启读屏标签"
        uid=2...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Browser-Demo-Project\test-result\run-20260918-174728\snapshots\snap-20260918-174835.txt`
```

### 步骤7: [第 4/10 轮] 打开视频页（新标签页）并停留 [✅ success]

```
动作: navigate
工具: new_page
参数: {
  "url": "https://www.douyin.com/video/6611776156595129614",
  "timeout": 30000
}
结果: ## Pages
1: about:blank
5: 火柴人超炫手翻画 - 抖音 (https://www.douyin.com/video/6611776156595129614) [selected]
断言:
  ✅ [high] url_contains: douyin.com → URL contains 'douyin.com': True
  ✅ [medium] url_contains: 6611776156595129614 → URL contains '6611776156595129614': True
  ✅ [medium] page_title: 抖音 → Page title contains '抖音': True
执行前快照预览:
## Latest page snapshot
uid=29_0 RootWebArea "火柴人超炫手翻画 - 抖音" url="https://www.douyin.com/video/6611776156595129614"
  uid=29_1 ignored
    uid=29_2 generic
      uid=29_3 button "开启读屏标签"
        uid=2...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Browser-Demo-Project\test-result\run-20260918-174728\snapshots\snap-20260918-174854.txt`
```

### 步骤8: [第 4/10 轮] 关闭该标签页 [✅ success]

```
动作: close_page
工具: close_page
参数: {
  "pageId": 5
}
结果: Note: the previously selected page was closed. Page 1 is now selected.
## Pages
1: about:blank [selected]
执行前快照预览:
## Latest page snapshot
uid=29_0 RootWebArea "火柴人超炫手翻画 - 抖音" url="https://www.douyin.com/video/6611776156595129614"
  uid=37_0 ignored
    uid=37_1 generic
      uid=29_3 button "开启读屏标签"
        uid=3...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Browser-Demo-Project\test-result\run-20260918-174728\snapshots\snap-20260918-174856.txt`
```

### 步骤9: [第 5/10 轮] 打开视频页（新标签页）并停留 [✅ success]

```
动作: navigate
工具: new_page
参数: {
  "url": "https://www.douyin.com/video/6611776156595129614",
  "timeout": 30000
}
结果: ## Pages
1: about:blank
6: 火柴人超炫手翻画 - 抖音 (https://www.douyin.com/video/6611776156595129614) [selected]
断言:
  ✅ [high] url_contains: douyin.com → URL contains 'douyin.com': True
  ✅ [medium] url_contains: 6611776156595129614 → URL contains '6611776156595129614': True
  ✅ [medium] page_title: 抖音 → Page title contains '抖音': True
执行前快照预览:
## Latest page snapshot
uid=39_0 RootWebArea "火柴人超炫手翻画 - 抖音" url="https://www.douyin.com/video/6611776156595129614"
  uid=39_1 ignored
    uid=39_2 generic
      uid=39_3 button "开启读屏标签"
        uid=3...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Browser-Demo-Project\test-result\run-20260918-174728\snapshots\snap-20260918-174914.txt`
```

### 步骤10: [第 5/10 轮] 关闭该标签页 [✅ success]

```
动作: close_page
工具: close_page
参数: {
  "pageId": 6
}
结果: Note: the previously selected page was closed. Page 1 is now selected.
## Pages
1: about:blank [selected]
执行前快照预览:
## Latest page snapshot
uid=39_0 RootWebArea "火柴人超炫手翻画 - 抖音" url="https://www.douyin.com/video/6611776156595129614"
  uid=47_0 ignored
    uid=47_1 generic
      uid=39_3 button "开启读屏标签"
        uid=4...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Browser-Demo-Project\test-result\run-20260918-174728\snapshots\snap-20260918-174915.txt`
```

### 步骤11: [第 6/10 轮] 打开视频页（新标签页）并停留 [✅ success]

```
动作: navigate
工具: new_page
参数: {
  "url": "https://www.douyin.com/video/6611776156595129614",
  "timeout": 30000
}
结果: ## Pages
1: about:blank
7: 火柴人超炫手翻画 - 抖音 (https://www.douyin.com/video/6611776156595129614) [selected]
断言:
  ✅ [high] url_contains: douyin.com → URL contains 'douyin.com': True
  ✅ [medium] url_contains: 6611776156595129614 → URL contains '6611776156595129614': True
  ✅ [medium] page_title: 抖音 → Page title contains '抖音': True
执行前快照预览:
## Latest page snapshot
uid=49_0 RootWebArea "火柴人超炫手翻画 - 抖音" url="https://www.douyin.com/video/6611776156595129614"
  uid=49_1 ignored
    uid=49_2 generic
      uid=49_3 button "开启读屏标签"
        uid=4...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Browser-Demo-Project\test-result\run-20260918-174728\snapshots\snap-20260918-174938.txt`
```

### 步骤12: [第 6/10 轮] 关闭该标签页 [✅ success]

```
动作: close_page
工具: close_page
参数: {
  "pageId": 7
}
结果: Note: the previously selected page was closed. Page 1 is now selected.
## Pages
1: about:blank [selected]
执行前快照预览:
## Latest page snapshot
uid=49_0 RootWebArea "火柴人超炫手翻画 - 抖音" url="https://www.douyin.com/video/6611776156595129614"
  uid=59_0 ignored
    uid=59_1 generic
      uid=49_3 button "开启读屏标签"
        uid=5...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Browser-Demo-Project\test-result\run-20260918-174728\snapshots\snap-20260918-174939.txt`
```

### 步骤13: [第 7/10 轮] 打开视频页（新标签页）并停留 [✅ success]

```
动作: navigate
工具: new_page
参数: {
  "url": "https://www.douyin.com/video/6611776156595129614",
  "timeout": 30000
}
结果: ## Pages
1: about:blank
8: 火柴人超炫手翻画 - 抖音 (https://www.douyin.com/video/6611776156595129614) [selected]
断言:
  ✅ [high] url_contains: douyin.com → URL contains 'douyin.com': True
  ✅ [medium] url_contains: 6611776156595129614 → URL contains '6611776156595129614': True
  ✅ [medium] page_title: 抖音 → Page title contains '抖音': True
执行前快照预览:
## Latest page snapshot
uid=61_0 RootWebArea "火柴人超炫手翻画 - 抖音" url="https://www.douyin.com/video/6611776156595129614"
  uid=61_1 ignored
    uid=61_2 generic
      uid=61_3 button "开启读屏标签"
        uid=6...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Browser-Demo-Project\test-result\run-20260918-174728\snapshots\snap-20260918-174956.txt`
```

### 步骤14: [第 7/10 轮] 关闭该标签页 [✅ success]

```
动作: close_page
工具: close_page
参数: {
  "pageId": 8
}
结果: Note: the previously selected page was closed. Page 1 is now selected.
## Pages
1: about:blank [selected]
执行前快照预览:
## Latest page snapshot
uid=61_0 RootWebArea "火柴人超炫手翻画 - 抖音" url="https://www.douyin.com/video/6611776156595129614"
  uid=69_0 ignored
    uid=69_1 generic
      uid=61_3 button "开启读屏标签"
        uid=6...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Browser-Demo-Project\test-result\run-20260918-174728\snapshots\snap-20260918-174957.txt`
```

### 步骤15: [第 8/10 轮] 打开视频页（新标签页）并停留 [✅ success]

```
动作: navigate
工具: new_page
参数: {
  "url": "https://www.douyin.com/video/6611776156595129614",
  "timeout": 30000
}
结果: ## Pages
1: about:blank
9: https://www.douyin.com/video/6611776156595129614 [selected]
断言:
  ✅ [high] url_contains: douyin.com → URL contains 'douyin.com': True
  ✅ [medium] url_contains: 6611776156595129614 → URL contains '6611776156595129614': True
  ✅ [medium] page_title: 抖音 → Page title contains '抖音': True
执行前快照预览:
## Latest page snapshot
uid=71_0 RootWebArea "火柴人超炫手翻画 - 抖音" url="https://www.douyin.com/video/6611776156595129614"
  uid=71_1 ignored
    uid=71_2 generic
      uid=71_3 button "开启读屏标签"
        uid=7...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Browser-Demo-Project\test-result\run-20260918-174728\snapshots\snap-20260918-175014.txt`
```

### 步骤16: [第 8/10 轮] 关闭该标签页 [✅ success]

```
动作: close_page
工具: close_page
参数: {
  "pageId": 9
}
结果: Note: the previously selected page was closed. Page 1 is now selected.
## Pages
1: about:blank [selected]
执行前快照预览:
## Latest page snapshot
uid=71_0 RootWebArea "火柴人超炫手翻画 - 抖音" url="https://www.douyin.com/video/6611776156595129614"
  uid=79_0 ignored
    uid=79_1 generic
      uid=71_3 button "开启读屏标签"
        uid=7...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Browser-Demo-Project\test-result\run-20260918-174728\snapshots\snap-20260918-175015.txt`
```

### 步骤17: [第 9/10 轮] 打开视频页（新标签页）并停留 [✅ success]

```
动作: navigate
工具: new_page
参数: {
  "url": "https://www.douyin.com/video/6611776156595129614",
  "timeout": 30000
}
结果: ## Pages
1: about:blank
10: https://www.douyin.com/video/6611776156595129614 [selected]
断言:
  ✅ [high] url_contains: douyin.com → URL contains 'douyin.com': True
  ✅ [medium] url_contains: 6611776156595129614 → URL contains '6611776156595129614': True
  ✅ [medium] page_title: 抖音 → Page title contains '抖音': True
执行前快照预览:
## Latest page snapshot
uid=81_0 RootWebArea "火柴人超炫手翻画 - 抖音" url="https://www.douyin.com/video/6611776156595129614"
  uid=81_1 ignored
    uid=81_2 generic
      uid=81_3 button "开启读屏标签"
        uid=8...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Browser-Demo-Project\test-result\run-20260918-174728\snapshots\snap-20260918-175029.txt`
```

### 步骤18: [第 9/10 轮] 关闭该标签页 [✅ success]

```
动作: close_page
工具: close_page
参数: {
  "pageId": 10
}
结果: Note: the previously selected page was closed. Page 1 is now selected.
## Pages
1: about:blank [selected]
执行前快照预览:
## Latest page snapshot
uid=81_0 RootWebArea "火柴人超炫手翻画 - 抖音" url="https://www.douyin.com/video/6611776156595129614"
  uid=89_0 ignored
    uid=89_1 generic
      uid=81_3 button "开启读屏标签"
        uid=8...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Browser-Demo-Project\test-result\run-20260918-174728\snapshots\snap-20260918-175031.txt`
```

### 步骤19: [第 10/10 轮] 打开视频页（新标签页）并停留 [✅ success]

```
动作: navigate
工具: new_page
参数: {
  "url": "https://www.douyin.com/video/6611776156595129614",
  "timeout": 30000
}
结果: ## Pages
1: about:blank
11: https://www.douyin.com/video/6611776156595129614 [selected]
断言:
  ✅ [high] url_contains: douyin.com → URL contains 'douyin.com': True
  ✅ [medium] url_contains: 6611776156595129614 → URL contains '6611776156595129614': True
  ✅ [medium] page_title: 抖音 → Page title contains '抖音': True
执行前快照预览:
## Latest page snapshot
uid=91_0 RootWebArea "火柴人超炫手翻画 - 抖音" url="https://www.douyin.com/video/6611776156595129614"
  uid=91_1 ignored
    uid=91_2 generic
      uid=91_3 button "开启读屏标签"
        uid=9...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Browser-Demo-Project\test-result\run-20260918-174728\snapshots\snap-20260918-175046.txt`
```

### 步骤20: [第 10/10 轮] 关闭该标签页 [✅ success]

```
动作: close_page
工具: close_page
参数: {
  "pageId": 11
}
结果: Note: the previously selected page was closed. Page 1 is now selected.
## Pages
1: about:blank [selected]
执行前快照预览:
## Latest page snapshot
uid=91_0 RootWebArea "火柴人超炫手翻画 - 抖音" url="https://www.douyin.com/video/6611776156595129614"
  uid=99_0 ignored
    uid=99_1 generic
      uid=91_3 button "开启读屏标签"
        uid=9...
快照文件: `D:\APPPROJECTS\pdd-test-system\testcases\Browser-Demo-Project\test-result\run-20260918-174728\snapshots\snap-20260918-175047.txt`
```

