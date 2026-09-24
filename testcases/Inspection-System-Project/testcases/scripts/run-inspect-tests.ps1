# E2E Test Runner - Inspection System (PC + H5)
# 按依赖顺序执行：基础数据 -> 点位 -> H5 扫码 -> PC 记录/异常/统计
#
# Usage:
#   pwsh run-inspect-tests.ps1                          # 全量（PC + H5）
#   pwsh run-inspect-tests.ps1 -SkipH5                  # 仅 PC
#   pwsh run-inspect-tests.ps1 -Only pc-006             # 只跑匹配的用例
#   pwsh run-inspect-tests.ps1 -SkipValidate            # 跳过静态校验
#
# 注意：本脚本管的是「跨用例有数据依赖」的巡检套件，顺序不能乱。
# 若用例之间彼此独立，直接用引擎的目录模式更简单：
#   .\run-test testcases\Inspection-System-Project\testcases\frontend\pc

param(
    [string]$Python = "C:\Users\name\.workbuddy\binaries\python\envs\pdd-test\Scripts\python.exe",
    [switch]$SkipH5,
    [switch]$SkipValidate,
    [string]$Only = ""
)

$ErrorActionPreference = "Continue"

# 本脚本位置: <test-system>/testcases/Inspection-System-Project/testcases/scripts/
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path      # .../testcases/scripts
$caseRoot  = Split-Path -Parent $scriptDir                        # .../Inspection-System-Project/testcases
$projDir   = Split-Path -Parent $caseRoot                         # .../Inspection-System-Project
$systemDir = Split-Path -Parent (Split-Path -Parent $projDir)     # <test-system>

$testDir = Join-Path $caseRoot "frontend"
$runner  = Join-Path $systemDir "tests\testcase-ai.py"
$resultDir = Join-Path $projDir "test-result"

if (-not (Test-Path $runner)) {
    Write-Host "[ERROR] 找不到测试引擎: $runner" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $Python)) {
    Write-Host "[ERROR] 找不到 Python: $Python" -ForegroundColor Red
    Write-Host "        可显式指定: -Python `"<python.exe 路径>`"" -ForegroundColor Yellow
    exit 1
}

Write-Host "引擎   : $runner"
Write-Host "用例   : $testDir"
Write-Host "报告   : $resultDir"
Write-Host ("-" * 70)

# 依赖自检（testcase-ai.py 需要 pyyaml + mcp）
& $Python -c "import yaml, mcp" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Python 依赖缺失，先安装：" -ForegroundColor Red
    Write-Host "        $Python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple pyyaml mcp openai"
    exit 1
}

# 静态校验：秒级完成，不启浏览器
if (-not $SkipValidate) {
    Write-Host "`n[1/2] 静态校验" -ForegroundColor Cyan
    & $Python (Join-Path $scriptDir "validate-cases.py") $testDir
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ABORT] 先修校验错误，再跑 E2E。" -ForegroundColor Red
        exit 1
    }
}

# 执行顺序有讲究：后面的用例依赖前面用例造的数据
$order = @(
    "pc/pc-001-login",
    "pc/pc-002-room-crud",
    "pc/pc-003-area-crud",
    "pc/pc-004-template-detail",
    "pc/pc-005-point-crud",
    "pc/pc-006-point-qrcode",
    "pc/pc-007-point-import",
    "h5/h5-001-scan-normal",
    "h5/h5-003-duplicate-reject",
    "h5/h5-002-abnormal-submit",
    "pc/pc-008-record-query-remark",
    "pc/pc-009-record-supplement",
    "pc/pc-010-abnormal-process",
    "pc/pc-011-stats"
)

if ($SkipH5) { $order = $order | Where-Object { $_ -notlike "h5/*" } }
if ($Only)   { $order = $order | Where-Object { $_ -like "*$Only*" } }

Write-Host "`n[2/2] E2E 执行（$($order.Count) 条）" -ForegroundColor Cyan
$passed = @(); $failed = @()

foreach ($item in $order) {
    $yaml = Join-Path $testDir "$item.yaml"
    if (-not (Test-Path $yaml)) {
        Write-Host "[SKIP] $item (文件不存在)" -ForegroundColor Yellow
        continue
    }
    Write-Host "`n>>> $item" -ForegroundColor White
    & $Python $runner $yaml
    if ($LASTEXITCODE -eq 0) { $passed += $item } else { $failed += $item }
}

Write-Host ("`n" + "=" * 70)
Write-Host "PASSED ($($passed.Count)):" -ForegroundColor Green
$passed | ForEach-Object { Write-Host "  + $_" }
if ($failed.Count -gt 0) {
    Write-Host "FAILED ($($failed.Count)):" -ForegroundColor Red
    $failed | ForEach-Object { Write-Host "  - $_" }
}
Write-Host "=" * 70
Write-Host "报告目录: $resultDir"
