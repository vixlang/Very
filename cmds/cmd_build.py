"""very build — 编译 Vix 项目"""

from pathlib import Path

import typer
from pyrsult import Failure, Success

from apis import collect
from apis.build import Progress, Log, build_project

from .share import log

app = typer.Typer()


@app.callback(invoke_without_command=True)
def build(ctx: typer.Context):
    gen = build_project(Path.cwd(), ctx.args)
    for event in gen:
        match event:
            case Progress(msg, pct):
                log.info(f"{msg} ({pct:.0f}%)")
            case Log(level, msg):
                getattr(log, level)(msg)

    match collect(gen):
        case Success(path):
            log.ok(f"编译成功: {path}")
        case Failure(err):
            log.error(str(err))
            raise typer.Exit(code=1)
