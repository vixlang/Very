import typer

from apis._error import IOError, Validation
from apis.scaffold import scaffold_project
from pyrsult import Failure, Success

from .share import log

app = typer.Typer()


@app.callback(invoke_without_command=True)
def init(
    name: str = typer.Argument(..., help="项目名称"),
    dir: str = typer.Option(None, "-d", "--dir", help="初始化目录（默认使用项目名称）"),
):
    """初始化一个新的 Vix 项目"""
    result = scaffold_project(name, dir_path=dir)

    match result:
        case Success(path):
            log.ok(f"成功创建项目 '[bold]{name}[/bold]' 于 {path}")
        case Failure(Validation(reason)):
            log.error(reason)
            raise typer.Exit(code=1)
        case Failure(IOError(_, detail)):
            log.error(f"创建项目失败: {detail}")
            raise typer.Exit(code=1)
