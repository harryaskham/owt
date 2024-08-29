from typing import Callable, Sequence, Hashable, Any
import io
from owt.summat.adaptor import Adaptor, Nullary, DropKWs, CallOut
from owt.summat.functional import (
    F,
    Exec,
    Const,
    Identity,
    Cond,
    Fork,
)
from owt.summat.io import (
    PathSource,
    Kwargs,
    Import,
    Install,
    Input,
    QuerySource,
    JSONDataSource,
)
from owt.summat.file import (
    LoadFile,
)
import dataclasses


@dataclasses.dataclass
class Owt[**T, U](Adaptor[T, U]):
    kwargs_cls: type[T.kwargs]
    pipeline: list[Adaptor]
    input_kwargs: T.kwargs | None = None

    @classmethod
    def builder(cls, kwargs_cls: type[T.kwargs]) -> "Owt[T, T.kwargs]":
        return cls(kwargs_cls=kwargs_cls, pipeline=[])

    def to[V](self, adaptor: Adaptor[[U], V]) -> "Owt[T, V]":
        return Owt(
            pipeline=self.pipeline + [adaptor],
            kwargs_cls=self.kwargs_cls,
            input_kwargs=self.input_kwargs)

    def open(self, root_dir: str | None = None) -> "Owt[T, io.BytesIO]":
        return self.to(LoadFile(root_dir))

    def importing(self, *modules: str) -> "Owt[T, U]":
        return self.to(Import(*modules))

    def installing(self, *packages: str) -> "Owt[T, U]":
        return self.to(Install(*packages))

    def input(self) -> "Owt[T, T.kwargs]":
        return self.to(Input(lambda: self.input_kwargs))

    def query(self) -> "Owt[T, dict[str, str]]":
        return self.to(QuerySource())

    def json(self) -> "Owt[T, Any]":
        return self.to(JSONDataSource())

    def clear(self) -> "Owt[T, Nullary]":
        return self.const(Nullary())

    def kwargs(self, **kwargs: T.kwargs) -> "Owt[T, U]":
        return self.to(Kwargs(**kwargs))

    def path(self) -> "Owt[T, list[str]]":
        return self.to(PathSource())

    def last[V](self) -> "Owt[T, V]":
        def f(xs: U) -> V:
            if hasattr(xs, "__getitem__"):
                return xs[-1]
            else:
                raise TypeError(f"Expected a sequence for last(), got {type(xs)}")
        return self.f(f)

    def f[V](self, f: Callable[[U], V]) -> "Owt[T, V]":
        return self.to(F(f))

    def exec(self, f: Callable[[U], Any]) -> "Owt[T, U]":
        return self.to(Exec(f))

    def const[V](self, a: V) -> "Owt[T, V]":
        return self.to(Const(a))

    def identity(self) -> "Owt[T, U]":
        return self.to(Identity())

    def cond[V, W](self, _then: Adaptor[[U], W | V], _else: Adaptor[[U], V | W]) -> "Owt[T, V | W]":
        return self.to(Cond(_then, _else))

    def fork[V, W](
        self, left: Adaptor[[U], V], right: Adaptor[[U], W]
    ) -> "Owt[T, tuple[V, W]]":
        return self.to(Fork(left, right))

    def cast[V](self, cst: Callable[[U], V]) -> "Owt[T, V]":
        return self.f(cst)

    def map[V](
        self, f: Callable[[Any], V]
    ) -> "Owt[T, Sequence[V]]":
        return (self
                .cast(lambda u: isinstance(u, list) and u or [])
                .f(lambda xs: [f(x) for x in xs]))

    def foldl[V](self, f: Callable[[V, U], V], acc: U) -> "Owt[T, V]":
        def go(xs):
            _acc = acc
            for x in xs:
                _acc = f(_acc, x)
            return _acc
        return (self
                .cast(lambda u: isinstance(u, list) and u or [])
                .f(go))

    def foldl1[V](self, f: Callable[[V, V], V]) -> "Owt[T, V]":
        def go(xs):
            _acc, xs = xs[0], xs[1:]
            for x in xs:
                _acc = f(_acc, x)
            return _acc
        return (self
                .cast(lambda u: isinstance(u, list) and u or [])
                .f(go))

    def ix[V](self, i: int) -> "Owt[T, V]":
        return (self
                .cast(lambda u: isinstance(u, list) and u or [])
                .f(lambda xs: xs[i]))

    def get[V](self, key: Hashable) -> "Owt[T, V]":
        return (self
                .cast(lambda u: isinstance(u, dict) and u or {})
                .f(lambda xs: xs[key]))

    def call(self, **kwargs: T.kwargs) -> CallOut[U]:
        self.input_kwargs = kwargs
        run_kwargs = self.kwargs_cls(**kwargs)
        for adaptor in self.pipeline:
            out, out_kwargs = adaptor(**run_kwargs)
            run_kwargs = self.kwargs_cls(**out_kwargs)
            if not isinstance(out, Nullary):
                run_kwargs["__last__"] = out
        return DropKWs(out)


def pipe[**T](kwargs_cls: type[T.kwargs]) -> Owt[T, T.kwargs]:
    return Owt.builder(kwargs_cls)
