from typing import Unpack, Callable
from owt.summat.adaptor import Args, Adaptor, Out
from owt.summat.functional import F, FK, Const
import dataclasses


@dataclasses.dataclass(frozen=True)
class Owt[T: Args, U](Adaptor[T, U]):

    kwargs_cls: type[T]
    pipeline: list[Adaptor]

    @classmethod
    def builder(cls, kwargs_cls: Unpack[T]) -> 'Owt[T, Unpack[T]]':
        return cls(kwargs_cls=kwargs_cls, pipeline=[])

    def to[V](self, adaptor: Adaptor[T, V]) -> 'Owt[T, V]':
        return dataclasses.replace(self, pipeline=self.pipeline + [adaptor])

    def f[V](self, fn: Callable[[U], V]) -> 'Owt[T, V]':
        return self.to(F(fn))

    def fk[V](self, fn: Callable[Args, V]) -> 'Owt[T, V]':
        return self.to(FK(fn))

    def const[V](self, a: V) -> 'Owt[T, V]':
        return self.to(Const(a))

    def __call__(self, **kwargs: Unpack[T]) -> Out[U]:
        run_kwargs = self.kwargs_cls(**kwargs)
        for adaptor in self.pipeline:
            print(run_kwargs)
            out, out_kwargs = adaptor(**run_kwargs)
            run_kwargs = self.kwargs_cls(**out_kwargs)
            run_kwargs["__last__"] = out
        return out, {}


def pipe[T: Args](kwargs_cls: type[T]=Args) -> Owt[T, T]:
    return Owt.builder(kwargs_cls)
