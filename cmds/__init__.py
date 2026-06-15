from .base import Command as Command
from . import cmd_add, cmd_del, cmd_list, cmd_prune, cmd_init, cmd_search
from .utils import log as log, console as console

CMD_REGISTRY: dict[str, dict] = {
    "add":    {"cls": cmd_add.AddCmd,     "color": "green",   "desc": "添加包"},
    "del":    {"cls": cmd_del.DelCmd,     "color": "red",     "desc": "删除包"},
    "list":   {"cls": cmd_list.ListCmd,   "color": "cyan",    "desc": "列出已安装的包"},
    "prune":  {"cls": cmd_prune.PruneCmd, "color": "yellow",  "desc": "清理无效包和空目录"},
    "init":   {"cls": cmd_init.InitCmd,   "color": "magenta", "desc": "初始化新项目"},
    "search": {"cls": cmd_search.SearchCmd,"color": "blue",   "desc": "搜索可用的包"},
}

cmds: list[type[Command]] = [entry["cls"] for entry in CMD_REGISTRY.values()]
