import typer
from pyrsult import Success, Failure
from apis.tool import update_tool, list_tools
from apis._event import Progress, Log
from cmds.share import log


update_app = typer.Typer()


def _update_one(package: str):
    gen = update_tool(package)
    try:
        while True:
            match next(gen):
                case Log(level, msg):
                    getattr(log, level, log.info)(msg)
                case Progress(msg, _):
                    log.info(f"  {msg}")
    except StopIteration:
        pass


@update_app.callback(invoke_without_command=True)
def update(
    package: str = typer.Argument(None, help="工具包名（不指定则更新所有工具）"),
):
    """更新 Vix 工具"""
    if package:
        _update_one(package)
        return

    match list_tools():
        case Success(names):
            if not names:
                log.info("没有已安装的工具")
                return
            for name in names:
                _update_one(name)
        case Failure(err):
            log.error(str(err))
            raise typer.Exit(code=1)
