from typing import Any, Protocol, Unpack, TypedDict, Callable
import copy
import dataclasses

class Args(TypedDict):
    __last__: Any

type Out[T] = Out[T]


class Adaptor[T: Args, U](Protocol):
    def __call__(self, **kwargs: Unpack[T]) -> Out[U]: ...

    def done(self) -> Callable[[Unpack[T]], U]:
        def _run(**kwargs: Unpack[T]) -> U:
            return self(**kwargs)[0]
        return _run

