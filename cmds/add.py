from .base import Command
import argparse


class AddCmd(Command):
    NAME = "add"

    def execute(self):
        package_name = getattr(self.namespace, "package", "unknown")
        version = getattr(self.namespace, "version", "latest")
        print(f"增加包 {package_name}, 版本: {version}")
        

    def set_parser(self, p: argparse.ArgumentParser) -> argparse.ArgumentParser:
        subparsers = p.add_subparsers(dest="subcommand", help="Available commands")
        
        add_parser = subparsers.add_parser("add", help="Add a package")
        add_parser.add_argument("package", help="Package name to add")
        add_parser.add_argument("--version", "-v", help="Package version", default="latest")
        
        return p
