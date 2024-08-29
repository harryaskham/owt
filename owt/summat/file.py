from owt.summat.functional import F
import os
from typing import Any
import io


class LoadFile(F[[Any], io.BytesIO]):

    def __init__(self, root_dir: str | None = None) -> None:
        # If a root directory is set, it cannot be overridden by a kwarg.
        self.root_dir = root_dir

        def f(__last__: Any, **kwargs) -> io.BytesIO:
            path = str(__last__)
            if self.root_dir is not None:
                path = os.path.join(self.root_dir, path)
            with open(path, "rb") as f:
                return io.BytesIO(f.read())

        super().__init__(f)
