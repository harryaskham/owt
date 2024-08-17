from .adaptor import Args, Adaptor, Out
from typing import Any, Callable, Unpack


class F[T: Args, U, Last](Adaptor[T, U]):

    def __init__(self, f: Callable[[Last], U]) -> None:
        self.f = f

    def __call__(self, **kwargs: Unpack[T]) -> Out[U]:
        return self.f(kwargs["__last__"]), {}

class FK[T: Args, U, Last](Adaptor[T, U]):

    def __init__(self, f: Callable[[Unpack[T]], U]) -> None:
        self.f = f

    def __call__(self, **kwargs: Unpack[T]) -> Out[U]:
        return self.f(**kwargs), {}


class Const[T](Adaptor[Any, T]):

    def __init__(self, a: T) -> None:
        self.a = a

    def __call__(self, **kwargs: Args) -> Out[T]:
        return self.value, {}

   
class Reset(Const[None]):
    def __init__(self) -> None:
        super().__init__(None)
