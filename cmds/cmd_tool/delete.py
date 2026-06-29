import typer
from pyrsult import Success, Failure
from apis.tool import delete_tool
from cmds.share import log

del_app = typer.Typer()


@del_app.callback(invoke_without_command=True)
def delete(package: str = typer.Argument(..., help="工具包名")):
    """删除 Vix 工具"""
    result = delete_tool(package)
    match result:
        case Success():
            log.ok("工具已删除")
        case Failure(err):
            log.error(str(err))
