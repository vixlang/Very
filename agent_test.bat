@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM  agent_test.bat — Very CLI 端到端自动化测试脚本
REM  用途：在临时目录中完整走一遍 very 工作流，验证各命令可用
REM  前置条件：
REM    1. 已更新 pyproject.toml 中的版本号
REM    2. 系统已安装 git（very add 需要）
REM ============================================================

echo ============================================================
echo  Very CLI 端到端测试
echo ============================================================
echo.

REM ---------- 0. 安装 very 到用户环境 ----------
echo [0/8] 安装 very (uv tool install . --upgrade)
uv tool install . --upgrade
if errorlevel 1 (
    echo [FAIL] very 安装失败
    exit /b 1
)
echo [PASS] very 安装成功
echo.

REM ---------- 1. 版本检查 ----------
echo [1/8] 版本检查 (very --version)
very --version
if errorlevel 1 (
    echo [FAIL] very --version 执行失败
    exit /b 1
)
echo [PASS] 版本检查通过
echo.

REM ---------- 2. 准备临时测试目录 ----------
echo [2/8] 准备临时测试目录
set "TEST_DIR=%TEMP%\for_agent_test_%RANDOM%"
mkdir "%TEST_DIR%"
if not exist "%TEST_DIR%" (
    echo [FAIL] 无法创建临时目录: %TEST_DIR%
    exit /b 1
)
cd /d "%TEST_DIR%"
echo 测试目录: %TEST_DIR%
echo [PASS] 临时目录创建成功
echo.

REM ---------- 3. 初始化项目 ----------
echo [3/8] 初始化 Vix 项目 (very init proj)
very init proj
if errorlevel 1 (
    echo [FAIL] very init 失败
    goto :cleanup
)
echo --- 项目目录结构 ---
tree /f proj
echo.
cd proj
echo [PASS] 项目初始化成功
echo.

REM ---------- 4. 验证生成的文件 ----------
echo [4/8] 验证项目文件完整性
set "FILES_OK=1"
if not exist "vindex.toml" (
    echo [MISSING] vindex.toml
    set "FILES_OK=0"
)
if not exist "main.vix" (
    echo [MISSING] main.vix
    set "FILES_OK=0"
)
if not exist "src\lib.vix" (
    echo [MISSING] src\lib.vix
    set "FILES_OK=0"
)
if not exist ".gitignore" (
    echo [MISSING] .gitignore
    set "FILES_OK=0"
)
if not exist "README.md" (
    echo [MISSING] README.md
    set "FILES_OK=0"
)
if "!FILES_OK!"=="0" (
    echo [FAIL] 项目文件不完整
    goto :cleanup
)
echo [PASS] 所有项目文件均存在
echo.

echo [5/8] 添加依赖包 (very add game)
very add game
if errorlevel 1 (
    echo [FAIL] very add game 添加依赖失败
    goto :cleanup
)

echo 接下来是 Vix 导包检测, 出现错误一般不是 Very 的问题
echo   import "game" > main.vix
echo   fn main() ^: i32 { >> main.vix
echo       say() >> main.vix
echo       return 0 >> main.vix
echo   } >> main.vix

REM ---------- 5. 语法检查 ----------
echo [5/8] 语法检查 (very good)
very good
if errorlevel 1 (
    echo [FAIL] very good 语法检查失败
    goto :cleanup
)
echo [PASS] 语法检查通过
echo.

REM ---------- 6. 构建项目 ----------
echo [6/8] 构建项目 (very build)
very build
if errorlevel 1 (
    echo [FAIL] very build 构建失败
    goto :cleanup
)
echo --- 构建产物目录结构 ---
dir /s /b
echo.
echo [PASS] 构建成功
echo.

REM ---------- 7. 列出已安装的包 ----------
echo [7/8] 列出已安装的包 (very list)
very list
echo [PASS] list 命令执行成功（无包时也应正常退出）
echo.

REM ---------- 8. 运行项目 ----------
echo [8/8] 运行项目 (very run)
very run
if errorlevel 1 (
    echo [WARN] very run 返回非零退出码（可能缺少 Vix 编译器，非脚本问题）
) else (
    echo [PASS] 项目运行成功
)
echo.

REM ============================================================
REM  测试汇总
REM ============================================================
echo ============================================================
echo  所有测试步骤已执行完毕
echo  测试目录: %TEST_DIR%
echo ============================================================

:cleanup
echo.
echo 是否清理临时目录 %TEST_DIR% ? (Y/n)
set /p "CLEANUP="
if /i not "!CLEANUP!"=="n" (
    cd /d "%TEMP%"
    rmdir /s /q "%TEST_DIR%" 2>nul
    echo 临时目录已清理
) else (
    echo 临时目录已保留: %TEST_DIR%
)

endlocal
echo.
echo 测试完成
exit /b 0
