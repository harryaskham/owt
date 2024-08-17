from typing import Any, Protocol, Unpack, TypedDict, Callable
import flask
import copy
import dataclasses

class Args(TypedDict):
    __request__: flask.Request | None = None
    __last__: Any = None

type Out[T] = Out[T]


class Adaptor[T: Args, U](Protocol):
    def __call__(self, **kwargs: Unpack[T]) -> Out[U]: ...

    def build(self) -> Callable[[Unpack[T]], U]:
        def _run(**kwargs: Unpack[T]) -> U:
            return self(**kwargs)[0]
        return _run

class Const[T](Adaptor[Any, T]):
    def __init__(self, value: T) -> None:
        self.value = value
    def __call__(self, _: flask.Request, **kwargs: Any) -> T:
        return self.value, {}

@dataclasses.dataclass(frozen=True)
class Owt[T: Args, U](Adaptor[T, U]):

    kwargs_cls: type[T]
    pipeline: list[Adaptor]

    @classmethod
    def builder(cls, kwargs_cls: Unpack[T]) -> 'Owt[T, Unpack[T]]':
        return cls(kwargs_cls=kwargs_cls, pipeline=[])

    def into[V](self, adaptor: Adaptor[T, V]) -> 'Owt[T, V]':
        return dataclasses.replace(self, pipeline=self.pipeline + [adaptor])

    def __call__(self, **kwargs: Unpack[T]) -> Out[U]:
        run_kwargs = self.kwargs_cls(**kwargs)
        for adaptor in self.pipeline:
            print(run_kwargs)
            out, out_kwargs = adaptor(**run_kwargs)
            run_kwargs = self.kwargs_cls(**out_kwargs)
            run_kwargs["__last__"] = out
        return out, {}

def pipeline[T: Args](kwargs_cls: type[T]) -> Owt[T, T]:
    return Owt.builder(kwargs_cls)
