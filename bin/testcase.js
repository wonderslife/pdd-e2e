#!/usr/bin/env node
/**
 * BDRM Test System - Testcase Project Init
 *
 * 用法:
 *   node bin/testcase.js init <项目名> [-f]   在 testcases/<项目名>/ 生成测试用例骨架
 *   node bin/testcase.js list                 列出已有测试用例项目
 *   node bin/testcase.js help                 帮助
 *
 * init 生成结构 (对齐 PDD 框架 ruoyi 模板):
 *   testcases/<项目名>/
 *   ├── README.md                     # 项目用例说明
 *   ├── backend/                      # 后端 API 用例
 *   ├── frontend/                     # 前端 E2E 用例 (yaml + env 成对)
 *   ├── shared/                       # 共享测试数据
 *   ├── reports/                      # 测试报告
 *   ├── scripts/                      # 批量执行脚本
 *   │   ├── run-all-tests.ps1
 *   │   ├── run-backend-tests.ps1
 *   │   └── run-frontend-tests.ps1
 *   └── examples/                     # 样例与格式文档 (来自 testcase-modeler skill)
 *       ├── login-flow.yaml/.env
 *       ├── asset-eval-apply.yaml/.env
 *       └── yaml-format-guide.md
 *
 * 默认合并模式: 已存在的文件/目录跳过不覆盖; -f/--force 才覆盖。
 * 执行引擎位于项目根 tests/ 目录 (testcase-ai.py), examples 样例来自 skill/testcase-modeler。
 */

'use strict';

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const TESTCASES_DIR = path.join(ROOT, 'testcases');
const SKILL_EXAMPLES = path.join(ROOT, 'skill', 'testcase-modeler', 'examples');

// ---------- 控制台着色 ----------
const C = {
  blue: (s) => `\x1b[34m${s}\x1b[0m`,
  green: (s) => `\x1b[32m${s}\x1b[0m`,
  yellow: (s) => `\x1b[33m${s}\x1b[0m`,
  gray: (s) => `\x1b[90m${s}\x1b[0m`,
  red: (s) => `\x1b[31m${s}\x1b[0m`,
};

// ---------- 模板内容 ----------

const README_TEMPLATE = (name) => `# E2E Test Cases - ${name}

## Structure

\`\`\`
${name}/
├── backend/              # 后端 API 测试用例
├── frontend/             # 前端 E2E 测试用例 (yaml + env 成对)
├── shared/               # 共享测试数据
├── reports/              # 测试报告
├── scripts/              # 批量执行脚本
└── examples/             # 样例与 YAML 格式文档
\`\`\`

## 执行方式

执行引擎位于项目根目录 tests/ 下 (\`testcase-ai.py\`, Chrome DevTools MCP 驱动):

\`\`\`bash
cd tests

# 执行单个用例
python testcase-ai.py ../testcases/${name}/frontend/<case>.yaml

# 批量执行 (scripts 内按需补充)
pwsh ../testcases/${name}/scripts/run-all-tests.ps1
\`\`\`

## 用例编写规范

- YAML 格式详见 [examples/yaml-format-guide.md](examples/yaml-format-guide.md)
- 每个用例配套一个同名 \`.env\` 文件存放环境变量 (URL / 账号等, 密码走环境变量不落明文)
- 建模新用例: 使用 testcase-modeler skill (自然语言 -> YAML)
- 执行用例: 使用 testcase-agent skill (YAML -> E2E 执行 + HTML 报告)
`;

const RUN_ALL_PS1 = `# E2E Test Runner - All Tests (按项目补充用例清单)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDir = Split-Path -Parent $scriptDir
$testsDir = Resolve-Path (Join-Path $projectDir '..\\..\\tests')

Write-Host "Running all E2E tests for $((Split-Path -Leaf $projectDir))..."

# 按需补充: 逐个执行 frontend 下的 yaml 用例, 例如:
# python (Join-Path $testsDir 'testcase-ai.py') ../testcases/frontend/<case>.yaml

Write-Host "All tests completed."
`;

const RUN_BACKEND_PS1 = `# Backend Test Runner

Write-Host "Running backend tests..."
# TODO: 按项目补充后端 API 用例执行
`;

