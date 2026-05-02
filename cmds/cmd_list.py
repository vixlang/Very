from .base import Command
import argparse
from pathlib import Path
from .utils import Config, log, console
from rich.table import Table
from rich.tree import Tree


class ListCmd(Command):
    NAME = "list"

    def execute(self):
        tree_mode = getattr(self.namespace, "tree", False)
        libs_path = Config.VIX_LIBS_PATH

        if not libs_path.exists():
            log.critical("包目录不存在!")

        if tree_mode:
            self._print_tree(libs_path)
        else:
            self._print_list(libs_path)

    def _print_list(self, libs_path: Path):
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

        for master_dir in libs_path.iterdir():
            if not master_dir.is_dir():
                continue
            for user_dir in master_dir.iterdir():
                if not user_dir.is_dir():
                    continue
                for repo_dir in user_dir.iterdir():
                    if not repo_dir.is_dir():
                        continue
                    vindex_file = repo_dir / "vindex.toml"
                    package_name = f"{master_dir.name}:{user_dir.name}.{repo_dir.name}"
                    total += 1
                    if vindex_file.exists():
                        available += 1
                        table.add_row(
                            str(total), package_name, "[green]可用[/green]"
                        )
                    else:
                        table.add_row(
                            str(total), f"[dim]{package_name}[/dim]", "[red]不可用[/red]"
                        )

        if total == 0:
            # 没有安装任何包时显示友好提示
            from rich.panel import Panel
            console.print()
            console.print(
                Panel(
                    "[bold yellow]当前没有安装任何包[/bold yellow]\n\n"
                    "[dim]使用以下命令添加包:[/dim]\n"
                    "  [green]vpm add <包名>[/green]    - 添加一个包\n"
                    "  [green]vpm add --help[/green]    - 查看添加命令的帮助\n\n"
                    "[dim]示例:[/dim]\n"
                    "  [cyan]vpm add fexcode.vnet[/cyan]\n"
                    "  [cyan]vpm add @fexcode.vnet[/cyan]     (Gitee)\n",
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

    def _print_tree(self, libs_path: Path):
        console.print("\n[bold]Vix 包目录结构[/bold]")
        tree = Tree(f"[bold blue]{libs_path}[/bold blue]", guide_style="dim cyan")

        master_dirs = sorted(d for d in libs_path.iterdir() if d.is_dir())
        for master_dir in master_dirs:
            master_branch = tree.add(f"[bold cyan]{master_dir.name}[/bold cyan]")

            user_dirs = sorted(user for user in master_dir.iterdir() if user.is_dir())
            for user_dir in user_dirs:
                user_branch = master_branch.add(
                    f"[bold green]{user_dir.name}[/bold green]"
                )

                repo_dirs = sorted(repo for repo in user_dir.iterdir() if repo.is_dir())
                for repo_dir in repo_dirs:
                    vindex_file = repo_dir / "vindex.toml"
                    if not vindex_file.exists():
                        user_branch.add(
                            f"[dim]{repo_dir.name}[/dim] [red](不可用)[/red]"
                        )
                    else:
                        user_branch.add(f"{repo_dir.name}")

        console.print(tree)

    def set_parser(self, p: argparse._SubParsersAction) -> argparse.ArgumentParser:
        list_parser = p.add_parser(
            "list",
            help="列出所有已安装的包",
            epilog=命令格式说明,
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        list_parser.add_argument(
            "-t", "--tree", action="store_true", help="以树形结构显示包列表"
        )
        return list_parser


命令格式说明 = """
|======================== vpm list 命令格式说明 ========================|
[#] 格式为: 
[>]     vpm list [-t|--tree]
[/] 
[#] 说明：列出所有已安装的包
[/]
[#] 参数：
[-]     -t, --tree    以树形结构显示包列表
|==================================================================|
"""
