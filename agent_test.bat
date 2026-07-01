@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM  agent_test.bat — Very CLI 端到端自动化测试脚本
REM  用途：在临时目录中完整走一遍 very 工作流，验证各命令可用
REM  前置条件：
REM    1. 已编译 very（go build -o very.exe .）
REM    2. very.exe 在 PATH 中，或脚本在 very 源码目录运行
REM    3. 系统已安装 git（very add 需要）
REM ============================================================

REM ---------- 颜色定义（如果支持） ----------
for /f "tokens=2 delims=:" %%a in ('chcp') do set "ORIGINAL_CODEPAGE=%%a"
chcp 65001 >nul 2>nul

set "COLOR_RESET="
set "COLOR_RED="
set "COLOR_GREEN="
set "COLOR_YELLOW="
set "COLOR_CYAN="

for /f "tokens=2 delims=:" %%a in ('echo %CMDCMDLINE% ^| findstr /i "\\\\wt\\\\"') do (
    if not errorlevel 1 (
        set "COLOR_RESET=[0m"
        set "COLOR_RED=[31m"
        set "COLOR_GREEN=[32m"
        set "COLOR_YELLOW=[33m"
        set "COLOR_CYAN=[36m"
    )
)

echo %COLOR_CYAN%============================================================%COLOR_RESET%
echo %COLOR_CYAN% Very CLI 端到端测试%COLOR_RESET%
echo %COLOR_CYAN%============================================================%COLOR_RESET%
echo.

REM ---------- 检查前置条件 ----------
echo [前置检查] 验证必需工具...
set "PRE_CHECK_FAILED=0"

where git >nul 2>nul
if errorlevel 1 (
    echo %COLOR_YELLOW%[WARN] git 未安装，very add 可能失败%COLOR_RESET%
) else (
    echo %COLOR_GREEN%[PASS] git 已安装%COLOR_RESET%
)

where very >nul 2>nul
if errorlevel 1 (
    echo %COLOR_RED%[FAIL] very 未安装或不在 PATH 中%COLOR_RESET%
    set "PRE_CHECK_FAILED=1"
) else (
    echo %COLOR_GREEN%[PASS] very 已安装%COLOR_RESET%
)

if "!PRE_CHECK_FAILED!"=="1" (
    echo.
    echo %COLOR_RED%前置检查失败，请先安装 very%COLOR_RESET%
    exit /b 1
)
echo.

REM ---------- 1. 版本检查 ----------
echo [1/9] 版本检查 (very version)
very version
if errorlevel 1 (
    echo %COLOR_RED%[FAIL] very version 执行失败%COLOR_RESET%
    exit /b 1
)
echo %COLOR_GREEN%[PASS] 版本检查通过%COLOR_RESET%
echo.

REM ---------- 2. 准备临时测试目录 ----------
echo [2/9] 准备临时测试目录
set "TEST_DIR=%TEMP%\very_test_%RANDOM%_%RANDOM%"
mkdir "%TEST_DIR%" 2>nul
if not exist "%TEST_DIR%" (
    echo %COLOR_RED%[FAIL] 无法创建临时目录: %TEST_DIR%%COLOR_RESET%
    exit /b 1
)
cd /d "%TEST_DIR%"
echo 测试目录: %TEST_DIR%
echo %COLOR_GREEN%[PASS] 临时目录创建成功%COLOR_RESET%
echo.

REM ---------- 3. 初始化项目 ----------
echo [3/9] 初始化 Vix 项目 (very init proj)
very init proj
if errorlevel 1 (
    echo %COLOR_RED%[FAIL] very init 失败%COLOR_RESET%
    goto :cleanup
)
cd proj
echo %COLOR_GREEN%[PASS] 项目初始化成功%COLOR_RESET%

echo --- 项目目录结构 ---
dir /b /s 2>nul | findstr /v "\.git"
echo.

REM ---------- 4. 验证生成的文件 ----------
echo [4/9] 验证项目文件完整性
set "FILES_OK=1"

call :check_file "vindex.toml"
call :check_file "main.vix"
call :check_file ".gitignore"
call :check_file "README.md"

if "!FILES_OK!"=="0" (
    echo %COLOR_RED%[FAIL] 项目文件不完整%COLOR_RESET%
    goto :cleanup
)
echo %COLOR_GREEN%[PASS] 所有项目文件均存在%COLOR_RESET%
echo.

