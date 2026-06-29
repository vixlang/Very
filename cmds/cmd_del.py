import typer

from apis._error import IOError, NotFound
from apis.pkg import delete_package
from pyrsult import Failure, Success

from .share import log
from .utils import ask_confirm

app = typer.Typer()


@app.callback(invoke_without_command=True)
def delete(
    package: str = typer.Argument(..., help="需要删除的包名（支持简写语法）"),
):
    """删除包"""
    if not ask_confirm(f"确认删除 [white]{package}[/white]?", default=False):
        log.warn("已取消操作")
        return

    result = delete_package(package)

    match result:
        case Success(None):
            log.ok(f"包 [bold]{package}[/bold] 已删除")
        case Failure(NotFound(_, name)):
            log.error(
                f"包不存在: [white]{name}[/white]\n"
                "  • 包名拼写错误\n"
                "  • 该包尚未安装"
            )
            raise typer.Exit(code=1)
        case Failure(IOError(_, detail)):
            log.error(f"删除失败: {detail}")
            raise typer.Exit(code=1)
