from .base import Command
import argparse
from git import Repo,remote
import re
from pathlib import Path
from ._utils import Config, log, VIndexTool
import shutil


包格式说明 = """
|======================== vpm add 包格式说明 ========================|

格式为: 
    vpm add git主仓库地址:用户名.git仓库项目名@分支名

注意：默认仓库为 github.com

示例：
    >>> vpm add fexcode.vnet            # 下载 github.com/fexcode/vnet 仓库
    >>> vpm add fexcode.vnet@master     # 下载 github.com/fexcode/vnet 仓库 master 分支
    >>> vpm add gitee.com/fexcode.vnet  # 下载 gitee.com/fexcode/vnet 仓库
    >>> vpm add gitee/fexcode.vnet@master  # .com 可以省略
"""

from tqdm import tqdm

class TqdmProgress(remote.RemoteProgress):
    def __init__(self):
        super().__init__()
        # 初始化时，tqdm 的总量未知，设为 None
        self.pbar = tqdm(unit='objects', desc="Cloning")

    def update(self, op_code, cur_count, max_count=None, message=''):
        # 当首次获得总量时，初始化进度条的总量
        if max_count and not self.pbar.total:
            self.pbar.total = max_count
        # 计算自上次更新以来的新增进度
        new_count = cur_count - self.pbar.n
        # 更新进度条
        self.pbar.update(new_count)

    def __del__(self):
        # 对象销毁时关闭进度条
        if hasattr(self, 'pbar'):
            self.pbar.close()


class AddCmd(Command):
    NAME = "add"

    def execute(self):
        package_name = getattr(self.namespace, "package", "unknown")
        version = getattr(self.namespace, "version", "latest")
        # print(f"增加包 {package_name}, 版本: {version}")

        if ":" in package_name:
            master, package_name = package_name.split(":")
            if not "." in master:
                master = master + ".com"
        else:
            master = "github.com"

        if "@" in package_name:
            package_name, branch = package_name.split("@")
        else:
            branch = None  # git的默认分支

        package_name = package_name.replace(".", "/")

        PACK_PATH = Config.VIX_HOME / package_name

        if PACK_PATH.exists():
            log.warning(f"包 {package_name} 已经存在!")
            yn = input("是否覆盖? (y/n): ")
            if yn.lower() != "y":
                log.warning("已取消操作")
                return
            else:
                shutil.rmtree(PACK_PATH)
                log.success(f"删除包 {package_name} 成功")

        log.info(f"开始下载包 https://{master}/{package_name} ...")

        Repo.clone_from(
            f"https://{master}/{package_name}",
            PACK_PATH,
            branch=branch,
            progress=TqdmProgress()
        )

        log.info(f"下载包 {package_name} 成功，正在检查包信息 ...")

        index = VIndexTool(PACK_PATH)
        content = index.content(package_name=package_name)

        log.success(f"增加包 {package_name} 成功")
        log.debug(content)

    def set_parser(self, p: argparse.ArgumentParser) -> argparse.ArgumentParser:
        subparsers = p.add_subparsers(dest="subcommand", help="Available commands")

        add_parser = subparsers.add_parser(
            "add",
            help="Add a package",
            epilog=包格式说明,
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        add_parser.add_argument("package", help="需要添加的包名")
        add_parser.add_argument(
            "--version", "-v", help="Package version", default="latest"
        )

        return p
