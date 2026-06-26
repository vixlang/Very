"""very exe — execute compiled Vix tools."""

from .base import Command
from .cmd_tool import install_tool
from .utils import Config, log
import argparse
import sys
import subprocess


class ExeCmd(Command):
    NAME = "exe"

    def set_parser(self, p: argparse._SubParsersAction) -> argparse.ArgumentParser:
        parser = p.add_parser(
            "exe",
            help="执行 Vix 工具",
            description="查找并执行已安装的 Vix 工具，未安装则自动安装。",
        )
        parser.add_argument("tool", help="要执行的工具名")
        return parser

    def execute(self):
        tool_name = getattr(self.namespace, "tool", "")
        extra = self.extra_args

        if not tool_name:
            log.error("请指定要执行的工具名")
            return

        suffix = ".exe" if sys.platform == "win32" else ""
        binary_path = Config.VIX_TOOLS_PATH / f"{tool_name}{suffix}"

        if not binary_path.exists():
            log.info(f"工具 [cyan]{tool_name}[/cyan] 未安装，正在自动安装...")
            result = install_tool(tool_name)
            if result is None:
                log.error(f"无法安装工具 {tool_name}")
                return
            binary_path = result

        if not binary_path.exists():
            log.error(f"工具 {tool_name} 安装后未找到编译产物")
            return

        try:
            result = subprocess.run([str(binary_path)] + extra)
            if result.returncode != 0:
                log.warning(f"工具以退出码 {result.returncode} 退出")
        except FileNotFoundError:
            log.error(f"找不到可执行文件: {binary_path}")
        except Exception as e:
            log.error(f"执行失败: {e}")
