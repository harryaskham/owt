import base64
import pytest
from flask.testing import FlaskClient
from owt.server import app, Server

def test_hello_world(client: FlaskClient):
    code = """
def run(name):
    return f"Hello {name}!"
"""
    
    code_b64 = base64.b64encode(code.encode()).decode()
    kwargs = '{"name": "World"}'
    kwargs_b64 = base64.b64encode(kwargs.encode()).decode()
    
    response = client.get(
        "/test",
        query_string={
            "code_b64": code_b64,
            "kwargs_b64": kwargs_b64,
        }
    )
    
    assert response.status_code == 200
    assert response.data.decode() == "Hello World!"


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

pytest.fixture(autouse=True)
def init_server():
    app.config['TESTING'] = True
    Server.serve(address="127.0.0.1", port=9876, auth=None)