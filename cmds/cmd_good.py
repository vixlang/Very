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
            "file", nargs="?", default="main.vix", help="要检查的 .vix 文件 (默认: main.vix)"
        )
        return parser

    def execute(self):
        if not Path("vindex.toml").exists():
            log.error("未找到 vindex.toml，请确保在项目根目录运行此命令")
            return

        input_file = Path(self.namespace.file)
        if not input_file.exists():
            log.error(f"文件不存在: {input_file}")
            return

        console.print(f"  [green]ℹ[/green]  检查: [dim]{input_file}[/dim]")
        result = subprocess.run(
            ["vixc", str(input_file), "--check"],
            cwd=Path(".").resolve(),
        )
        if result.returncode == 0:
            console.print("  [green]✔[/green]  语法和类型检查通过")
        sys.exit(result.returncode)


命令格式说明 = """
|======================== very good 命令格式说明 ========================|
[#] 格式为:
[>]     very good [<file>]
[/]
[#] 说明：检查 Vix 语法和类型，不生成输出文件
[#] 参数:
[>]     file      要检查的 .vix 文件（默认 main.vix）
|==================================================================|
"""