const RUN_FRONTEND_PS1 = `# Frontend E2E Test Runner

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDir = Split-Path -Parent $scriptDir
$testsDir = Resolve-Path (Join-Path $projectDir '..\\..\\tests')
$frontendDir = Join-Path $scriptDir '..\\frontend'

Write-Host "Running frontend E2E tests..."

Get-ChildItem -Path $frontendDir -Filter *.yaml | ForEach-Object {
    Write-Host ">> $($_.Name)"
    python (Join-Path $testsDir 'testcase-ai.py') $_.FullName
}

Write-Host "Frontend tests completed."
`;

const INIT_FILES = [
  { rel: 'README.md', content: README_TEMPLATE },
  { rel: 'scripts/run-all-tests.ps1', content: () => RUN_ALL_PS1 },
  { rel: 'scripts/run-backend-tests.ps1', content: () => RUN_BACKEND_PS1 },
  { rel: 'scripts/run-frontend-tests.ps1', content: () => RUN_FRONTEND_PS1 },
];

const INIT_DIRS = ['backend', 'frontend', 'shared', 'reports', 'scripts'];

// ---------- 工具函数 ----------

function safeName(name) {
  if (!name || /[\\/:*?"<>|]/.test(name) || name.startsWith('.')) {
    console.error(C.red(`[X] 非法项目名: "${name}" (不能包含 \\ / : * ? " < > | 且不能以 . 开头)`));
    process.exit(1);
  }
  return name;
}

function copyDirSync(src, dst, force, stats) {
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    const s = path.join(src, entry.name);
    const d = path.join(dst, entry.name);
    if (entry.isDirectory()) {
      fs.mkdirSync(d, { recursive: true });
      copyDirSync(s, d, force, stats);
    } else {
      if (fs.existsSync(d) && !force) {
        stats.skip++;
        console.log(C.gray(`  [SKIP] examples/${entry.name} (已存在)`));
    } else {
      fs.mkdirSync(path.dirname(d), { recursive: true });
      fs.copyFileSync(s, d);
        stats.ok++;
        console.log(C.gray(`  [OK] examples/${entry.name}`));
      }
    }
  }
}

// ---------- 命令 ----------

function cmdInit(name, force) {
  name = safeName(name);
  const projectDir = path.join(TESTCASES_DIR, name);
  const stats = { ok: 0, skip: 0 };

  console.log(C.blue('\n========================================'));
  console.log(C.blue('   BDRM Testcase Project Init'));
  console.log(C.blue('========================================\n'));
  console.log(C.gray(`  Project: ${name}`));
  console.log(C.gray(`  Target:  ${projectDir}\n`));

  if (!fs.existsSync(TESTCASES_DIR)) {
    fs.mkdirSync(TESTCASES_DIR, { recursive: true });
  }
  if (fs.existsSync(projectDir) && force) {
    console.log(C.yellow(`[!] -f 强制模式: 已存在的文件将被覆盖 (test-result 等运行产物不受影响)\n`));
  }

  // 1. 目录
  console.log(C.blue('>> Creating directory structure...'));
  for (const dir of INIT_DIRS) {
    fs.mkdirSync(path.join(projectDir, dir), { recursive: true });
    console.log(C.gray(`  [OK] ${dir}/`));
  }

  // 2. 模板文件 (合并模式跳过已存在)
  console.log(C.blue('\n>> Creating template files...'));
  for (const file of INIT_FILES) {
    const full = path.join(projectDir, file.rel);
    const content = typeof file.content === 'function' ? file.content(name) : file.content;
    if (fs.existsSync(full) && !force) {
      stats.skip++;
      console.log(C.gray(`  [SKIP] ${file.rel} (已存在)`));
    } else {
      fs.mkdirSync(path.dirname(full), { recursive: true });
      fs.writeFileSync(full, content, 'utf-8');
      stats.ok++;
      console.log(C.gray(`  [OK] ${file.rel}`));
    }
  }

  // 3. examples 样例 (来自 testcase-modeler skill)
  console.log(C.blue('\n>> Copying example test cases...'));
  if (fs.existsSync(SKILL_EXAMPLES)) {
    copyDirSync(SKILL_EXAMPLES, path.join(projectDir, 'examples'), force, stats);
  } else {
    console.log(C.yellow(`  [SKIP] 样例源不存在: ${SKILL_EXAMPLES} (请确认 skill/testcase-modeler 已就位)`));
  }

  // 4. 汇总
  console.log(C.green('\n========================================'));
  console.log(C.green('   [OK] Testcase project ready!'));
  console.log(C.green('========================================\n'));
  console.log(C.gray(`  新建/更新: ${stats.ok}  跳过(已存在): ${stats.skip}`));
  console.log(C.gray(`  下一步:`));
  console.log(C.gray(`    1. 在 frontend/ 或 backend/ 下编写 yaml 用例 (可配合 testcase-modeler skill)`));
  console.log(C.gray(`    2. 执行: cd tests && python testcase-ai.py ../testcases/${name}/frontend/<case>.yaml`));
  console.log(C.gray(`    3. 报告输出: ../test-result/run-<时间戳>/\n`));
}

