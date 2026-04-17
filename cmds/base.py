from abc import ABC, abstractmethod
import argparse
from ._utils import log


class Command(ABC):
    NAME: str

    @property
    def name(self) -> str:
        # 如果报错了，看看你是不是没有定义 NAME
        return self.NAME

    def __init__(self, p: argparse.ArgumentParser):
        self.parser = self.set_parser(p)
        # 这里不立即解析参数，参数在 main.py 中统一解析
        self.namespace = None

    @abstractmethod
    def set_parser(self, p: argparse.ArgumentParser) -> argparse.ArgumentParser: ...

    @abstractmethod
    def execute(self): ...
