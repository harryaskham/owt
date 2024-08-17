# example/echo/echo.py

from owt import Server


def run(name=None):
    return f"Hello, {name}, from {Server.sing().address}:{Server.sing().port}!"
