import typer
from pyrsult import Success, Failure
from apis.tool import install_tool
from apis._event import Progress, Log
from cmds.share import log

add_app = typer.Typer()


@add_app.callback(invoke_without_command=True)
def add(package: str = typer.Argument(..., help="工具包名")):
    """安装 Vix 工具"""
    gen = install_tool(package)
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
            log.ok(f"工具已安装: {info.binary_path}")
        case Failure(err):
            log.error(str(err))
