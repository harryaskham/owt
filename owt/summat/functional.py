from owt.summat.adaptor import Adaptor, Out, In

import copy
import logging
from typing import Any, Callable, Sequence, Unpack


class F[T, U](Adaptor[T, U]):
    def __init__(self, f: Callable[[T], U]) -> None:
        self.f = f

    def __call__(self, **kwargs: Unpack[In[T]]) -> Out[U]:
        try:
            # Only one arg means simply unary application
            if list(kwargs.keys()) == ["__last__"]:
                _in: T = kwargs["__last__"]
                out: U = self.f(_in)
                return out, {"__last__": out}
        except Exception:
            logging.debug("Failed to apply unary function")

        try:
            kwargs_without_last = copy.copy(kwargs)
            if "__last__" in kwargs_without_last:
                del kwargs_without_last["__last__"]

            # Prefer calling with kwargs
            return self.f(**kwargs_without_last), {}
        except Exception:
            logging.debug("Failed to apply kwargs")

        try:
            # On failure try a unary call with __last__, discarding other args
            return self.f(kwargs["__last__"]), {}
        except Exception:
            logging.debug("Failed to apply __last__")
            raise


class Exec[T](F[T, T]):
    def __call__(self, **kwargs: In[T]) -> Out[T]:
        super().__call__(**kwargs)
        return kwargs.get("__last__"), kwargs


class Const[T](Adaptor[Any, T]):
    def __init__(self, a: T) -> None:
        self.a = a

    def __call__(self, **_: Any) -> Out[T]:
        return self.a, {"__last__": self.a}


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
