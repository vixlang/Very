from .base import Command as Command
from . import cmd_add, cmd_del, cmd_list, cmd_prune, cmd_init, cmd_search
from .utils import log as log, console as console

cmds: list[type[Command]] = [
    cmd_add.AddCmd,
    cmd_del.DelCmd,
    cmd_list.ListCmd,
    cmd_prune.PruneCmd,
    cmd_init.InitCmd,
    cmd_search.SearchCmd,
]
