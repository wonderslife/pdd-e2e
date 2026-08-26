@echo off
setlocal
set CHROME_PATH=C:\Users\name\AppData\Local\Google\Chrome\Application\chrome.exe
if "%1"=="" (
  echo Usage: run-test ^<yaml文件^> [--think^|--think-deep]
  echo Example: run-test testcases\frontend\PRESALE-001-goods-create.yaml
  echo Example: run-test testcases\frontend\PRESALE-100-goods-create.yaml --think
  exit /b 1
)
"C:\Users\name\.workbuddy\binaries\python\envs\pdd-test\Scripts\python.exe" "%~dp0tests\testcase-ai.py" %*
