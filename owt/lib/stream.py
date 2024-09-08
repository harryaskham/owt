import json

def event(**kwargs):
    return "data: %s\n\n" % (json.dumps(kwargs))

def done():
    return "data: [DONE]\n\n"

def response(generator, *args, **kwargs):
    return generator(*args, **kwargs), {"Content-Type": "text/event-stream"}
