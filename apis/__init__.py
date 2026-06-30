from collections.abc import Generator
from typing import TypeVar

from pyrsult import Result

T = TypeVar("T")


def collect(gen: Generator[object, None, T]) -> T:
    try:
        while True:
            next(gen)
    except StopIteration as e:
        return e.value
