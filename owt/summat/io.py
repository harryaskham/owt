from . import adaptor
from .adaptor import Args, Adaptor, Out
from typing import Text, Unpack
import io
import copy


class BufferSink(adaptor.Adaptor['BufferSink.Kwargs', tuple[Text, int]]):
    class Kwargs(adaptor.Args):
        buf: io.BytesIO

    def __call__(self, **kwargs: Unpack[Kwargs]) -> Out[tuple[Text, int]]:
        buf = kwargs["buf"]
        return (buf.getvalue(), 200), {}

   
class NameOutput[T](Adaptor[Args, T]):
    def __init__(self, name: str) -> None:
        self.name = name

    def __call__(self, **kwargs: Unpack[Args]) -> Out[T]:
        new_kwargs = copy.copy(kwargs)
        new_kwargs[self.name] = new_kwargs["__last__"]
        return new_kwargs["__last__"], new_kwargs
