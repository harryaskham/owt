import argparse
import urllib.parse
import requests
import sys
import base64
import logging


parser = argparse.ArgumentParser(description="Owt CLI")
parser.add_argument(
    "--address",
    default="http://localhost:9876/owt",
    help="Address of Owt server to call",
)
code_run = parser.add_mutually_exclusive_group(required=True)
code_run.add_argument(
    "--code",
    help="Code defining the run function",
)
code_run.add_argument(
    "--run",
    help="Code containing the run function",
)
kwargs_group = parser.add_mutually_exclusive_group()
kwargs_group.add_argument("--kwargs", help="Kwargs to call with (as valid python dict)")
kwargs_group.add_argument(
    "--arg", nargs=2, action="append", help="Args as --arg name value"
)
parser.add_argument("--method", default="GET", help="HTTP method to use")
parser.add_argument("--fn-name", default="run", help="Runner function name")
# Switch to only print URL
parser.add_argument("--url", action="store_true", help="Print URL only")


def call_owt(
    address: str, method: str, code: str, kwargs: str, fn_name: str, url_only: bool
) -> bytes:
    code_b64 = base64.b64encode(code.encode())
    kwargs_b64 = base64.b64encode(kwargs.encode())
    data = {
        "code_b64": code_b64,
        "kwargs_b64": kwargs_b64,
    }

    if url_only:
        return (f"{address}?{urllib.parse.urlencode(data)}").encode()

    match method.lower():
        case "get":
            return requests.get(address, params=data).content
        case "post":
            return requests.post(address, json=data).content
        case m:
            raise ValueError(f"Unsupported method: {m}")


def main():
    try:
        args = parser.parse_args()
    except argparse.ArgumentError as e:
        logging.error(f"Error parsing arguments: {e}")
        sys.exit(1)
    result = call_owt(
        address=args.address,
        method=args.method,
        code=(args.code or f"run = {args.run}"),
        kwargs=(
            args.kwargs
            or "{%s}" % ",".join([f"'{a[0]}': {a[1]}" for a in args.arg])
            or "{}"
        ),
        fn_name=args.fn_name,
        url_only=args.url,
    )
    sys.stdout.buffer.write(result)


if __name__ == "__main__":
    sys.exit(main())
