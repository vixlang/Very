from cmds import cmds, Command, log, console
from rich.panel import Panel

import argparse

global_parser = argparse.ArgumentParser()
subparsers = global_parser.add_subparsers(dest="subcommand", help="[可用命令]")


class Xpm:
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


xpm = Xpm(global_parser)
xpm.register(cmds)


def print_banner():
    console.print(
        Panel(
            "[bold cyan]Vix 包管理器[/bold cyan]\n\n"
            "[dim]用法: xpm <命令> [参数][/dim]\n\n"
            "[bold]可用命令:[/bold]\n"
            "  [green]add[/green]    添加包\n"
            "  [red]del[/red]     删除包\n"
            "  [cyan]list[/cyan]   列出已安装的包\n"
            "  [yellow]prune[/yellow]  清理无效包和空目录\n"
            "  [magenta]init[/magenta]   初始化新项目",
            title="[bold]VPM[/bold]",
            border_style="blue",
            padding=(1, 2),
        )
    )


def main():
    args = global_parser.parse_args()

    if not hasattr(args, "subcommand") or not args.subcommand:
        print_banner()
        exit(1)

    xpm.run(args.subcommand, args)


if __name__ == "__main__":
    main()
