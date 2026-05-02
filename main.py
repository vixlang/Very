from cmds import cmds, Command, log, console
from cmds.utils import err_console
from rich.panel import Panel
from rich.text import Text
from rich.console import Console

import argparse
import sys

# 从 pyproject.toml 读取版本号
try:
    import tomllib
    from pathlib import Path
    
    pyproject_path = Path(__file__).parent / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        pyproject_data = tomllib.load(f)
    VERSION = pyproject_data.get("project", {}).get("version", "unknown")
except Exception:
    VERSION = "0.2.0"  #  fallback 版本

def show_version():
    """显示彩色版本信息"""
    console = Console()
    
    console.print()
    
    # 创建彩色的版本信息
    text = Text()
    text.append("╭─────────────────────────────────────╮\n", style="bold cyan")
    text.append("│  ", style="cyan")
    text.append("VPM", style="bold bright_cyan")
    text.append("  ", style="cyan")
    text.append("v", style="dim white")
    text.append(VERSION, style="bold bright_green")
    text.append("                        │\n", style="cyan")
    text.append("│  ", style="cyan")
    text.append("Vix", style="bold yellow")
    text.append(" ", style="white")
    text.append("包管理器", style="bright_white")
    text.append("                       │\n", style="cyan")
    text.append("╰─────────────────────────────────────╯", style="bold cyan")
    
    console.print(text)
    console.print()
    
    sys.exit(0)

global_parser = argparse.ArgumentParser(
    prog="vpm",
    description="Vix 包管理器",
    epilog="使用 'vpm <命令> --help' 查看命令的详细信息"
)
global_parser.add_argument(
    "-v", "--version",
    action="store_true",
    help="显示版本号"
)
subparsers = global_parser.add_subparsers(dest="subcommand", help="[可用命令]")


class Vpm:
    def __init__(self, parser: argparse.ArgumentParser):
        self.commands: dict[str, Command] = {}
        self.parser = parser

    def register(self, cmds: list[type[Command]]):
        for cmd in cmds:
            c = cmd(subparsers)
            self.commands[cmd.NAME] = c

    def run(self, cmd_name, args):
        if cmd_name not in self.commands:
            err_console.print()
            err_console.print(
                Panel(
                    f"[bold red]未知命令: [white]{cmd_name}[/white][/bold red]\n\n"
                    f"[yellow]可用的命令有:[/yellow]\n"
                    f"  [green]add[/green]    - 添加包\n"
                    f"  [red]del[/red]     - 删除包\n"
                    f"  [cyan]list[/cyan]   - 列出已安装的包\n"
                    f"  [yellow]prune[/yellow]  - 清理无效包和空目录\n"
                    f"  [magenta]init[/magenta]   - 初始化新项目\n\n"
                    f"[dim]使用 [white]vpm <命令> --help[/white] 查看命令的详细信息[/dim]",
                    title="[bold red]✘ 错误[/bold red]",
                    border_style="red",
                    padding=(1, 2),
                )
            )
            err_console.print()
            exit(1)

        cmd = self.commands[cmd_name]
        cmd.namespace = args
        try:
            cmd.execute()
        except KeyboardInterrupt:
            console.print()
            log.warning("操作已取消")
            exit(0)
        except Exception as e:
            err_console.print()
            err_console.print(
                Panel(
                    f"[bold red]命令执行失败[/bold red]\n\n"
                    f"[white]{str(e)}[/white]\n\n"
                    f"[dim]如果问题持续，请检查网络连接或联系开发者[/dim]",
                    title="[bold red]✘ 错误[/bold red]",
                    border_style="red",
                    padding=(1, 2),
                )
            )
            err_console.print()
            exit(1)


vpm = Vpm(global_parser)
vpm.register(cmds)


def print_banner():
    console.print(
        Panel(
            "[bold cyan]Vix 包管理器[/bold cyan]\n\n"
            "[dim]用法: vpm <命令> [参数][/dim]\n\n"
            "[bold]可用命令:[/bold]\n"
            "  [green]add[/green]    添加包\n"
            "  [red]del[/red]     删除包\n"
            "  [cyan]list[/cyan]   列出已安装的包\n"
            "  [yellow]prune[/yellow]  清理无效包和空目录\n"
            "  [magenta]init[/magenta]   初始化新项目",
            title="[bold]VPM[/bold]",
            border_style="cyan",
            padding=(1, 2),
        )
    )
    console.print()
    console.print(
        Panel(
            "  [bold red]del[/bold red]      删除已安装的包\n\n"
            "  [bold cyan]list[/bold cyan]    列出所有已安装的包\n\n"
            "  [bold yellow]prune[/bold yellow]  清理无效包和空目录",
            border_style="cyan",
            padding=(1, 2),
        )
    )


if __name__ == "__main__":
    try:
        args = global_parser.parse_args()
    except SystemExit as e:
        # argparse 在遇到错误时会调用 sys.exit
        # 我们捕获它并提供更友好的提示
        if e.code != 0:
            err_console.print()
            err_console.print(
                Panel(
                    "[bold red]参数错误[/bold red]\n\n"
                    "[yellow]请检查命令格式是否正确[/yellow]\n\n"
                    "[dim]使用 [white]vpm --help[/white] 查看帮助信息[/dim]",
                    title="[bold red]✘ 错误[/bold red]",
                    border_style="red",
                    padding=(1, 2),
                )
            )
            err_console.print()
        exit(e.code)

    # 处理版本参数
    if hasattr(args, 'version') and args.version:
        show_version()

    if not hasattr(args, "subcommand") or not args.subcommand:
        print_banner()
        exit(1)

    vpm.run(args.subcommand, args)
