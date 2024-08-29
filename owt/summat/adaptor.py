import abc
import dataclasses
from typing import Callable, Concatenate, Any


class Special: ...


class Nullary(Special): ...


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

@dataclasses.dataclass(frozen=True)
class PassKWs[KW](Special):
    kwargs: KW


type CallOut[U] = KeepKWs[U] | DropKWs[U] | SetKWs[U, Any] | PassKWs[Any] | Passthrough


type OutKW[**T, U] = tuple[U, T.kwargs]
type Out[**T, U] = OutKW[T, U] | OutKW[[], U] | OutKW[Concatenate[U, T], U] | OutKW[T, Nullary]


class Adaptor[**T, U](abc.ABC):
    def __call__(self, **kwargs: T.kwargs) -> Out[T, U]:
        match self.call(**kwargs):
            case Passthrough():
                match kwargs.get("__last__"):
                    case None:
                        return Nullary(), kwargs
                    case u:
                        return u, kwargs
            case PassKWs(kws):
                match kwargs.get("__last__"):
                    case None:
                        return Nullary(), kws
                    case u:
                        return u, kws
            case KeepKWs(u):
                kwargs["__last__"] = u
                return u, kwargs
            case DropKWs(u):
                return u, {"__last__": u}
            case SetKWs(u, kws):
                kws["__last__"] = u
                return u, kws
            case u:
                raise ValueError(f"Invalid call() CallOut: {u}")

    @abc.abstractmethod
    def call(self, *, __last__, **kwargs: T.kwargs) -> CallOut[U]: ...

    def done(self) -> Callable[T, U]:
        def _run(*args, **kwargs: T.kwargs) -> U:
            u = self.__call__(**kwargs)[0]
            match u:
                case Nullary():
                    raise ValueError("Run cannot return Nullary")
                case _:
                    return u

        return _run
