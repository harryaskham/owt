# example/meta/bootstrap.py


def run(**kwargs):
    from flask import request
    import os

    payload_code_b64 = kwargs["payload_code_b64"]
    payload_kwargs_b64 = kwargs["payload_kwargs_b64"]
    print(request.base_url)
    return os.popen(
        f'source ./example/meta/bootstrap.sh; $(owtInOwt "{request.base_url}" "{payload_code_b64}" "{payload_kwargs_b64}")'
    ).read()
