from .base import Command
import argparse
import subprocess
import sys
from pathlib import Path
from .utils import log


class BuildCmd(Command):
    NAME = "build"

    def set_parser(self, p: argparse._SubParsersAction) -> argparse.ArgumentParser:
        parser = p.add_parser(
            self.NAME,
            help="编译 Vix 项目",
            epilog="所有无法识别的参数将原样透传给 vixc，例如: very build -o hello.exe --target=wasm32",
        )
        # 不在 argparse 注册 passthrough 参数, 避免被 -o / --target 等干扰
        return parser

    def execute(self):
        # argparse 无法识别的参数原样透传 vixc
        args_list = self.extra_args

        # 确认在 vix 项目根目录
        if not Path("vindex.toml").exists():
            log.error("未找到 vindex.toml，请确保在项目根目录运行此命令")
            return

        # 检查参数中是否已包含 .vix 输入文件
        has_input = any(a.endswith(".vix") for a in args_list)
        if not has_input:
            main_vix = Path("main.vix").resolve()
            if not main_vix.exists():
                log.error("未找到 main.vix，请指定输入文件或确保项目根目录有 main.vix")
                return
            args_list = [str(main_vix)] + args_list
        else:
            # 将用户传入的 .vix 相对路径转为绝对路径
            args_list = [
                str(Path(a).resolve()) if a.endswith(".vix") else a
                for a in args_list
            ]

        # 构建产物输出到 .vix/temp
        temp_dir = Path(".vix/temp")
        temp_dir.mkdir(parents=True, exist_ok=True)

        cmd = ["vixc"] + args_list
        log.info(f"执行: [dim]{' '.join(cmd)}[/dim]")

        result = subprocess.run(cmd, cwd=temp_dir)
        sys.exit(result.returncode)
