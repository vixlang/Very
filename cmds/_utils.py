import sys
from datetime import datetime
from colorama import init, Fore, Style

init(autoreset=True)


class Logger:
    def info(self, msg):
        print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} {msg}")

    def success(self, msg):
        print(f"{Fore.GREEN}[SUCCESS]{Style.RESET_ALL} {msg}")

    def warning(self, msg):
        print(f"{Fore.YELLOW}[WARNING]{Style.RESET_ALL} {msg}")

    def error(self, msg):
        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} {msg}", file=sys.stderr)

    def debug(self, msg):
        print(f"{Fore.MAGENTA}[DEBUG]{Style.RESET_ALL} {msg}")

    def critical(self, msg):
        """不可恢复的错误，直接退出"""
        print(f"{Fore.RED}====== [CRITICAL] {msg} ====== {Style.RESET_ALL}", file=sys.stderr)
        exit(1)


# 创建全局实例
log = Logger()
