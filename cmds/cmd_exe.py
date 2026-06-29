"""very exe — execute compiled Vix tools."""

import subprocess
import sys

import typer
from pyrsult import Failure, Success

from apis import collect
from apis.tool import Progress, Log, install_tool
from apis.types import Config

from .share import log


app = typer.Typer(name="exe", help="执行已编译的 Vix 工具")


@app.command(context_settings=dict(
    ignore_unknown_options=True,
    allow_extra_args=True,
))
def exe(tool: str, ctx: typer.Context):
    extra = list(ctx.args)
    suffix = ".exe" if sys.platform == "win32" else ""
    binary_path = Config.VIX_TOOLS_PATH / f"{tool}{suffix}"

    Tool_Is_Installed = False
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
            case Success(info):
                binary_path = info.binary_path
                log.ok(f"工具 {info.full_name} 已安装")
                Tool_Is_Installed = True
            case Failure(err):
                log.error(str(err))
                raise typer.Exit(code=1)

    if not Tool_Is_Installed and not binary_path.exists():
        log.error(f"找不到可执行文件: {tool}")
        raise typer.Exit(code=1)

    p = subprocess.run([str(binary_path)] + extra)
    if p.returncode != 0:
        log.warn(f"工具以退出码 {p.returncode} 退出")
    raise typer.Exit(code=p.returncode)
