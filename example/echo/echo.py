def run(request, name=None):
    return f"Hello, {name}, from {Server.sing().address}:{Server.sing().port}!"
