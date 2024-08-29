from owt.summat.adaptor import Adaptor, CallOut, DropKWs, SetKWs, HasLast
from owt.summat.functional import Const, Exec
from typing import Any, Callable
import subprocess
import sys
import io
import importlib
import copy
from flask import request
import json


class Input[T](Adaptor[Any, T]):
    """Re-seed the pipeline with the initial input kwargs."""

    def __init__(self, get_input: Callable[[], T]) -> None:
        self.get_input = get_input

    def call(self, **kwargs) -> CallOut[T]:
        u = self.get_input()
        return SetKWs(u, u)


class JSONDataSource(Const[Any]):
    def __init__(self) -> None:
        super().__init__(json.loads(request.data))


class QuerySource(Const[dict[str, str]]):
    def __init__(self) -> None:
        super().__init__(request.args.to_dict())


class PathSource(Const[list[str]]):
    def __init__(self) -> None:
        segments = request.path.strip("/").split("/")
        super().__init__(segments)


class BufferSink(Adaptor[[io.BytesIO], bytes]):
    """Sink the last value output to a buffer."""

    def call(self, *, __last__: io.BytesIO, **_) -> CallOut[bytes]:
        return DropKWs(__last__.getvalue())


class NameOutput[T](Adaptor[HasLast[T], T]):
    """Give a kwarg name to the last value output."""

    def __init__(self, name: str) -> None:
        self.name = name

    def call(self, *, __last__: T,  **kwargs) -> CallOut[T]:
        new_kwargs = copy.copy(kwargs)
        new_kwargs[self.name] = __last__
        return SetKWs(__last__,  new_kwargs)


class Kwargs[**T, U](Adaptor[T, U]):
    """Define a set of default kwargs."""

    def __init__(self, **kwargs: T.kwargs) -> None:
        self.kwargs = kwargs

    def call(self, *, __last__, **bindings: T.kwargs) -> CallOut[U]:
        new_kwargs = copy.copy(self.kwargs)
        new_kwargs.update(bindings)
        return SetKWs(__last__, new_kwargs)


class Import[**T, U](Exec[T, U]):
    """Imports available to the rest of the pipeline."""

    def __init__(self, *modules) -> None:
        def f(*args, **kwargs):
            for module in self.modules:
                importlib.import_module(module)
        super().__init__(f)


class Install[**T, U](Exec[T, U]):
    """Installs via pip."""

    def __init__(self, *packages) -> None:
        def f(*args, **kwargs):
            subprocess.check_call([sys.executable, "-m", "pip", "install", *packages])
        super().__init__(f)
