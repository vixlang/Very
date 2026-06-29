from collections.abc import Generator

from pyrsult import Result


def collect(gen: Generator) -> Result:
    try:
        while True:
            next(gen)
    except StopIteration as e:
        return e.value
