from .base import Command
import argparse
from .utils import Config, log

命令格式说明 = """
|======================== vpm prune 命令格式说明 ========================|
[#] 格式为:
[>]     vpm prune [--empty-only | --invalid-only]
[/]
[#] 说明：删除没有vindex.toml的包和空目录
[#] 选项:
[>]     --empty-only      只删除空目录
[>]     --invalid-only    只删除没有vindex.toml的包
|==================================================================|
"""


class PruneCmd(Command):
    NAME = "prune"

    def execute(self):
        libs_path = Config.VIX_LIBS_PATH

        if not libs_path.exists():
            log.critical("包目录不存在!")
            return

        removed_count = 0
        empty_dir_count = 0

        # 如果不是只删除空目录，则删除无效包
        if not getattr(self.namespace, "empty_only", False):
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

                        # 检查是否存在vindex.toml
                        vindex_file = repo_dir / "vindex.toml"
                        if not vindex_file.exists():
                            package_name = (
                                f"{master_dir.name}:{user_dir.name}.{repo_dir.name}"
                            )
                            log.warning(f"删除无效包: {package_name}")

                            # 删除整个仓库目录
                            import shutil

                            shutil.rmtree(repo_dir)
                            removed_count += 1

        # 如果不是只删除无效包，则清理空目录
        if not getattr(self.namespace, "invalid_only", False):
            # 清理空目录（只到包目录这一级）
            master_dirs = sorted(
                [d for d in libs_path.iterdir() if d.is_dir()], reverse=True
            )
            for master_dir in master_dirs:
                # 清理空的用户目录
                user_dirs = sorted(
                    [d for d in master_dir.iterdir() if d.is_dir()], reverse=True
                )
                for user_dir in user_dirs:
                    # 清理空的包目录
                    repo_dirs = sorted(
                        [d for d in user_dir.iterdir() if d.is_dir()], reverse=True
                    )
                    for repo_dir in repo_dirs:
                        # 检查包目录是否为空
                        if not any(repo_dir.iterdir()):
                            repo_dir.rmdir()
                            log.info(f"清理空目录: {repo_dir.relative_to(libs_path)}")
                            empty_dir_count += 1

                    # 检查用户目录是否为空
                    if not any(user_dir.iterdir()):
                        user_dir.rmdir()
                        log.info(f"清理空目录: {user_dir.relative_to(libs_path)}")
                        empty_dir_count += 1

                # 检查git主仓库目录是否为空
                if not any(master_dir.iterdir()):
                    master_dir.rmdir()
                    log.info(f"清理空目录: {master_dir.relative_to(libs_path)}")
                    empty_dir_count += 1

        # 输出清理结果
        if getattr(self.namespace, "empty_only", False):
            log.info(f"清理完成，共删除 {empty_dir_count} 个空目录")
        elif getattr(self.namespace, "invalid_only", False):
            log.info(f"清理完成，共删除 {removed_count} 个无效包")
        else:
            log.info(
                f"清理完成，共删除 {removed_count} 个无效包和 {empty_dir_count} 个空目录"
            )

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
