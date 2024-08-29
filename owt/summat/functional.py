from owt.summat.adaptor import LTD, Adaptor, HasLast, CallOut, KeepKWs, DropKWs, SetKWs, Passthrough

from typing import Any, Callable, Sequence, Unpack


class F[**T, U](Adaptor[T, U]):
    def __init__(self, f: Callable[T, U]) -> None:
        self.f = f

    def call(self, **kwargs: T.kwargs) -> CallOut[U]:
        match list(kwargs.keys()):
            case ["__last__"]:
                _in = kwargs["__last__"]
                out = self.f(_in)
            case _:
                out = self.f(**kwargs)
        return DropKWs(out)


class Exec[T](Adaptor[HasLast[T], T]):
    def call(self, **kwargs: HasLast[T]) -> CallOut[T]:
        super().__call__(**kwargs)
        return Passthrough()


class Const[U](Adaptor[Any, U]):
    def __init__(self, a: U) -> None:
        self.a = a

    def call(self, **_: Any) -> CallOut[U]:
        return DropKWs(self.a)


class Identity[T](Adaptor[HasLast[T], T]):
    def call(self, **kwargs: HasLast[T]) -> CallOut[T]:
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
                case SetKWs(value, kwargs):
                    return SetKWs(value, kwargs)
        return merge(u)


class Fork[**T, U, V](Adaptor[T, tuple[U, V]]):
    def __init__(self, left: Adaptor[T, U], right: Adaptor[T, V]) -> None:
        self.left = left
        self.right = right

    def call(self, **kwargs: T.kwargs) -> CallOut[tuple[U, V]]:
        lu, lkws = self.left(**kwargs)
        ru, rkws = self.right(**kwargs)
        return DropKWs((lu, ru))


class Map[T, U](Adaptor[HasLast[Sequence[T]], Sequence[U]]):
    def __init__(self, f: Callable[[T], U]) -> None:
        self.f = f

    def call(self, **kwargs: HasLast[Sequence[T]]) -> CallOut[Sequence[U]]:
        def getLast[L](__last__: L, **_) -> L:
            return __last__
        xs: Sequence[T] = getLast(**kwargs)
        return DropKWs([self.f(x) for x in xs])


class Foldl[T, U, V](Adaptor[T, V]):
    def __init__(self, f: Callable[[U, V], V], initial: U) -> None:
        self.f = f
        self.initial = initial

    def call(self, **kwargs: HasLast[T]) -> CallOut[V]:
        sequence = kwargs["__last__"]
        result = self.initial
        for item in sequence:
            result = self.f(result, item)
        return DropKWs(result)


class Foldl1[T, V](Adaptor[T, V]):
    def __init__(self, f: Callable[[V, V], V]) -> None:
        self.f = f

    def call(self, **kwargs: HasLast[T]) -> CallOut[V]:
        sequence = kwargs["__last__"]
        if not sequence:
            raise ValueError("Sequence must not be empty for Foldl1")
        result = sequence[0]
        for item in sequence[1:]:
            result = self.f(result, item)
        return DropKWs(result)


class Ix[T](Adaptor[Sequence[T], T]):
    def __init__(self, i: int) -> None:
        self.i = i

    def call(self, **kwargs: HasLast[Sequence[T]]) -> CallOut[T]:
        return DropKWs(kwargs["__last__"][self.i])
