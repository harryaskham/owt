from owt.summat.adaptor import Adaptor, HasLast, CallOut, KeepKWs, DropKWs, SetKWs, Passthrough

from typing import Any, Callable, Sequence


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

    def call(self, *, __last__: Sequence[T], **_) -> CallOut[Sequence[U]]:
        return DropKWs([self.f(x) for x in __last__])


class Foldl[T, U](Adaptor[HasLast[Sequence[T]], U]):
    def __init__(self, f: Callable[[U, T], U], initial: U) -> None:
        self.f = f
        self.initial = initial

    def call(self, *, __last__: Sequence[T], **_) -> CallOut[U]:
        result = self.initial
        for item in __last__:
            result = self.f(result, item)
        return DropKWs(result)

class Foldl1[T](Adaptor[HasLast[Sequence[T]], T]):
    def __init__(self, f: Callable[[T, T], T]) -> None:
        self.f = f

    def call(self, *, __last__: Sequence[T], **_) -> CallOut[T]:
        if not __last__:
            raise ValueError("Sequence must not be empty for Foldl1")
        result = __last__[0]
        for item in __last__[1:]:
            result = self.f(result, item)
        return DropKWs(result)



class Ix[T](Adaptor[HasLast[Sequence[T]], T]):
    def __init__(self, i: int) -> None:
        self.i = i

    def call(self, *, __last__: Sequence[T], **_) -> CallOut[T]:
        return DropKWs(__last__[self.i])
