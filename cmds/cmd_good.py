"""very good — 检查 Vix 语法和类型"""

from .base import Command
import argparse
import subprocess
import sys
from pathlib import Path
from .utils import log, console


class GoodCmd(Command):
    NAME = "good"

    def set_parser(self, p: argparse._SubParsersAction) -> argparse.ArgumentParser:
        parser = p.add_parser(
            self.NAME,
            help="检查语法和类型",
            epilog=命令格式说明,
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        parser.add_argument(
            "files",
            nargs="*",
            default=[],
            help="要检查的 .vix 文件或目录 (支持通配符, 默认: main.vix)",
        )
        return parser

    def _resolve_files(self, patterns: list[str]) -> list[Path]:
        if not patterns:
            main = Path("main.vix")
            return [main] if main.exists() else []

        files: list[Path] = []
        seen: set[Path] = set()
        for p in patterns:
            path = Path(p)
            if path.is_dir():
                for f in sorted(path.rglob("*.vix")):
                    if f not in seen:
                        files.append(f)
                        seen.add(f)
            else:
                expanded = list(Path(".").glob(p)) if ("*" in p or "?" in p) else [path]
                for f in expanded:
                    resolved = f.resolve()
                    if f.exists() and resolved not in seen:
                        files.append(f)
                        seen.add(resolved)
        return files

    def execute(self):
        if not Path("vindex.toml").exists():
            log.error("未找到 vindex.toml，请确保在项目根目录运行此命令")
            return

        patterns = self.namespace.files
        files = self._resolve_files(patterns)

        if not files:
            if patterns:
                log.error(f"未找到匹配的文件: {' '.join(patterns)}")
            else:
                log.error("未找到 main.vix，请指定要检查的文件")
            return

        has_error = False
        for i, f in enumerate(files):
            if i > 0:
                console.print()
            console.print(f"  [green]ℹ[/green]  检查: [dim]{f}[/dim]")
            result = subprocess.run(
                ["vixc", str(f), "--check"],
                cwd=Path(".").resolve(),
            )
            if result.returncode != 0:
                has_error = True

        if not has_error:
            console.print("  [green]✔[/green]  全部通过")
        sys.exit(1 if has_error else 0)


命令格式说明 = """
|======================== very good 命令格式说明 ========================|
[#] 格式为:
[>]     very good [<file>...]
[/]
[#] 说明：检查 Vix 语法和类型，不生成输出文件
[#] 参数:
[>]     file      要检查的 .vix 文件、目录或通配符（默认 main.vix）
[#] 示例:
[>]     very good
[>]     very good src/
[>]     very good src/*.vix lib/*.vix
|==================================================================|
"""
