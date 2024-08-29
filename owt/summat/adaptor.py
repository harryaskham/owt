import abc
import dataclasses
from typing import Protocol, Callable, Concatenate, TypedDict, ParamSpec, Any


class Last[U](Protocol):
    def __call__(self, /, *, __last__: U, **kwargs) -> U: ...


class HasLast[L](Protocol):
    @property
    def __last__(self) -> L: ...

class L[U](TypedDict):
    __last__: U




class Special: ...


class Nullary(Special): ...


@dataclasses.dataclass(frozen=True)
class KeepKWs[U](Special):
    u: U

@dataclasses.dataclass(frozen=True)
class DropKWs[U](Special):
    u: U

@dataclasses.dataclass(frozen=True)
class SetKWs[U, KW](Special):
    u: U
    kwargs: KW


type CallOut[U] = U | KeepKWs[U] | DropKWs[U] | SetKWs[U, Any]

type OutKW[**T, U] = tuple[U, T.kwargs]
type Out[**T, U] = OutKW[T, U] | OutKW[[], U] | OutKW[Concatenate[L[U], ...], U]



class Adaptor[**T, U](abc.ABC):
    def __call__(self, **kwargs: T.kwargs) -> Out[T, U]:
        match self.call(**kwargs):
            case KeepKWs(u):
                match kwargs:
                    case L():
                        kwargs.__last__ = u
                    case _: ...
                return u, kwargs
            case DropKWs(u):
                return u, L(__last__=u)
            case SetKWs(u, kws):
                kws.__last__ = u
                return u, kws
            case u:
                return u, L(__last__=u)

    @abc.abstractmethod
    def call(self, **kwargs: T.kwargs) -> CallOut[U]: ...

    def done(self) -> Callable[T, U]:
        def _run(*args, **kwargs: T.kwargs) -> U:
            return self.__call__(**kwargs)[0]

        return _run
