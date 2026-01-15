import functools
import json
from collections.abc import Callable
from typing import Any, Concatenate

type InstanceMethod[**P, R] = Callable[Concatenate[Any, P], R]


def _hacky_sanitise(o: Any) -> Any:
    """See https://stackoverflow.com/a/36142844"""
    return json.loads(json.dumps(o, default=str))


def log_method_inputs_and_outputs[**P, R](
    method: InstanceMethod[P, R],
) -> InstanceMethod[P, R]:
    @functools.wraps(method)
    def wrapper(self: Any, *args: P.args, **kwargs: P.kwargs):
        result = method(self, *args, **kwargs)
        return result

    return wrapper
