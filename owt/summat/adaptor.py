from typing import Any, Protocol, TypedDict, Callable


class Args(TypedDict):
    __last__: Any

class In[T](TypedDict):
    __last__: T


type Out[U] = tuple[U, In[U]]


class Special: ...


class Nullary(Special): ...


class Adaptor[T, U](Protocol):
    def __call__(self, **kwargs: T) -> Out[U]: ...

    def done(self) -> Callable[[T], U]:
        def _run(**kwargs: In[T]) -> U:
            return self(**kwargs)[0]

        return _run
