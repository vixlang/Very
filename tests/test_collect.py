from pyrsult import Success

from apis import collect


def test_collect_returns_generator_result():
    def gen():
        yield "event"
        return Success("ok")

    result = collect(gen())

    assert result.is_ok()
    assert result.unwrap() == "ok"
