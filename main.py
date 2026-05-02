from cmds import cmds, Command, log, console
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
            log.critical("未知命令: %s" % cmd_name)
            self.parser.print_help()
            exit(1)

        cmd = self.commands[cmd_name]
        cmd.namespace = args
        cmd.execute()


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
    args = global_parser.parse_args()

    # 处理版本参数
    if hasattr(args, 'version') and args.version:
        show_version()

    if not hasattr(args, "subcommand") or not args.subcommand:
        print_banner()
        exit(1)

    vpm.run(args.subcommand, args)
