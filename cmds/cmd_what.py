import typer
from pyrsult import Failure, Success
from rich.markdown import Markdown
from rich.panel import Panel

from apis._error import IOError, NotFound
from apis.pkg import read_package_readme

from .share import log
from .utils import console

app = typer.Typer()


@app.callback(invoke_without_command=True)
def what(
    package: str = typer.Argument(..., help="已安装的包名（支持简写语法）"),
):
    """查看已安装包的 README"""
    result = read_package_readme(package)

    match result:
        case Success(content):
            md = Markdown(content)
            console.print(Panel(md, title=f"[bold]{package}[/bold]", border_style="cyan"))
        case Failure(NotFound("package", name)):
            log.error(f"包不存在: [white]{name}[/white]")
            raise typer.Exit(code=1)
        case Failure(NotFound("readme", path)):
            log.error(f"未找到 README 文件: {path}")
            raise typer.Exit(code=1)
        case Failure(IOError(_, detail)):
            log.error(f"读取失败: {detail}")
            raise typer.Exit(code=1)
