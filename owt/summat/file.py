from . import adaptor
from typing import Unpack, TypedDict
import os
import io


class LoadFile(adaptor.Adaptor["LoadFile.Kwargs", io.BytesIO]):
    class Kwargs(TypedDict):
        path: str

    def __init__(self, root_dir: str | None = None) -> None:
        # If a root directory is set, it cannot be overridden by a kwarg.
        self.root_dir = root_dir

    def __call__(self, **kwargs: Unpack[Kwargs]) -> adaptor.Out[io.BytesIO]:
        path = kwargs["path"]
        if self.root_dir is not None:
            path = os.path.join(self.root_dir, path)
        with open(path, "rb") as f:
            return io.BytesIO(f.read()), {}
