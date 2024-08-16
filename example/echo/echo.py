def run(request, name=None):
    # Loads from either the free-text path or the request body
    if not name:
        name = request.path.split("/")[-1]
    return f"Hello, {name}!"
