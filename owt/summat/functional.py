from owt.summat.adaptor import (
    Adaptor,
    CallOut,
    KeepKWs,
    DropKWs,
    Passthrough,
    PassKWs,
    Nullary,
)

from typing import Any, Callable


class F[**T, U](Adaptor[T, U]):
    def __init__(self, f: Callable[T, U]) -> None:
        self.f = f

    def call(self, **kwargs: T.kwargs) -> CallOut[U]:
        match list(kwargs.keys()):
            case ["__last__"]:
                _in = kwargs["__last__"]
                out = self.f(_in)
            case _:
                try:
                    out = self.f(**kwargs)
                except Exception:
                    del kwargs["__last__"]
                    out = self.f(**kwargs)
        return DropKWs(out)


class Exec[**T, U](Adaptor[T, U]):
    def __init__(self, f: Callable[T, Any]) -> None:
        self.f = f

    def call(self, **kwargs: T.kwargs) -> CallOut[U]:
        self.f(**kwargs)
        return Passthrough()


class Const[U](Adaptor[Any, U]):
    def __init__(self, a: U) -> None:
        self.a = a

    def call(self, **_: Any) -> CallOut[U]:
        return DropKWs(self.a)


class Identity[T](Adaptor[[T], T]):
    def call(self, **_) -> CallOut[T]:
        return Passthrough()


class Cond[**T, U, V](Adaptor[T, U | V]):
    def __init__(self, _then: Adaptor[T, U], _else: Adaptor[T, V]) -> None:
        self._then = _then
        self._else = _else

    def call(self, **kwargs: T.kwargs) -> CallOut[U | V]:
        u: CallOut[U] | CallOut[V]
        if kwargs["__last__"]:
            u = self._then.call(**kwargs)
        else:
            u = self._else.call(**kwargs)

        def merge(u: CallOut[U] | CallOut[V]) -> CallOut[U | V]:
            match u:
                case Passthrough():
                    return Passthrough()
                case KeepKWs(value):
                    return KeepKWs(value)
                case DropKWs(value):
                    return DropKWs(value)
                case PassKWs(kwargs):
                    return PassKWs(kwargs)

        return merge(u)


class Fork[**T, U, V](Adaptor[T, tuple[U | Nullary, V | Nullary]]):
    def __init__(self, left: Adaptor[T, U], right: Adaptor[T, V]) -> None:
        self.left = left
        self.right = right

    def call(self, **kwargs: T.kwargs) -> CallOut[tuple[U | Nullary, V | Nullary]]:
        lu, lkws = self.left(**kwargs)
        ru, rkws = self.right(**kwargs)
        return DropKWs((lu, ru))
