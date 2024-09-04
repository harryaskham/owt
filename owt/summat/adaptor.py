import abc
import logging
import copy
import dataclasses
from typing import Callable, Concatenate, Any


class Special: ...


class Nullary(Special): ...


type PassthroughKW[U] = dict[str, U]


@dataclasses.dataclass(frozen=True)
class Passthrough[U](Special):
    u: U | Nullary
    kwargs: PassthroughKW[U]


@dataclasses.dataclass(frozen=True)
class KeepKWs[U](Special):
    u: U


@dataclasses.dataclass(frozen=True)
class DropKWs[U](Special):
    u: U


@dataclasses.dataclass(frozen=True)
class PassKWs[U](Special):
    kwargs: PassthroughKW[U]


type CallOut[U] = KeepKWs[U] | DropKWs[U] | PassKWs[Any] | Passthrough[U]


type OutKW[**T, U] = tuple[U, T.kwargs]
type Out[**T, U] = (
    OutKW[T, U] | OutKW[[], U] | OutKW[Concatenate[U, T], U] | OutKW[T, Nullary]
)


class Adaptor[**T, U](abc.ABC):
    def __call__(self, **kwargs: T.kwargs) -> Out[T, U]:
        logging.debug("Calling %s with %s", self, kwargs)
        match self.call(**kwargs):
            case Passthrough(u, new_kwargs):
                logging.debug("Passthrough with: %s, %s", u, new_kwargs)
                match u:
                    case Nullary():
                        return Nullary(), new_kwargs
                    case _:
                        return u, new_kwargs
            case PassKWs(new_kwargs):
                if "__last__" not in new_kwargs and "__last__" in kwargs:
                    new_kwargs["__last__"] = kwargs["__last__"]
                return Nullary(), new_kwargs
            case KeepKWs(u):
                new_kwargs = copy.copy(kwargs)
                new_kwargs["__last__"] = u
                logging.debug("KeepKWs: %s, %s, %s", self, u, new_kwargs)
                return u, new_kwargs
            case DropKWs(u):
                new_kwargs = {"__last__": u}
                logging.debug("DropKWs: %s, %s, %s", self, u, new_kwargs)
                return u, new_kwargs
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
                logging.debug("Calling composed with kwargs: %s", kwargs)
                u, u_kwargs = this(**kwargs)
                logging.debug(
                    "Composed intermediate result:\nOut: %s\nKwargs: %s", u, u_kwargs
                )
                res = other.call(**u_kwargs)
                logging.debug("Composed final result: %s", res)
                return res

        return Composed()
