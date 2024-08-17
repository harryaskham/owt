from typing import Callable, TypeVar, Any, reveal_type, Optional, Protocol, Mapping
import hashlib
import urllib
import asyncio
from collections import defaultdict
import base64
import logging
import os
import json
from dataclasses import dataclass
import dataclasses
from multiprocessing.connection import Client
from flask import (
    Flask,
    Request,
    Response,
    jsonify,
    send_file,
    send_from_directory,
    render_template,
    url_for,
    current_app,
)
import flask
from flask_cors import CORS
from flask_httpauth import HTTPBasicAuth
import requests
from multiprocessing import Process
import bark
import argparse
from logging.config import dictConfig

type Kwargs = Mapping[str, Any]


class OwtAdaptor[T](Protocol):
    def run(self, request: flask.Request, **kwargs: T) -> flask.Response: ...
