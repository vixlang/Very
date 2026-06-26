from .base import Command
import argparse
from .utils import Config, log, console, iter_package_dirs, iter_empty_dirs, parse_pack_name, build_dep_tree
from rich.panel import Panel
from rich.table import Table
import shutil
from pathlib import Path


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
        unused_only = getattr(self.namespace, "unused_only", False)

        removed_packages = []
        removed_dirs = []
        unused_packages = []

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

        # ── 孤立包检查（默认 + --unused 显式） ──
        if not empty_only and not invalid_only or unused_only:
            unused_packages = self._remove_unused(libs_path)

        self._print_summary(removed_packages, removed_dirs, unused_packages, empty_only, invalid_only, unused_only)

    def _remove_unused(self, libs_path: Path) -> list[str]:
        """查找并删除孤立包。"""
        vindex_path = Path.cwd() / "vindex.toml"
        root_deps: list[str] = []
        if vindex_path.exists():
            import tomllib
            with open(vindex_path, "rb") as f:
                data = tomllib.load(f)
            root_deps = data.get("project", {}).get("deps", [])
            legacy = list(data.get("dependencies", {}).keys())
            root_deps = list(dict.fromkeys(root_deps + legacy))

        log.info("构建依赖树...")
        referenced = build_dep_tree(libs_path, root_deps)

        unused: list[str] = []
        for _, _, repo_dir, full_name in iter_package_dirs(libs_path):
            if full_name not in referenced:
                unused.append(full_name)

        if unused:
            log.warning(f"发现 [bold]{len(unused)}[/bold] 个孤立包: [dim]{', '.join(unused)}[/dim]")
            from .utils import ask_confirm
            if ask_confirm("是否删除这些孤立包?", default=False):
                for _, _, repo_dir, full_name in iter_package_dirs(libs_path):
                    if full_name in unused:
                        shutil.rmtree(repo_dir)
                        log.success(f"已删除孤立包: {full_name}")
                return unused
        else:
            log.info("没有孤立包")

        return []

    def _print_summary(self, packages, dirs, unused, empty_only: bool, invalid_only: bool, unused_only: bool):
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("label", style="cyan")
        table.add_column("value", style="bold white")

        if empty_only:
            table.add_row("清理的空目录数", str(len(dirs)))
        elif invalid_only:
            table.add_row("删除的无效包数", str(len(packages)))
        elif unused_only:
            table.add_row("删除的孤立包数", str(len(unused)))
        else:
            if packages:
                table.add_row("删除的无效包数", str(len(packages)))
            if dirs:
                table.add_row("清理的空目录数", str(len(dirs)))
            if unused:
                table.add_row("删除的孤立包数", str(len(unused)))

        total = len(packages) + len(dirs) + len(unused)
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
        prune_parser.add_argument(
            "--unused", action="store_true", dest="unused_only", help="只删除不被引用的孤立包"
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
