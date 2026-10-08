from __future__ import annotations

import io
import json
import unittest
from types import SimpleNamespace
from unittest import mock

from arweave import transaction_uploader as uploader_module


class SyntheticTransaction:
    api_url = "https://synthetic.invalid"

    def __init__(self, count):
        self.chunks = {"chunks": [{} for _ in range(count)], "data_root": b"synthetic"}
        self.data = b"public synthetic payload"

    @property
    def json_data(self):
        return json.dumps({"id": "SYNTHETIC", "data": "present" if self.data else ""})

    def to_dict(self):
        return {"id": "SYNTHETIC", "data": ""}

    def get_chunk(self, index):
        if index >= len(self.chunks["chunks"]):
            raise IndexError("synthetic chunk boundary")
        return {
            "chunk": b"c3ludGhldGlj",
            "data_path": b"c3ludGhldGlj",
            "offset": str(index),
            "data_size": "2",
        }


class UploaderFaultTests(unittest.TestCase):
    def setUp(self):
        self.validate = mock.patch.object(uploader_module, "validate_path", return_value=True)
        self.sleep = mock.patch.object(
            uploader_module.time,
            "sleep",
            side_effect=AssertionError("real retry sleep is forbidden"),
        )
        self.validate.start()
        self.sleep.start()

    def tearDown(self):
        self.sleep.stop()
        self.validate.stop()

    def test_single_body_success_advances_once_and_refuses_duplicate(self):
        calls = []

        def success(url, **_kwargs):
            calls.append(url)
            return SimpleNamespace(status_code=200, text="{}")

        with mock.patch.object(uploader_module.requests, "post", side_effect=success):
            transaction = SyntheticTransaction(1)
            uploader = uploader_module.TransactionUploader(transaction=transaction, file_handler=io.BytesIO())
            uploader.upload_chunk()
            self.assertTrue(uploader.is_complete)
            self.assertEqual((uploader.chunk_index, len(calls)), (1, 1))
            with self.assertRaises(uploader_module.TransactionUploaderException):
                uploader.upload_chunk()
            self.assertEqual(len(calls), 1)

    def test_multiple_chunks_advance_only_after_acknowledgement(self):
        calls = []

        def success(url, **_kwargs):
            calls.append(url.rsplit("/", 1)[-1])
            return SimpleNamespace(status_code=200, text="{}")

        with mock.patch.object(uploader_module.requests, "post", side_effect=success):
            uploader = uploader_module.TransactionUploader(transaction=SyntheticTransaction(2), file_handler=io.BytesIO())
            uploader.upload_chunk()
            self.assertEqual((uploader.tx_posted, uploader.chunk_index), (True, 1))
            uploader.upload_chunk()
            self.assertTrue(uploader.is_complete)
            self.assertEqual(calls, ["tx", "chunk", "chunk"])

    def test_uncertain_transport_outcome_is_not_retried_or_advanced(self):
        with mock.patch.object(
            uploader_module.requests, "post", side_effect=TimeoutError("synthetic uncertain outcome")
        ) as transport:
            uploader = uploader_module.TransactionUploader(transaction=SyntheticTransaction(1), file_handler=io.BytesIO())
            with self.assertRaises(TimeoutError):
                uploader.upload_chunk()
            self.assertEqual(transport.call_count, 1)
            self.assertFalse(uploader.tx_posted)
            self.assertEqual(uploader.chunk_index, 0)

    def test_rejection_does_not_advance_and_legacy_retry_bug_is_explicit(self):
        response = SimpleNamespace(status_code=500, text='{"error":"synthetic"}')
        with mock.patch.object(uploader_module.requests, "post", return_value=response) as transport:
            uploader = uploader_module.TransactionUploader(transaction=SyntheticTransaction(1), file_handler=io.BytesIO())
            with self.assertRaises(uploader_module.TransactionUploaderException):
                uploader.upload_chunk()
            self.assertEqual((uploader.tx_posted, uploader.chunk_index, transport.call_count), (False, 0, 1))
            with self.assertRaises(TypeError):
                uploader.upload_chunk()
            self.assertEqual(transport.call_count, 1)

    def test_persisted_resume_serialization_limitation_is_preserved(self):
        uploader = uploader_module.TransactionUploader(transaction=SyntheticTransaction(1), file_handler=io.BytesIO())
        serialized = json.loads(uploader.to_json())
        self.assertIs(serialized["lastResponseError"], False)
        self.assertNotIn("txPosted", serialized)


if __name__ == "__main__":
    unittest.main()