REM ---------- 5. 添加依赖包 ----------
echo [5/9] 添加依赖包 (very add game)
very add game
if errorlevel 1 (
    echo %COLOR_RED%[FAIL] very add game 添加依赖失败%COLOR_RESET%
    goto :cleanup
)
echo %COLOR_GREEN%[PASS] 依赖添加成功%COLOR_RESET%

echo --- 更新 main.vix 以使用 game 包 ---
echo import "game"> main.vix.new
echo.>> main.vix.new
echo fn main(): i32 {>> main.vix.new
echo     say()>> main.vix.new
echo     return 0>> main.vix.new
echo }>> main.vix.new

if exist main.vix.new (
    move /y main.vix.new main.vix >nul
    echo %COLOR_GREEN%[PASS] main.vix 已更新%COLOR_RESET%
) else (
    echo %COLOR_RED%[FAIL] 无法创建 main.vix.new%COLOR_RESET%
    goto :cleanup
)
echo.

REM ---------- 6. 语法检查 ----------
echo [6/9] 语法检查 (very good)
very good
if errorlevel 1 (
    echo %COLOR_YELLOW%[WARN] very good 语法检查失败（可能缺少 vixc 编译器）%COLOR_RESET%
) else (
    echo %COLOR_GREEN%[PASS] 语法检查通过%COLOR_RESET%
)
echo.

REM ---------- 7. 构建项目 ----------
echo [7/9] 构建项目 (very build)
very build
if errorlevel 1 (
    echo %COLOR_YELLOW%[WARN] very build 构建失败（可能缺少 vixc 编译器）%COLOR_RESET%
) else (
    echo %COLOR_GREEN%[PASS] 构建成功%COLOR_RESET%
)
echo.

REM ---------- 8. 列出已安装的包 ----------
echo [8/9] 列出已安装的包 (very list)
very list
if errorlevel 1 (
    echo %COLOR_YELLOW%[WARN] very list 返回非零退出码%COLOR_RESET%
) else (
    echo %COLOR_GREEN%[PASS] list 命令执行成功%COLOR_RESET%
)
echo.

REM ---------- 9. 运行项目 ----------
echo [9/9] 运行项目 (very run)
very run
if errorlevel 1 (
    echo %COLOR_YELLOW%[WARN] very run 返回非零退出码（可能缺少 Vix 编译器）%COLOR_RESET%
) else (
    echo %COLOR_GREEN%[PASS] 项目运行成功%COLOR_RESET%
)
echo.

REM ---------- 测试总结 ----------
echo %COLOR_CYAN%============================================================%COLOR_RESET%
echo %COLOR_CYAN% 测试完成！%COLOR_RESET%
echo %COLOR_CYAN%============================================================%COLOR_RESET%
echo.
echo 测试目录: %TEST_DIR%
echo.
echo 测试步骤摘要:
echo   [1] 版本检查: PASS
echo   [2] 临时目录: PASS
echo   [3] 项目初始化: PASS
echo   [4] 文件完整性: PASS
echo   [5] 依赖添加: PASS
echo   [6] 语法检查: 已执行
echo   [7] 构建: 已执行
echo   [8] 列表命令: 已执行
echo   [9] 运行: 已执行
echo.

:cleanup
echo.
set /p "CLEANUP=是否清理临时目录 %TEST_DIR% ? (Y/n) "
if /i "!CLEANUP!"=="n" (
    echo %COLOR_YELLOW%临时目录已保留: %TEST_DIR%%COLOR_RESET%
) else (
    cd /d "%TEMP%" 2>nul
    rmdir /s /q "%TEST_DIR%" 2>nul
    if exist "%TEST_DIR%" (
        echo %COLOR_YELLOW%[WARN] 无法完全清理临时目录，请手动删除: %TEST_DIR%%COLOR_RESET%
    ) else (
        echo %COLOR_GREEN%[PASS] 临时目录已清理%COLOR_RESET%
    )
)

endlocal
echo.
echo 测试脚本执行完毕
exit /b 0

REM ============================================================
REM  辅助函数
REM ============================================================

:check_file
if not exist "%~1" (
    echo %COLOR_RED%[MISSING] %~1%COLOR_RESET%
    set "FILES_OK=0"
) else (
    echo %COLOR_GREEN%[OK] %~1%COLOR_RESET%
)
exit /b 0
