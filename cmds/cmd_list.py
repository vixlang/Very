from pathlib import Path

import typer
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from .utils import Config, console, iter_package_dirs

app = typer.Typer()


@app.callback(invoke_without_command=True)
def list_packages(
    tree: bool = typer.Option(False, "-t", "--tree", help="以树形结构显示包列表"),
):
    """列出所有已安装的包"""
    libs_path = Config.local_libs_path()

    if not libs_path.exists():
        console.print("[red]包目录不存在![/red]")
        raise typer.Exit(code=1)
    if not libs_path.is_dir():
        console.print("[red]包路径不是目录![/red]")
        raise typer.Exit(code=1)

    if tree:
        _print_tree(libs_path)
    else:
        _print_list(libs_path)


def _print_list(libs_path: Path):
    table = Table(
        title="\n[bold]已安装的 Vix 包[/bold]",
        show_lines=True,
        header_style="bold cyan",
    )
    table.add_column("序号", style="dim", justify="center", width=4)
    table.add_column("包名", style="bold white")
    table.add_column("状态", justify="center", width=8)

    total = 0
    available = 0

    for _, _, repo_dir, package_name in iter_package_dirs(libs_path):
        vindex_file = repo_dir / "vindex.toml"
        total += 1
        if vindex_file.exists():
            available += 1
            table.add_row(str(total), package_name, "[green]可用[/green]")
        else:
            table.add_row(str(total), f"[dim]{package_name}[/dim]", "[red]不可用[/red]")

    if total == 0:
        console.print()
        console.print(
            Panel(
                "[bold yellow]当前没有安装任何包[/bold yellow]\n\n"
                "[dim]使用以下命令添加包:[/dim]\n"
                "  [green]very add <包名>[/green]    - 添加一个包\n"
                "  [green]very add --help[/green]    - 查看添加命令的帮助\n\n"
                "[dim]示例:[/dim]\n"
                "  [cyan]very add fexcode.vnet[/cyan]\n"
                "  [cyan]very add @fexcode.vnet[/cyan]     (Gitee)\n",
                title="[bold]📦 包列表[/bold]",
                border_style="yellow",
                padding=(1, 2),
            )
        )
        console.print()
    else:
        footer = f"[dim]共 {total} 个包, {available} 个可用, {total - available} 个不可用[/dim]"
        console.print(table)
        console.print(footer)


def _print_tree(libs_path: Path):
    console.print("\n[bold]Vix 包目录结构[/bold]")
    tree = Tree(f"[bold blue]{libs_path}[/bold blue]", guide_style="dim cyan")

    master_dirs = sorted(d for d in libs_path.iterdir() if d.is_dir())
    for master_dir in master_dirs:
        master_branch = tree.add(f"[bold cyan]{master_dir.name}[/bold cyan]")
        user_dirs = sorted(user for user in master_dir.iterdir() if user.is_dir())
        for user_dir in user_dirs:
            user_branch = master_branch.add(f"[bold green]{user_dir.name}[/bold green]")
            repo_dirs = sorted(repo for repo in user_dir.iterdir() if repo.is_dir())
            for repo_dir in repo_dirs:
                vindex_file = repo_dir / "vindex.toml"
                if not vindex_file.exists():
                    user_branch.add(f"[dim]{repo_dir.name}[/dim] [red](不可用)[/red]")
                else:
                    user_branch.add(f"{repo_dir.name}")

    console.print(tree)
