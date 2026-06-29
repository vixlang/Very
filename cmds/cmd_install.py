import typer
from pyrsult import Failure, Success

from apis._event import Log, Progress
from apis.pkg import install_dependencies

from .share import log

app = typer.Typer()


@app.callback(invoke_without_command=True)
def install(
    local: bool = typer.Option(
        False, "-l", "--local", help="强制在项目 .vix 目录下载（即使全局已存在）"
    ),
):
    """安装 vindex.toml 中声明的所有依赖"""
    gen = install_dependencies(force_local=local)
    try:
        while True:
            match next(gen):
                case Log(level, msg):
                    getattr(log, level)(msg)
                case Progress(msg, _):
                    log.info(f"  {msg}")
    except StopIteration as e:
        result = e.value

    match result:
        case Success(packages):
            for p in packages:
                log.ok(f"安装完成: {p.full_name}")
        case Failure(err):
            log.error(str(err))
            raise typer.Exit(code=1)
