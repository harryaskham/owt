import abc
from typing import TypedDict, Protocol


class WithLast[T](TypedDict):
    __last__: T


type Out[U] = tuple[U, WithLast[U]]


class Special: ...


class Nullary(Special): ...

class RunFn[T, U](Protocol):
    def __call__(self, **kwargs: T) -> U: ...


class Adaptor[T, U](abc.ABC):
    @abc.abstractmethod
    def __call__(self, **kwargs: T) -> Out[U]: ...

    def done(self) -> RunFn[T, U]:
        def _run(**kwargs: T) -> U:
            return self.__call__(**kwargs)[0]

        return _run
