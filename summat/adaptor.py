from typing import Any, Protocol, Mapping
import flask

type Kwargs = Mapping[str, Any]


class OwtAdaptor[T](Protocol):
    def run(self, request: flask.Request, **kwargs: T) -> flask.Response: ...
