"""very run — 编译并运行 Vix 项目"""

from pathlib import Path

import typer
from pyrsult import Err, Ok

from apis import collect
from apis.build import Progress, Log, build_and_run

from .share import log

app = typer.Typer()


@app.callback(invoke_without_command=True)
def run(
    ctx: typer.Context,
    keep: bool = typer.Option(False, "-k", "--keep", help="运行后保留生成的可执行文件"),
):
    gen = build_and_run(Path.cwd(), ctx.args, keep=keep)
    for event in gen:
        match event:
            case Progress(msg, pct):
                log.info(f"{msg} ({pct:.0f}%)")
            case Log(level, msg):
                getattr(log, level)(msg)

    match collect(gen):
        case Ok(exit_code):
            if exit_code != 0:
                log.warn(f"程序以退出码 {exit_code} 退出")
            raise typer.Exit(code=exit_code)
        case Err(err):
            log.error(str(err))
            raise typer.Exit(code=1)
