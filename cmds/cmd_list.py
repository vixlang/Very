from .base import Command
import argparse
from pathlib import Path
from .utils import Config, log


命令格式说明 = """
|======================== vpm list 命令格式说明 ========================|
[#] 格式为: 
[>]     vpm list [-t|--tree]
[/] 
[#] 说明：列出所有已安装的包
[/]
[#] 参数：
[-]     -t, --tree    以树形结构显示包列表
|==================================================================|
"""


class ListCmd(Command):
    NAME = "list"

    def execute(self):
        tree_mode = getattr(self.namespace, "tree", False)
        libs_path = Config.VIX_LIBS_PATH

        if not libs_path.exists():
            log.warning("包目录不存在!")
            return

        if tree_mode:
            self._print_tree(libs_path)
        else:
            self._print_list(libs_path)

    def _print_list(self, libs_path: Path):
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

    def _print_tree(self, libs_path: Path):
        log.info(f"{libs_path}")
        master_dirs = sorted(d for d in libs_path.iterdir() if d.is_dir())
        for i, master_dir in enumerate(master_dirs):
            is_last_master = i == len(master_dirs) - 1
            master_prefix = "└── " if is_last_master else "├── "
            log.info(f"{master_prefix}{master_dir.name}")

            user_dirs = sorted(user for user in master_dir.iterdir() if user.is_dir())
            for j, user_dir in enumerate(user_dirs):
                is_last_user = j == len(user_dirs) - 1
                if is_last_master:
                    user_prefix = "    └── " if is_last_user else "    ├── "
                else:
                    user_prefix = "│   └── " if is_last_user else "│   ├── "
                log.info(f"{user_prefix}{user_dir.name}")

                repo_dirs = sorted(repo for repo in user_dir.iterdir() if repo.is_dir())
                for k, repo_dir in enumerate(repo_dirs):
                    is_last_repo = k == len(repo_dirs) - 1
                    if is_last_master and is_last_user:
                        repo_prefix = "        └── " if is_last_repo else "        ├── "
                    elif is_last_master:
                        repo_prefix = "    │   └── " if is_last_repo else "    │   ├── "
                    elif is_last_user:
                        repo_prefix = "│       └── " if is_last_repo else "│       ├── "
                    else:
                        repo_prefix = "│   │   └── " if is_last_repo else "│   │   ├── "
                    log.info(f"{repo_prefix}{repo_dir.name}")

    def set_parser(self, p: argparse._SubParsersAction) -> argparse.ArgumentParser:
        list_parser = p.add_parser(
            "list",
            help="列出所有已安装的包",
            epilog=命令格式说明,
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        list_parser.add_argument(
            "-t", "--tree",
            action="store_true",
            help="以树形结构显示包列表"
        )
        return list_parser
