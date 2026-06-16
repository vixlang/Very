"""very run — 编译并运行 Vix 项目

流程:
  1. 执行 very build 编译项目
  2. 运行生成的可执行文件
  3. 删除可执行文件（除非指定 --keep / -k）

默认只输出程序的输出, 使用 -v/--vdebug 显示编译调试信息。
"""

from .base import Command
from .cmd_build import BuildCmd
import argparse
import subprocess
from pathlib import Path
from .utils import log, console


class RunCmd(Command):
    NAME = "run"

    def set_parser(self, p: argparse._SubParsersAction) -> argparse.ArgumentParser:
        parser = p.add_parser(
            self.NAME,
            help="编译并运行 Vix 项目",
            epilog="所有无法识别的参数将原样透传给 vixc，例如: very run -o hello.exe --target=wasm32",
        )
        parser.add_argument(
            "-k",
            "--keep",
            action="store_true",
            help="运行后保留生成的可执行文件",
        )
        parser.add_argument(
            "-v",
            "--vdebug",
            action="store_true",
            help="显示编译调试信息",
        )
        return parser

    def execute(self):
        args = self.namespace
        extra = self.extra_args

        keep = getattr(args, "keep", False)
        verbose = getattr(args, "vdebug", False)

        if not Path("vindex.toml").exists():
            log.error("未找到 vindex.toml，请确保在项目根目录运行此命令")
            return

        output_name = BuildCmd._extract_output_name(extra)[0]
        if output_name is None:
            output_name = BuildCmd._default_output_name()
        output_path = Path(output_name).resolve()

        if verbose:
            console.print("[bold cyan]▶ 编译项目...[/bold cyan]")
        build_cmd = BuildCmd.create_for_subcommand(
            self.namespace, extra, silent=not verbose
        )
        try:
            build_cmd.execute()
        except SystemExit as e:
            if e.code != 0:
                log.error("编译失败，无法运行")
                return

        if not output_path.exists():
            log.error(f"编译产物 {output_path.name} 未生成")
            return

        result = subprocess.run([str(output_path)] + extra)

        if result.returncode != 0:
            log.warning(f"程序以退出码 {result.returncode} 退出")

        if not keep:
            output_path.unlink()
        elif verbose:
            console.print(f"[dim]保留 {output_path.name}（--keep）[/dim]")
