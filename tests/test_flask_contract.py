from __future__ import annotations

import contextlib
import importlib.util
import io
import pathlib
import socket
import sys
import unittest
from unittest import mock

import requests
from werkzeug.datastructures import FileStorage


ROOT = pathlib.Path(__file__).resolve().parents[1]
CSS_URL = "https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css"
CSS_SRI = "sha384-sRIl4kxILFvY47J16cr9ZwB07vP4J8+LH7qKQnuqkuIAvNWLzeN8tE5YBujZqJLB"
JS_URL = "https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/js/bootstrap.bundle.min.js"
JS_SRI = "sha384-FKyoEForCGlyvwx9Hj09JcYn3nv7wiPVlz7YYwJrWVcXK/BmnVDxM+D2scQbITxI"


class SyntheticWallet:
    balance = "1.25"
    address = "synthetic-address"

    def __init__(self, *_args, **_kwargs):
        pass

    def get_last_transaction_id(self):
        return "synthetic-transaction-id"


class SyntheticTransaction:
    id = "synthetic-upload-transaction-id"

    def __init__(self, *_args, **_kwargs):
        self.tags = []

    def get_status(self):
        return {"confirmed": {"block_height": 1}}

    def get_data(self):
        return "synthetic response"

    def add_tag(self, *args):
        self.tags.append(args)

    def sign(self):
        pass


class SyntheticUploader:
    uploaded_chunks = 0
    total_chunks = 2
    pct_complete = 0

    @property
    def is_complete(self):
        return self.uploaded_chunks == self.total_chunks

    def upload_chunk(self):
        if self.uploaded_chunks >= self.total_chunks:
            raise AssertionError("synthetic upload exceeded its bound")
        self.uploaded_chunks += 1
        self.pct_complete = self.uploaded_chunks * 50


class FlaskContractTests(unittest.TestCase):
    def test_all_twenty_one_contract_checks_without_external_requests(self):
        network_attempts = []
        saved_files = []
        removed_files = []
        uploaders = []

        def deny(*_args, **_kwargs):
            network_attempts.append(True)
            raise AssertionError("network prohibited in Flask compatibility validation")

        def save_file(_self, filename, *_args, **_kwargs):
            saved_files.append(str(filename))

        def make_uploader(*_args, **_kwargs):
            uploader = SyntheticUploader()
            uploaders.append(uploader)
            return uploader

        checks = []
        with (
            mock.patch.object(requests.sessions.Session, "request", deny),
            mock.patch.object(socket, "create_connection", deny),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            name = "arweave_dependency_contract_test"
            specification = importlib.util.spec_from_file_location(name, ROOT / "run.py")
            module = importlib.util.module_from_spec(specification)
            sys.modules[name] = module
            specification.loader.exec_module(module)
            module.app.config["TESTING"] = True
            expected = {
                ("/", "GET"),
                ("/uploader", "GET"),
                ("/uploader", "POST"),
                ("/wallet", "GET"),
                ("/lastTransaction", "GET"),
                ("/upload", "GET"),
                ("/upload", "POST"),
                ("/search", "GET"),
                ("/search", "POST"),
                ("/test1", "GET"),
                ("/test1", "POST"),
            }
            actual = {
                (rule.rule, method)
                for rule in module.app.url_map.iter_rules()
                if rule.rule != "/static/<path:filename>"
                for method in rule.methods
                if method not in {"HEAD", "OPTIONS"}
            }
            self.assertEqual(actual, expected)
            checks.append("11 route/method contracts")
            client = module.app.test_client()
            with (
                mock.patch.object(module.arweave, "Wallet", SyntheticWallet),
                mock.patch.object(module, "Transaction", SyntheticTransaction),
                mock.patch.object(module, "get_uploader", side_effect=make_uploader),
                mock.patch.object(FileStorage, "save", save_file),
                mock.patch.object(module.os, "remove", side_effect=lambda path: removed_files.append(str(path))),
                mock.patch.object(module, "open", create=True, side_effect=lambda *_a, **_k: io.BytesIO(b"synthetic document")),
            ):
                for url in ("/", "/uploader", "/wallet", "/lastTransaction", "/upload", "/search"):
                    response = client.get(url)
                    self.assertEqual(response.status_code, 200)
                    self.assertTrue(response.content_type.startswith("text/html"))
                    checks.append("GET " + url)
                for url in ("/uploader", "/lastTransaction", "/upload"):
                    markup = client.get(url).get_data(as_text=True)
                    self.assertNotIn("bootstrap@5.0.2", markup)
                    self.assertIn(CSS_URL, markup)
                    self.assertIn(CSS_SRI, markup)
                    self.assertIn(JS_URL, markup)
                    self.assertIn(JS_SRI, markup)
                    checks.append("Bootstrap URL/SRI " + url)
                response = client.post(
                    "/uploader",
                    data={"file": (io.BytesIO(b"synthetic wallet input"), "wallet.json")},
                )
                self.assertEqual(response.status_code, 200)
                checks.append("wallet upload")
                module.wallet = SyntheticWallet()
                response = client.get("/wallet")
                self.assertEqual(response.status_code, 200)
                self.assertIn(b"synthetic-address", response.data)
                checks.append("wallet render")
                response = client.get("/lastTransaction")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(set(response.get_json()), {"id", "status"})
                checks.append("last transaction JSON")
                response = client.post(
                    "/upload",
                    data={"file": (io.BytesIO(b"synthetic document"), "../../document.txt")},
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(uploaders[-1].uploaded_chunks, 2)
                self.assertTrue(any(path.replace("\\", "/").endswith("/document.txt") for path in saved_files))
                checks.append("sanitized upload")
                self.assertEqual(client.post("/search", data={"id": "synthetic-id"}).status_code, 200)
                checks.append("search POST")
                for method in ("get", "post"):
                    response = getattr(client, method)("/test1", query_string={"token": "synthetic-token"})
                    self.assertEqual(response.status_code, 200)
                    self.assertTrue(response.is_json)
                    checks.append("test1 " + method)
                self.assertEqual(client.post("/uploader", data={}).status_code, 400)
                checks.append("missing wallet")
                for field, invoke in (
                    ("id", lambda: client.post("/search", data={})),
                    ("token", lambda: client.get("/test1")),
                ):
                    with self.assertRaises(KeyError) as caught:
                        invoke()
                    self.assertEqual(caught.exception.args, (field,))
                    checks.append("missing " + field)
                before = len(uploaders)
                response = client.post("/upload", data={})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(len(uploaders), before)
                checks.append("missing document")
            sys.modules.pop(name, None)
        self.assertEqual(len(checks), 21)
        self.assertEqual(network_attempts, [])
        self.assertGreaterEqual(len(removed_files), 1)


if __name__ == "__main__":
    unittest.main()
