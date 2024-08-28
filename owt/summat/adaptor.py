from typing import Any, Protocol, Unpack, TypedDict, Callable


class Args(TypedDict):
    __last__: Any


type Out[T] = tuple[T, Args]


class Special: ...


class Nullary(Special): ...


class Adaptor[T: Args | TypedDict, U](Protocol):
    def __call__(self, **kwargs: Unpack[T]) -> Out[U]: ...

    def done(self) -> Callable[[Unpack[T]], U]:
        def _run(**kwargs: Unpack[T]) -> U:
            result = self(**kwargs)[0]
            match result:
                case Nullary():
                    return None
                case _:
                    return result

        return _run
