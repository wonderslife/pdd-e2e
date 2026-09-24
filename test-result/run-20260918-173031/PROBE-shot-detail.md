# 探针 - 验证 teardown 截图是否真落盘

- **ID**: `PROBE-shot`
- **状态**: **PASS** (100.0%)
- **时间**: 2026-09-18 17:30:31
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

### 步骤1: 打开抖音视频页 [✅ success]

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
执行前快照预览:
## Latest page snapshot
uid=2_0 RootWebArea "火柴人超炫手翻画 - 抖音" url="https://www.douyin.com/video/6611776156595129614"
  uid=2_1 ignored
    uid=2_2 generic
      uid=2_3 button "开启读屏标签"
        uid=2_4 S...
快照文件: `D:\APPPROJECTS\pdd-test-system\test-result\run-20260918-173031\snapshots\snap-20260918-173055.txt`
```

