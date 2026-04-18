from cmds import *

import argparse

global_parser = argparse.ArgumentParser()
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
        # 设置命名空间
        cmd.namespace = args
        cmd.execute()


vpm = Vpm(global_parser)
vpm.register(cmds)


if __name__ == "__main__":
    args = global_parser.parse_args()

    # 如果没有指定命令，显示帮助信息
    if not hasattr(args, "subcommand") or not args.subcommand:
        global_parser.print_help()
        exit(1)

    vpm.run(args.subcommand, args)
