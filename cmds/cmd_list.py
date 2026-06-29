from collections import defaultdict

import typer
from rich.table import Table
from rich.tree import Tree

from apis._error import NotFound
from apis.pkg import list_packages as api_list_packages
from pyrsult import Failure, Success

from .share import log
from .utils import console

app = typer.Typer()


@app.callback(invoke_without_command=True)
def list_command(
    tree: bool = typer.Option(False, "-t", "--tree", help="以树形结构显示包列表"),
):
    """列出所有已安装的包"""
    result = api_list_packages()

    match result:
        case Success(packages):
            if not packages:
                log.info("当前没有安装任何包")
                return
            if tree:
                _print_tree(packages)
            else:
                _print_list(packages)
        case Failure(NotFound(_, _)):
            log.info("当前没有安装任何包")
        case Failure(err):
            log.error(f"列出包失败: {err}")
            raise typer.Exit(code=1)


def _print_list(packages):
    table = Table(
        title="\n[bold]已安装的 Vix 包[/bold]",
        show_lines=True,
        header_style="bold cyan",
    )
    table.add_column("序号", style="dim", justify="center", width=4)
    table.add_column("包名", style="bold white")
    table.add_column("状态", justify="center", width=8)

    for i, pkg in enumerate(packages, 1):
        status = "[green]可用[/green]" if pkg.has_vindex else "[red]不可用[/red]"
        name = pkg.full_name if pkg.has_vindex else f"[dim]{pkg.full_name}[/dim]"
        table.add_row(str(i), name, status)

    console.print(table)
    avail = sum(1 for p in packages if p.has_vindex)
    log.info(
        f"[dim]共 {len(packages)} 个包, {avail} 个可用, "
        f"{len(packages) - avail} 个不可用[/dim]"
    )


def _print_tree(packages):
    hosts: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for pkg in packages:
        hosts[pkg.host][pkg.user].append(pkg)

    tree = Tree("[bold blue]包列表[/bold blue]", guide_style="dim cyan")
    for host in sorted(hosts):
        host_branch = tree.add(f"[bold cyan]{host}[/bold cyan]")
        for user in sorted(hosts[host]):
            user_branch = host_branch.add(f"[bold green]{user}[/bold green]")
            for pkg in sorted(hosts[host][user], key=lambda x: x.repo):
                if pkg.has_vindex:
                    user_branch.add(pkg.repo)
                else:
                    user_branch.add(f"[dim]{pkg.repo}[/dim] [red](不可用)[/red]")

    console.print(tree)
