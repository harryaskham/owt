# example/bootstrap/bootstrap.py
from owt import args


def run(request, payload_code_b64, payload_kwargs_b64):
    import os

    return os.popen(
        f'source ./example/meta/bootstrap.sh; $(owtInOwt http://localhost {args.port} "{payload_code_b64}" "{payload_kwargs_b64}")'
    ).read()
