from collections.abc import Generator

from pyrsult import Result


def collect(gen: Generator) -> Result:
    for _ in gen:
        pass
    try:
        gen.send(None)
    except StopIteration as e:
        return e.value
