import typer
from pyrsult import Failure, Success

from apis._event import Log, Progress
from apis.pkg import list_packages, update_package

from .share import log

app = typer.Typer()


def _update_one(spec: str):
    gen = update_package(spec)
    try:
        while True:
            match next(gen):
                case Log(level, msg):
                    getattr(log, level)(msg)
                case Progress(msg, _):
                    log.info(f"  {msg}")
    except StopIteration:
        pass


@app.callback(invoke_without_command=True)
def update(
    package: str = typer.Argument(
        None, help="要更新的包名（不指定则更新所有已安装的包）"
    ),
):
    """更新已安装的包"""
    if package:
        _update_one(package)
        return

    match list_packages():
        case Success(packages):
            if not packages:
                log.info("没有已安装的包")
                return
            for p in packages:
                _update_one(p.full_name)
        case Failure(err):
            log.error(str(err))
            raise typer.Exit(code=1)
