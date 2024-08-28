from owt.summat.adaptor import In, Adaptor, Out, Nullary
from owt.summat.functional import Const
from typing import Text, Unpack, Sequence, Any, Callable
import logging
import subprocess
import sys
import io
import importlib
import copy
from flask import request
import json


class Input[T](Adaptor[Any, Nullary]):
    """Re-seed the pipeline with the initial input kwargs."""

    def __init__(self, get_input: Callable[[], T]) -> None:
        self.get_input = get_input

    def __call__(self, **_: Any) -> Out[T]:
        return Nullary(), self.get_input()


class DataSource(Const[dict[str, Any]]):
    def __init__(self) -> None:
        super().__init__(json.loads(request.data))


class QuerySource(Const[dict[str, str]]):
    def __init__(self) -> None:
        super().__init__(request.args.to_dict())


class PathSource(Const[list[str]]):
    def __init__(self) -> None:
        segments = request.path.strip("/").split("/")
        super().__init__(segments)


class BufferSink(Adaptor["BufferSink.Kwargs", tuple[Text, int]]):
    """Sink the last value output to a buffer."""

    class Kwargs(Args):
        buf: io.BytesIO

    def __call__(self, **kwargs: Unpack[Kwargs]) -> Out[tuple[Text, int]]:
        buf = kwargs["buf"]
        return (buf.getvalue(), 200), {}


class NameOutput[T](Adaptor[Args, T]):
    """Give a kwarg name to the last value output."""

    def __init__(self, name: str) -> None:
        self.name = name

    def __call__(self, **kwargs: Unpack[Args]) -> Out[T]:
        new_kwargs = copy.copy(kwargs)
        new_kwargs[self.name] = new_kwargs["__last__"]
        return new_kwargs["__last__"], new_kwargs


class Kwargs[K, U](Adaptor[K, U]):
    """Define a set of default kwargs."""

    def __init__(self, **kwargs: K) -> None:
        self.kwargs = kwargs

    def __call__(self, **bindings: Unpack[K]) -> Out[K]:
        new_kwargs = copy.copy(self.kwargs)
        new_kwargs.update(bindings)
        logging.debug("%s, %s, %s", bindings, self.kwargs, new_kwargs)
        return new_kwargs.get("__last__"), new_kwargs


class Import[T](Adaptor[T, T]):
    """Imports available to the rest of the pipeline."""

    def __init__(self, *modules) -> None:
        self.modules = modules

    def __call__(self, **kwargs: Unpack[T]) -> Out[T]:
        for module in self.modules:
            importlib.import_module(module)
        return kwargs.get("__last__"), kwargs


class Install[T](Adaptor[T, T]):
    """Installs via pip."""

    def __init__(self, *packages) -> None:
        self.packages = list(packages)

    @classmethod
    def pip_install(cls, packages: Sequence[str]) -> None:
        subprocess.check_call([sys.executable, "-m", "pip", "install", *packages])

    def __call__(self, **kwargs: Unpack[T]) -> Out[T]:
        Install.pip_install(self.packages)
        return kwargs.get("__last__"), kwargs
