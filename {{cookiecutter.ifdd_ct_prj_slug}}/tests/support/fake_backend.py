"""A tiny HTTP server that behaves like ifdd-be for the parts ct uses.

* POST /token                       client credentials -> access token
* PUT/PATCH /{segment}/{id}         create/replace or merge; 401 without token
* GET /{segment}?start=&end=        documents of that aspect
* GET /{segment}/{id}               one node

It keeps one document per (@id, @context) and answers "No changes
detected" for identical content. Like ifdd-be it takes the c_* cache metadata
out before it stores and compares (ifdd-be keeps them in columns); unlike
ifdd-be it has no valid time: the last write of a key wins, so an earlier
version of the faker followed by the current one counts as two changes on
every run. The real behaviour is covered by tests/integration against
ifdd-be-core. Runs in a thread on a free port.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

CLIENT_ID = "ifdd-ct-test"
CLIENT_SECRET = "s3cret"
TOKEN = "e2e-token"


class FakeBackend:
    def __init__(self):
        self.store: dict[tuple[str, str], dict] = {}
        self.log: list[tuple[str, str, int]] = []
        backend = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):  # keep test output clean
                pass

            def reply(self, status, body):
                # Log before answering: the client may look at the log as soon
                # as it has the answer, before this thread gets to run again.
                backend.log.append((self.command, self.path, status))
                data = json.dumps(body).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def body(self):
                return self.rfile.read(int(self.headers.get("Content-Length", 0))).decode()

            def authorised(self):
                if self.headers.get("Authorization") == f"Bearer {TOKEN}":
                    return True
                self.reply(401, {"detail": "Not authenticated"})
                return False

            def do_POST(self):
                form = parse_qs(self.body())
                if self.path == "/token" and form.get("grant_type") == ["client_credentials"] \
                        and form.get("client_id") == [CLIENT_ID] \
                        and form.get("client_secret") == [CLIENT_SECRET]:
                    return self.reply(200, {"access_token": TOKEN, "expires_in": 300})
                self.reply(401, {"error": "invalid_client"})

            def do_PUT(self):
                self.write(merge=False)

            def do_PATCH(self):
                self.write(merge=True)

            def write(self, merge):
                if not self.authorised():
                    return
                node = json.loads(self.body())
                doc = node.get("json", {})
                if "@id" not in doc or "@context" not in doc:
                    return self.reply(406, {"message": "@id or @context not found in data"})
                key = (doc["@id"], doc["@context"])
                doc = {k: v for k, v in doc.items() if not k.startswith("c_")}
                if merge:
                    if key not in backend.store:
                        return self.reply(404, {"detail": "Node not found"})
                    doc = {**backend.store[key], **doc}
                if backend.store.get(key) == doc:
                    return self.reply(200, {"message": "No changes detected"})
                created = key not in backend.store
                backend.store[key] = doc
                if created:
                    return self.reply(201, {"message": "Node created successfully"})
                self.reply(200, {"message": "Node updated successfully"})

            def do_GET(self):
                if not self.authorised():
                    return
                parts = [p for p in urlparse(self.path).path.split("/") if p]
                if len(parts) == 2:
                    found = [d for (i, _), d in backend.store.items() if urlparse(i).path == self.path]
                    return self.reply(200, found[0]) if found else self.reply(404, {"detail": "Node not found"})
                # Like ifdd-be: a list shows the aspect context of the segment
                # only (products -> product.jsonld), not base or domain contexts.
                segment = parts[0]
                aspect_file = f"/{segment[:-1]}.jsonld"
                self.reply(200, [d for (i, c), d in backend.store.items()
                                 if f"/{segment}/" in i and c.endswith(aspect_file)])

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()

    def statuses(self, method: str) -> list[int]:
        return [status for m, _, status in self.log if m == method]
