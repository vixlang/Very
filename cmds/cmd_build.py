from .base import Command
import argparse
import subprocess
import sys
from pathlib import Path
from .utils import log


class BuildCmd(Command):
    NAME = "build"

    def set_parser(self, p: argparse._SubParsersAction) -> argparse.ArgumentParser:
        parser = p.add_parser(self.NAME, help="编译 Vix 项目")
        parser.add_argument(
            "vixc_args",
            nargs=argparse.REMAINDER,
            help="传递给 vixc 的参数（原样透传）",
        )
        return parser

    def execute(self):
        args_list = self.namespace.vixc_args

        # 确认在 vix 项目根目录
        if not Path("vindex.toml").exists():
            log.error("未找到 vindex.toml，请确保在项目根目录运行此命令")
            return

        # 检查参数中是否已包含 .vix 输入文件
        has_input = any(a.endswith(".vix") for a in args_list)
        if not has_input:
            main_vix = Path("main.vix")
            if not main_vix.exists():
                log.error("未找到 main.vix，请指定输入文件或确保项目根目录有 main.vix")
                return
            args_list = [str(main_vix)] + args_list

        cmd = ["vixc"] + args_list
        log.info(f"执行: [dim]{' '.join(cmd)}[/dim]")

        result = subprocess.run(cmd)
        sys.exit(result.returncode)
