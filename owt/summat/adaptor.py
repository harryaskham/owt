import abc
import dataclasses
from typing import Protocol, Callable, Concatenate, TypedDict, ParamSpec, Any


class Special: ...


class Nullary(Special): ...

class L[U](TypedDict):
    __last__: U





class Passthrough(Special): ...

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


type CallOut[U] = KeepKWs[U] | DropKWs[U] | SetKWs[U, Any] | Passthrough

type OutKW[**T, U] = tuple[U, T.kwargs]
type Out[**T, U] = OutKW[T, U] | OutKW[[], U] | OutKW[Concatenate[L[U], ...], U]
type HasLast[T] = Concatenate[L[T], ...]



class Adaptor[**T, U](abc.ABC):
    def __call__(self, **kwargs: T.kwargs) -> Out[T, U]:
        match (kwargs, self.call(**kwargs)):
            case (L(), Passthrough()):
                return kwargs.__last__, kwargs
            case (_, Passthrough()):
                return kwargs["__last__"], kwargs
            case (L(), KeepKWs(u)):
                kwargs.__last__ = u
                return u, kwargs
            case (_, KeepKWs(u)):
                kwargs["__last__"] = u
                return u, kwargs
            case (_, DropKWs(u)):
                return u, L(__last__=u)
            case (_, SetKWs(u, kws)):
                kws.__last__ = u
                return u, kws
            case u:
                raise ValueError(f"Invalid call() CallOut: {u}")

    @abc.abstractmethod
    def call(self, **kwargs: T.kwargs) -> CallOut[U]: ...

    def done(self) -> Callable[T, U]:
        def _run(*args, **kwargs: T.kwargs) -> U:
            return self.__call__(**kwargs)[0]

        return _run
