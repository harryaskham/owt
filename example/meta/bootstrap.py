# example/meta/bootstrap.py


def run(**kwargs):
    from owt.server import Server
    import os

    payload_code_b64 = kwargs["payload_code_b64"]
    payload_kwargs_b64 = kwargs["payload_kwargs_b64"]
    return os.popen(
        f'source ./example/meta/bootstrap.sh; $(owtInOwt http://localhost {Server.sing().port} "{payload_code_b64}" "{payload_kwargs_b64}")'
    ).read()
