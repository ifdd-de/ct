"""A stand-in for ``requests.Session`` that records requests and replays answers.

    session = FakeSession(Response(201), Response(406, {"message": "bad"}))
    ...
    session.calls[0].method, session.calls[0].url, session.calls[0].json

Answers are used in order; when none are left, requests get 201 and token
requests get a fresh token.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


class Response:
    def __init__(self, status: int = 200, body: Any = None):
        self.status_code = status
        self._body = {"message": "ok"} if body is None else body
        self.text = self._body if isinstance(self._body, str) else json.dumps(self._body)
        self.headers: dict[str, str] = {"content-type": "application/json"}
        self.url = ""

    def json(self) -> Any:
        if isinstance(self._body, str):
            raise ValueError("not JSON")
        return self._body


def token(value: str = "t1", expires_in: int = 300) -> Response:
    return Response(200, {"access_token": value, "expires_in": expires_in})


@dataclass
class Call:
    method: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    json: Any = None
    form: Any = None
    params: Any = None
    timeout: Any = None


class FakeSession:
    def __init__(self, *answers: Response):
        self.answers = list(answers)
        self.calls: list[Call] = []
        self.verify: Any = True

    # requests.Session API used by ifdd.ct.http.Http
    def request(self, method, url, headers=None, data=None, params=None, timeout=None, **_):
        self.calls.append(Call(method, url, dict(headers or {}),
                               json.loads(data) if data else None, None, params, timeout))
        return self.answers.pop(0) if self.answers else Response(201)

    def post(self, url, data=None, timeout=None, **_):
        self.calls.append(Call("TOKEN", url, form=data, timeout=timeout))
        return self.answers.pop(0) if self.answers else token()

    def get(self, url, headers=None, **kwargs):  # used by the JSON-LD loader
        self.calls.append(Call("GET", url, dict(headers or {})))
        return self.answers.pop(0) if self.answers else Response(404, {})

    # conveniences for assertions
    def requests(self, method: str | None = None) -> list[Call]:
        return [c for c in self.calls if c.method != "TOKEN" and (method is None or c.method == method)]

    def token_requests(self) -> list[Call]:
        return [c for c in self.calls if c.method == "TOKEN"]
