"""very exe — execute compiled Vix tools."""

import subprocess

import typer

from .share import log
from .utils import Config

app = typer.Typer()


@app.callback(invoke_without_command=True)
def exe(
    ctx: typer.Context,
    tool: str = typer.Argument(..., help="要执行的工具名"),
):
    """执行 Vix 工具"""
    import sys

    extra = ctx.args

    if not tool:
        log.error("请指定要执行的工具名")
        raise typer.Exit(code=1)

    suffix = ".exe" if sys.platform == "win32" else ""
    binary_path = Config.VIX_TOOLS_PATH / f"{tool}{suffix}"

    if not binary_path.exists():
        log.info(f"工具 {tool} 未安装，正在自动安装...")
        from .tool import install_tool

        result = install_tool(tool)
        if result is None:
            log.error(f"无法安装工具 {tool}")
            raise typer.Exit(code=1)
        binary_path = result

    if not binary_path.exists():
        log.error(f"工具 {tool} 安装后未找到编译产物")
        raise typer.Exit(code=1)

    try:
        result = subprocess.run([str(binary_path)] + extra)
        if result.returncode != 0:
            log.warn(f"工具以退出码 {result.returncode} 退出")
        raise typer.Exit(code=result.returncode)
    except FileNotFoundError:
        log.error(f"找不到可执行文件: {binary_path}")
        raise typer.Exit(code=1)
    except Exception as e:
        log.error(f"执行失败: {e}")
        raise typer.Exit(code=1)
