import argparse
import requests
import sys
import base64
import logging

def call_owt(address: str, code: str, kwargs: str) -> bytes:
    code_b64 = base64.b64encode(code.encode()).decode()
    kwargs_b64 = base64.b64encode(kwargs.encode()).decode()
    r = requests.post(
        address,
        json={
            "code_b64": code_b64,
            "kwargs_b64": kwargs_b64,
        },
    )
    return r.content

parser = argparse.ArgumentParser(
    description="Owt CLI"
)
parser.add_argument(
    "--address",
    default="http://localhost:9876",
    help="Address of Owt server to call",
)
parser.add_argument(
    "--code", default="run = pipe().f(lambda _: 'Hello Owt!').done()", help="Code defining the run function")
parser.add_argument(
    "--kwargs", default="{}", help="Kwargs to call with")

def main():
    try:
        args = parser.parse_args()
    except argparse.ArgumentError as e:
        logging.error(f"Error parsing arguments: {e}")
        sys.exit(1)
    result = call_owt(args.address, args.code, args.kwargs)
    sys.stdout.buffer.write(result)


if __name__ == "__main__":
    sys.exit(main())
