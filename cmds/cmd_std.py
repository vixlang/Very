import typer
from pyrsult import Failure, Success

from apis._error import GitClone, GitPull
from apis.vstd import sync_std

from .share import log

app = typer.Typer()


@app.callback(invoke_without_command=True)
def std():
    """标准库管理"""
    _do_sync()


@app.command()
def sync():
    """同步标准库 vstd"""
    _do_sync()


def _do_sync():
    log.info("正在同步标准库 vstd ...")
    result = sync_std()
    match result:
        case Success(path):
            log.ok(f"标准库已同步到 {path}")
        case Failure(GitClone(_, detail)):
            log.error(f"克隆失败: {detail}")
            raise typer.Exit(code=1)
        case Failure(GitPull(_, detail)):
            log.error(f"拉取失败: {detail}")
            raise typer.Exit(code=1)
