"""very exe — execute compiled Vix tools."""

import subprocess
import sys

import typer
from pyrsult import Err, Ok

from apis import collect
from apis.tool import Progress, Log, install_tool
from apis.types import Config

from .share import log

app = typer.Typer()


@app.callback(invoke_without_command=True)
def exe(
    ctx: typer.Context,
    tool: str = typer.Argument(..., help="要执行的工具名"),
):
    extra = ctx.args
    suffix = ".exe" if sys.platform == "win32" else ""
    binary_path = Config.VIX_TOOLS_PATH / f"{tool}{suffix}"

    if not binary_path.exists():
        log.info(f"工具 {tool} 未安装，正在自动安装...")
        gen = install_tool(tool)
        for event in gen:
            match event:
                case Progress(msg, pct):
                    log.info(f"{msg} ({pct:.0f}%)")
                case Log(level, msg):
                    getattr(log, level)(msg)

        match collect(gen):
            case Ok(info):
                binary_path = info.binary_path
                log.ok(f"工具 {info.full_name} 已安装")
            case Err(err):
                log.error(str(err))
                raise typer.Exit(code=1)

    if not binary_path.exists():
        log.error(f"找不到可执行文件: {tool}")
        raise typer.Exit(code=1)

    p = subprocess.run([str(binary_path)] + extra)
    if p.returncode != 0:
        log.warn(f"工具以退出码 {p.returncode} 退出")
    raise typer.Exit(code=p.returncode)
