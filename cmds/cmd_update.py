from .base import Command
import argparse
from pathlib import Path
from .utils import log, parse_pack_name, Config, iter_package_dirs
from git import Repo


class UpdateCmd(Command):
    NAME = "update"

    def set_parser(self, p: argparse._SubParsersAction) -> argparse.ArgumentParser:
        parser = p.add_parser(self.NAME, help="更新已安装的包")
        parser.add_argument(
            "package",
            nargs="?",
            default=None,
            help="要更新的包名（不指定则更新所有已安装的包）",
        )
        return parser

    def execute(self):
        packname = self.namespace.package

        local_libs = Config.local_libs_path()
        if packname:
            packinfo = parse_pack_name(packname, parent=local_libs)
            self._update_one(packinfo.full_name, packinfo.pack_path)
        else:
            if not local_libs.exists():
                log.info("没有已安装的包")
                return
            packages = list(iter_package_dirs(local_libs))
            if not packages:
                log.info("没有已安装的包")
                return
            log.section("更新所有包")
            for _md, _ud, rd, full_name in packages:
                self._update_one(full_name, rd)

    def _update_one(self, display_name: str, repo_path: Path):
        if not repo_path.exists():
            log.error(f"包 {display_name} 未安装")
            return
        log.info(f"正在更新 [cyan]{display_name}[/cyan] ...")
        try:
            repo = Repo(repo_path)
            origin = repo.remotes.origin
            pull_info = origin.pull()
            if pull_info:
                log.success(f"{display_name} 已更新到最新")
            else:
                log.info(f"{display_name} 已经是最新")
        except Exception as e:
            log.error(f"更新 {display_name} 失败: {e}")