function cmdList() {
  if (!fs.existsSync(TESTCASES_DIR)) {
    console.log(C.yellow('testcases/ 目录不存在'));
    return;
  }
  const projects = fs.readdirSync(TESTCASES_DIR, { withFileTypes: true })
    .filter((e) => e.isDirectory())
    .map((e) => e.name);
  console.log(C.blue('\n已注册测试用例项目:'));
  if (projects.length === 0) {
    console.log(C.gray('  (空) 使用 node bin/testcase.js init <项目名> 创建'));
    return;
  }
  for (const p of projects) {
    const dir = path.join(TESTCASES_DIR, p);
    let yamlCount = 0;
    let resultRuns = 0;
    for (const sub of ['backend', 'frontend', 'shared', 'examples']) {
      const d = path.join(dir, sub);
      if (fs.existsSync(d)) {
        yamlCount += fs.readdirSync(d).filter((f) => f.endsWith('.yaml')).length;
      }
    }
    const trDir = path.join(dir, 'test-result');
    if (fs.existsSync(trDir)) {
      resultRuns = fs.readdirSync(trDir).filter((f) => f.startsWith('run-')).length;
    }
    // 兼容手动复制的双层 testcases/<name>/testcases/ 结构
    const inner = path.join(dir, 'testcases');
    if (fs.existsSync(inner)) {
      for (const sub of ['backend', 'frontend', 'shared', 'examples']) {
        const d = path.join(inner, sub);
        if (fs.existsSync(d)) {
          yamlCount += fs.readdirSync(d).filter((f) => f.endsWith('.yaml')).length;
        }
      }
    }
    console.log(C.gray(`  ${p.padEnd(36)} yaml: ${String(yamlCount).padStart(3)}  test-result runs: ${resultRuns}`));
  }
  console.log('');
}

function cmdHelp() {
  console.log(`
${C.blue('BDRM Testcase CLI')}

${C.green('用法:')}
  bin\\testcase init <项目名> [-f]            在 testcases/<项目名>/ 生成测试用例骨架
  bin\\testcase list                          列出已有项目及用例统计
  bin\\testcase help                          本帮助
  (等价: node bin/testcase.js ...; 请勿双击 .js 直接运行, Windows 会用 Script Host 执行报 800A03F6)

${C.green('说明:')}
  - init 默认合并模式: 已存在的文件跳过不覆盖, 加 -f/--force 才覆盖
  - examples 样例来自 skill/testcase-modeler/examples
  - 执行引擎: tests/testcase-ai.py (Chrome DevTools MCP)
`);
}

// ---------- 入口 ----------

const [, , cmd, ...args] = process.argv;

switch (cmd) {
  case 'init': {
    const force = args.some((a) => a === '-f' || a === '--force');
    const name = args.find((a) => !a.startsWith('-'));
    if (!name) {
      console.error(C.red('[X] 缺少项目名: bin\\testcase init <项目名> [-f]'));
      process.exit(1);
    }
    cmdInit(name, force);
    break;
  }
  case 'list':
    cmdList();
    break;
  case 'help':
  case '--help':
  case '-h':
  case undefined:
    cmdHelp();
    break;
  default:
    console.error(C.red(`[X] 未知命令: ${cmd} (可用: init / list / help)`));
    process.exit(1);
}
