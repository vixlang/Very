from .base import Command
import argparse
from pathlib import Path
from .utils import Config, log


命令格式说明 = """
|======================== vpm list 命令格式说明 ========================|
[#] 格式为: 
[>]     vpm list
[/] 
[#] 说明：列出所有已安装的包
|==================================================================|
"""


class ListCmd(Command):
    NAME = "list"

    def execute(self):
        libs_path = Config.VIX_LIBS_PATH

        if not libs_path.exists():
            log.warning("包目录不存在!")
            return

        # 遍历所有git主仓库目录
        for master_dir in libs_path.iterdir():
            if not master_dir.is_dir():
                continue

            # 遍历用户目录
            for user_dir in master_dir.iterdir():
                if not user_dir.is_dir():
                    continue

                # 遍历仓库目录
                for repo_dir in user_dir.iterdir():
                    if not repo_dir.is_dir():
                        continue

                    # 构建包名
                    package_name = f"{master_dir.name}:{user_dir.name}.{repo_dir.name}"
                    log.info(f"  {package_name}")

    def set_parser(self, p: argparse._SubParsersAction) -> argparse.ArgumentParser:
        list_parser = p.add_parser(
            "list",
            help="列出所有已安装的包",
            epilog=命令格式说明,
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        return list_parser
