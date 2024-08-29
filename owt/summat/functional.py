from owt.summat.adaptor import Adaptor, Out, L, HasLast, CallOut, KeepKWs, DropKWs, SetKWs, Passthrough

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


class Exec[T](F[HasLast[T], T]):
    def call(self, **kwargs: HasLast[T]) -> CallOut[T]:
        super().__call__(**kwargs)
        return Passthrough()


class Const[U](Adaptor[Any, U]):
    def __init__(self, a: U) -> None:
        self.a = a

    def call(self, **_: Any) -> CallOut[T]:
        return DropKWs(self.a)


class Identity[T](Adaptor[T, T]):
    def __call__(self, **kwargs: In[T]) -> Out[T]:
        return kwargs["__last__"], {}


class Cond[T, U, V](Adaptor[T, U | V]):
    def __init__(self, _then: Adaptor[T, U], _else: Adaptor[T, V]) -> None:
        self._then = _then
        self._else = _else

    def __call__(self, **kwargs: In[T]) -> Out[U | V]:
        if "__last__" in kwargs and kwargs["__last__"]:
            return self._then(**kwargs), {}
        else:
            return self._else(**kwargs), {}


class Fork[T, U, V](Adaptor[T, tuple[U, V]]):
    def __init__(self, left: Adaptor[T, U], right: Adaptor[T, V]) -> None:
        self.left = left
        self.right = right

    def __call__(self, **kwargs: In[T]) -> Out[tuple[U, V]]:
        left, lkwargs = self.left(**kwargs)
        right, rkwargs = self.right(**kwargs)
        return (left, right), {**lkwargs, **rkwargs}


class Map[T, U](F[Sequence[T], Sequence[U]]):
    def __init__(self, f: Callable[[T], U]) -> None:
        super().__init__(lambda xs, **kwargs: [f(x, **kwargs) for x in xs])


class Foldl[T, U, V](Adaptor[T, V]):
    def __init__(self, f: Callable[[U, V], V], initial: U) -> None:
        self.f = f
        self.initial = initial

    def __call__(self, **kwargs: In[T]) -> Out[V]:
        sequence = kwargs["__last__"]
        result = self.initial
        for item in sequence:
            result = self.f(result, item)
        return result, {}


class Foldl1[T, V](Adaptor[T, V]):
    def __init__(self, f: Callable[[V, V], V]) -> None:
        self.f = f

    def __call__(self, **kwargs: In[T]) -> Out[V]:
        sequence = kwargs["__last__"]
        if not sequence:
            raise ValueError("Sequence must not be empty for Foldl1")
        result = sequence[0]
        for item in sequence[1:]:
            result = self.f(result, item)
        return result, {}


class Ix[T](Adaptor[Sequence[T], T]):
    def __init__(self, i: int) -> None:
        self.i = i

    def __call__(self, **kwargs: In[Sequence[T]]) -> Out[T]:
        return kwargs["__last__"][self.i], {}
