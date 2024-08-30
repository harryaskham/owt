import abc
import logging
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
type Out[**T, U] = (
    OutKW[T, U] | OutKW[[], U] | OutKW[Concatenate[U, T], U] | OutKW[T, Nullary]
)


class Adaptor[**T, U](abc.ABC):
    def __call__(self, **kwargs: T.kwargs) -> Out[T, U]:
        logging.debug("Calling %s with %s", self, kwargs)
        match self.call(**kwargs):
            case Passthrough():
                match kwargs.get("__last__"):
                    case None:
                        logging.debug("Passthrough: Nullary, %s", self)
                        return Nullary(), kwargs
                    case u:
                        logging.debug("Passthrough: %s, %s", u, self)
                        return u, kwargs
            case PassKWs(kws):
                match kwargs.get("__last__"):
                    case None:
                        logging.debug("PassKWs: Nullary %s, %s", kws, self)
                        return Nullary(), kws
                    case u:
                        logging.debug("PassKWs: %s %s, %s", u, kws, self)
                        return u, kws
            case KeepKWs(u):
                kwargs["__last__"] = u
                logging.debug("KeepKWs: %s %s, %s", u, kwargs, self)
                return u, kwargs
            case DropKWs(u):
                logging.debug("DropKWs: %s %s, %s", u, kwargs, self)
                return u, {"__last__": u}
            case SetKWs(u, kws):
                kws["__last__"] = u
                logging.debug("SetKWs: %s %s, %s", u, kws, self)
                return u, kws
            case u:
                raise ValueError(f"Invalid call() CallOut: {u}")

    @abc.abstractmethod
    def call(self, *, __last__, **kwargs: T.kwargs) -> CallOut[U]: ...

    def done(self) -> Callable[T, U]:
        def _run(*args, **kwargs: T.kwargs) -> U:
            logging.debug("Running %s with %s", self, kwargs)
            u = self.__call__(**kwargs)[0]
            logging.debug("Result: %s", u)
            match u:
                case Nullary():
                    raise ValueError("Run cannot return Nullary")
                case _:
                    return u

        return _run

    def compose[V](self: "Adaptor[T, U]", other: "Adaptor[[U], V]") -> "Adaptor[T, V]":
        this = self

        logging.debug("Composing %s with %s", this, other)

        class Composed(Adaptor[T, V]):
            def call(self, **kwargs: T.kwargs) -> CallOut[V]:
                u, u_kwargs = this(**kwargs)
                if "__last__" in u_kwargs:
                    return other.call(**u_kwargs)
                else:
                    return other.call(__last__=u, **u_kwargs)

        return Composed()
