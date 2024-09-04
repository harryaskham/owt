from owt.summat.adaptor import Adaptor, CallOut, PassKWs
from owt.summat.functional import Const, Exec, F
from typing import Any, Callable
import subprocess
import sys
import importlib
import copy
from flask import request
import json


class Input[**T](Adaptor[Any, T.kwargs]):
    """Re-seed the pipeline with the initial input kwargs."""

    def __init__(self, get_input: Callable[[], T.kwargs]) -> None:
        self.get_input = get_input

    def call(self, **kwargs) -> CallOut[T.kwargs]:
        kws = self.get_input()
        return PassKWs(kws)


class JSONDataSource(Const[Any]):
    def __init__(self) -> None:
        super().__init__(json.loads(request.data))


class QuerySource(Const[dict[str, str]]):
    def __init__(self) -> None:
        super().__init__(request.args.to_dict())


class PathSource(Const[list[str]]):
    def __init__(self) -> None:
        super().__init__(request.path.strip("/").split("/"))


class NameOutput[**T, U](Adaptor[T, U]):
    """Give a kwarg name to the last value output."""

    def __init__(self, name: str) -> None:
        self.name = name

    def call(self, **kwargs: T.kwargs) -> CallOut[U]:
        new_kwargs = copy.copy(kwargs)
        new_kwargs[self.name] = new_kwargs["__last__"]
        return PassKWs(new_kwargs)


class Kwargs[**T, U](Adaptor[T, U]):
    """Define a set of default kwargs."""

    def __init__(self, **kwargs: T.kwargs) -> None:
        self.kwargs = kwargs

    def call(self, **bindings: T.kwargs) -> CallOut[U]:
        new_kwargs = copy.copy(self.kwargs)
        new_kwargs.update(bindings)
        return PassKWs(new_kwargs)


class Import[**T, U](Exec[T, U]):
    """Imports available to the rest of the pipeline."""

    def __init__(self, *modules: str | Callable[[], Any]) -> None:
        def f(*_: T.args, **kwargs: T.kwargs):
            for module in modules:
                match module:
                    case str():
                        importlib.import_module(module)
                    case _:
                        module()

        super().__init__(f)


class Install[**T, U](Exec[T, U]):
    """Installs via pip."""

    @classmethod
    def pip_install(cls, *packages: str) -> None:
        subprocess.check_call([sys.executable, "-m", "pip", "install", *packages])

    def __init__(self, *packages: str) -> None:
        def f(*args: T.args, **kwargs: T.kwargs):
            self.pip_install(*packages)

        super().__init__(f)


class Shell(F[[str], bytes]):
    @classmethod
    def run_cmd(cls, cmd: str) -> bytes:
        return subprocess.run(["bash", "-c", cmd], stdout=subprocess.PIPE).stdout

    def __init__(self) -> None:
        def f(cmd: str) -> bytes:
            return self.run_cmd(cmd)

        super().__init__(f)
