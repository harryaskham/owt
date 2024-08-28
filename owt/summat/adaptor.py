from typing import Any, Protocol, TypedDict


class Args(TypedDict):
    __last__: Any

class In[T](TypedDict):
    __last__: T


type Out[U] = tuple[U, In[U]]


class Special: ...


class Nullary(Special): ...


class RunFn[T, U](Protocol):
    def __call__(**kwargs: In[T]) -> U: ...


class Adaptor[T, U](Protocol):
    def __call__(self, **kwargs: In[T]) -> Out[U]: ...

    def done(self) -> RunFn[T, U]:
        def _run(**kwargs: In[T]) -> U:
            return self(**kwargs)[0]

        return _run
