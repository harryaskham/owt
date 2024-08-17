# example/echo/echo.py

from owt.server import Server


def run(name=None):
    return f"Hello, {name}, from {Server.sing().address}:{Server.sing().port}!"
