from typing import Unpack, Callable, Sequence, Hashable, Any
from owt.summat.adaptor import In, Adaptor, Out, Nullary
from owt.summat.functional import (
    F,
    Exec,
    Const,
    Identity,
    Cond,
    Fork,
    Map,
    Ix,
    Foldl,
    Foldl1,
)
from owt.summat.io import (
    PathSource,
    Kwargs,
    Import,
    Install,
    Input,
    QuerySource,
    DataSource,
)
import dataclasses


@dataclasses.dataclass
class Owt[T, U](Adaptor[T, U]):
    kwargs_cls: type[T]
    pipeline: list[Adaptor]
    input_kwargs: Unpack[T] | None = None

    @classmethod
    def builder(cls, kwargs_cls: Unpack[T]) -> "Owt[T, Unpack[T]]":
        return cls(kwargs_cls=kwargs_cls, pipeline=[])

    def importing(self, *modules: str) -> "Owt[T, T]":
        return self.to(Import(*modules))

    def installing(self, *packages: str) -> "Owt[T, T]":
        return self.to(Install(*packages))

    def input(self) -> "Owt[T, T]":
        return self.to(Input(lambda: self.input_kwargs))

    def query(self) -> "Owt[T, dict[str, str]]":
        return self.to(QuerySource())

    def data(self) -> "Owt[T, bytes]":
        return self.to(DataSource())

    def clear(self) -> "Owt[T, Nullary]":
        return self.const(Nullary())

    def kwargs[K](self, **kwargs: K) -> "Owt[K, U]":
        return self.to(Kwargs(**kwargs))

    def path(self) -> "Owt[T, list[str]]":
        return self.to(PathSource())

    def last[V](self) -> "Owt[T, V]":
        return self.f(lambda xs: xs[-1])

    def to[V](self, adaptor: Adaptor[T, V]) -> "Owt[T, V]":
        return dataclasses.replace(self, pipeline=self.pipeline + [adaptor])

    def f[V](self, fn: Callable[[U], V]) -> "Owt[T, V]":
        return self.to(F(fn))

    def exec(self, fn: Callable[[Any], Any]) -> "Owt[T, T]":
        return self.to(Exec(fn))

    def const[V](self, a: V) -> "Owt[T, V]":
        return self.to(Const(a))

    def identity(self) -> "Owt[T, T]":
        return self.to(Identity())

    def cond[V, W](self, _then: Adaptor[T, V], _else: Adaptor[T, W]) -> "Owt[T, V | W]":
        return self.to(Cond(_then, _else))

    def fork[V, W](
        self, left: Adaptor[T, V], right: Adaptor[T, W]
    ) -> "Owt[T, tuple[V, W]]":
        return self.to(Fork(left, right))

    def cast[V](self, t: type[V]) -> "Owt[T, V]":
        return self.f(lambda x: t(x))

    def map[V, U: Sequence[V]](
        self, fn: Callable[[Unpack[T] | U], Sequence[V]]
    ) -> "Owt[T, Sequence[V]]":
        return self.to(Map(fn))

    def foldl[V, U](self, f: Callable[[V, U], V], initial: U) -> "Owt[T, V]":
        return self.to(Foldl(f, initial))

    def foldl1[V](self, f: Callable[[V, V], V]) -> "Owt[T, V]":
        return self.to(Foldl1(f))

    def ix[V](self, i: int) -> "Owt[T, V]":
        return self.to(Ix(i))

    def get[V](self, key: Hashable) -> "Owt[T, V]":
        return self.f(lambda x: x[key])

    def __call__(self, **kwargs: Unpack[T]) -> Out[U]:
        self.input_kwargs = kwargs
        run_kwargs = self.kwargs_cls(**kwargs)
        for adaptor in self.pipeline:
            out, out_kwargs = adaptor(**run_kwargs)
            run_kwargs = self.kwargs_cls(**out_kwargs)
            if not isinstance(out, Nullary):
                run_kwargs["__last__"] = out
        return out, {}


def pipe[T](kwargs_cls: type[In[T]] = In) -> Owt[T, T]:
    return Owt.builder(kwargs_cls)
