import typer
from rich.panel import Panel
from rich.table import Table

from apis._error import NotFound
from apis.pkg import prune_packages
from pyrsult import Failure, Success

from .share import log
from .utils import console

app = typer.Typer()


@app.callback(invoke_without_command=True)
def prune(
    empty_only: bool = typer.Option(False, "--empty-only", help="只删除空目录"),
    invalid_only: bool = typer.Option(
        False, "--invalid-only", help="只删除没有 vindex.toml 的包"
    ),
    unused: bool = typer.Option(False, "--unused", help="只删除不被引用的孤立包"),
):
    """清理无效包、空目录和孤立包"""
    result = prune_packages(
        empty_only=empty_only,
        invalid_only=invalid_only,
        remove_unused=unused,
    )

    match result:
        case Success(report):
            _print_summary(report, empty_only, invalid_only, unused)
        case Failure(NotFound(_, _)):
            log.error("包目录不存在!")
            raise typer.Exit(code=1)
        case Failure(err):
            log.error(f"清理失败: {err}")
            raise typer.Exit(code=1)


def _print_summary(report, empty_only, invalid_only, unused_only):
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("label", style="cyan")
    table.add_column("value", style="bold white")

    if empty_only:
        table.add_row("清理的空目录数", str(len(report.removed_empty)))
    elif invalid_only:
        table.add_row("删除的无效包数", str(len(report.removed_invalid)))
    elif unused_only:
        table.add_row("删除的孤立包数", str(len(report.removed_unused)))
    else:
        if report.removed_invalid:
            table.add_row("删除的无效包数", str(len(report.removed_invalid)))
        if report.removed_empty:
            table.add_row("清理的空目录数", str(len(report.removed_empty)))
        if report.removed_unused:
            table.add_row("删除的孤立包数", str(len(report.removed_unused)))

    total = (
        len(report.removed_invalid)
        + len(report.removed_empty)
        + len(report.removed_unused)
    )
    table.add_row("合计", f"[green]{total}[/green]")

    console.print(Panel(table, title=" 清理完成 ", border_style="green"))
