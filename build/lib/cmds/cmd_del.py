from .base import Command
import argparse
from .utils import log, parse_pack_name, ask_confirm
import shutil


class DelCmd(Command):
    NAME = "del"

    def execute(self):
        package_name = getattr(self.namespace, "package", "unknown")
        pack_info = parse_pack_name(package_name)
        PACK_PATH = pack_info.pack_path

        if not PACK_PATH.exists():
            log.warning(f"包 [bold]{pack_info.full_name}[/bold] 不存在")
            return

        log.section(f"删除包: {pack_info.full_name}")
        if not ask_confirm("确认删除?", default=False):
            log.warning("已取消操作")
            return

        try:
            shutil.rmtree(PACK_PATH)
            log.success(f"包 {pack_info.full_name} 已删除")
        except Exception as e:
            log.error(f"删除失败: {e}")
            return

    def set_parser(self, p: argparse._SubParsersAction) -> argparse.ArgumentParser:
        del_parser = p.add_parser(
            "del",
            help="删除包",
            epilog=命令格式说明,
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        del_parser.add_argument("package", help="需要删除的包名")
        return del_parser


命令格式说明 = """
|======================== xpm del 命令格式说明 ========================|
[#] 格式为: 
[>]     xpm del git主仓库地址:用户名.git仓库项目名
[/] 
[#] 注意：默认仓库为 github.com
[/] 
[#] 示例：
[-]     xpm del fexcode.vnet                # 删除 github.com/fexcode/vnet 仓库  
[-]     xpm del gitee.com:fexcode.vnet      # 删除 gitee.com/fexcode/vnet 仓库  
[-]     xpm del gitee:fexcode.vnet          # .com 可以省略  
[-]     xpm del @fexcode.vnet               # @符号开头默认为 gitee.com
|==================================================================|
"""
