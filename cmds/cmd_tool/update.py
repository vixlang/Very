import typer
from pyrsult import Success, Failure
from apis.tool import update_tool
from apis._event import Progress, Log
from cmds.share import log

update_app = typer.Typer()


@update_app.callback(invoke_without_command=True)
def update(package: str = typer.Argument(..., help="工具包名")):
    """更新 Vix 工具"""
    gen = update_tool(package)
    result = None
    try:
        while True:
            event = next(gen)
            match event:
                case Progress(msg, _):
                    log.info(msg)
                case Log(level, msg):
                    getattr(log, level, log.info)(msg)
    except StopIteration as e:
        result = e.value

    match result:
        case Success(info):
            log.ok(f"工具已更新: {info.binary_path}")
        case Failure(err):
            log.error(str(err))
