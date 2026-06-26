from .base import Command
import argparse
from .utils import Config, log, console, iter_package_dirs, iter_empty_dirs
from rich.panel import Panel
from rich.table import Table
import shutil


class PruneCmd(Command):
    NAME = "prune"

    def execute(self):
        libs_path = Config.local_libs_path()

        if not libs_path.exists():
            log.critical("包目录不存在!")
            return
        if not libs_path.is_dir():
            log.critical("包路径不是目录!")
            return

        empty_only = getattr(self.namespace, "empty_only", False)
        invalid_only = getattr(self.namespace, "invalid_only", False)

        removed_packages = []
        removed_dirs = []

        if not empty_only:
            for _, _, repo_dir, package_name in iter_package_dirs(libs_path):
                vindex_file = repo_dir / "vindex.toml"
                if not vindex_file.exists():
                    removed_packages.append(package_name)
                    log.warning(f"无效包: [bold]{package_name}[/bold]")
                    shutil.rmtree(repo_dir)

        if not invalid_only:
            for empty_dir in iter_empty_dirs(libs_path):
                rel = empty_dir.relative_to(libs_path)
                removed_dirs.append(str(rel))
                empty_dir.rmdir()
                log.info(f"清理空目录: [dim]{rel}[/dim]")

        self._print_summary(removed_packages, removed_dirs, empty_only, invalid_only)

    def _print_summary(self, packages, dirs, empty_only: bool, invalid_only: bool):
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("label", style="cyan")
        table.add_column("value", style="bold white")

        if empty_only:
            table.add_row("清理的空目录数", str(len(dirs)))
        elif invalid_only:
            table.add_row("删除的无效包数", str(len(packages)))
        else:
            table.add_row("删除的无效包数", str(len(packages)))
            table.add_row("清理的空目录数", str(len(dirs)))

        total = len(packages) + len(dirs)
        table.add_row("合计", f"[green]{total}[/green]")

        console.print(Panel(table, title=" 清理完成 ", border_style="green"))

    def set_parser(self, p: argparse._SubParsersAction) -> argparse.ArgumentParser:
        prune_parser = p.add_parser(
            "prune",
            help="删除没有vindex.toml的包",
            epilog=命令格式说明,
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        prune_parser.add_argument(
            "--empty-only", action="store_true", help="只删除空目录"
        )
        prune_parser.add_argument(
            "--invalid-only", action="store_true", help="只删除没有vindex.toml的包"
        )
        return prune_parser


命令格式说明 = """
|======================== very prune 命令格式说明 ========================|
[#] 格式为:
[>]     very prune [--empty-only | --invalid-only]
[/]
[#] 说明：删除没有vindex.toml的包和空目录
[#] 选项:
[>]     --empty-only      只删除空目录
[>]     --invalid-only    只删除没有vindex.toml的包
|==================================================================|
"""
