from __future__ import annotations

import base64
import copy
import csv
import hashlib
import importlib.util
import io
import json
import os
import pathlib
import tempfile
import tomllib
import unittest
from unittest import mock
import zipfile


ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "arweave_bootstrap_locked", ROOT / "tools" / "bootstrap_locked.py"
)
INSTALLER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INSTALLER)


def write_wheel(path, payload_name="demo.py", payload=b"value = 1\n", valid=True, duplicate=False):
    digest = base64.urlsafe_b64encode(hashlib.sha256(payload).digest()).rstrip(b"=").decode("ascii")
    if not valid:
        digest = "A" * len(digest)
    record_name = "demo-1.0.dist-info/RECORD"
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow([payload_name, "sha256=" + digest, str(len(payload))])
    writer.writerow([record_name, "", ""])
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(payload_name, payload)
        if duplicate:
            archive.writestr(payload_name, payload)
        archive.writestr(record_name, output.getvalue())


class DependencyLockTests(unittest.TestCase):
    def test_exact_lock_roots_cardinality_and_forbidden_absence(self):
        lock = tomllib.loads((ROOT / "pylock.toml").read_text(encoding="utf-8"))
        names = {INSTALLER.canonicalize_name(item["name"]) for item in lock["packages"]}
        self.assertEqual(len(lock["packages"]), 21)
        self.assertEqual(len(names), 21)
        self.assertTrue(set(INSTALLER.DIRECT_ROOTS).issubset(names))
        self.assertTrue({"python-jose", "ecdsa", "pynacl", "psutil", "arweave-python-client"}.isdisjoint(names))

    def test_bootstrap_manifest_is_exact_two_package_boundary(self):
        manifest = json.loads((ROOT / "bootstrap-lock.json").read_text(encoding="utf-8"))
        identities = {(item["name"], item["version"]) for item in manifest["packages"]}
        self.assertEqual(identities, {("installer", "1.0.1"), ("packaging", "26.3")})

    def test_record_validator_accepts_complete_strong_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            wheel = pathlib.Path(directory) / "demo-1.0-py3-none-any.whl"
            write_wheel(wheel)
            INSTALLER.validate_record(wheel)

    def test_record_validator_rejects_traversal_tamper_and_duplicate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            traversal = root / "traversal.whl"
            write_wheel(traversal, "../escape.py")
            with self.assertRaisesRegex(ValueError, "unsafe or duplicate"):
                INSTALLER.validate_record(traversal)
            tampered = root / "tampered.whl"
            write_wheel(tampered, valid=False)
            with self.assertRaisesRegex(ValueError, "RECORD content mismatch"):
                INSTALLER.validate_record(tampered)
            duplicate = root / "duplicate.whl"
            write_wheel(duplicate, duplicate=True)
            with self.assertRaisesRegex(ValueError, "unsafe or duplicate"):
                INSTALLER.validate_record(duplicate)

    def test_outer_hash_mismatch_fails_before_import_or_install(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            wheel = root / "demo-1.0-py3-none-any.whl"
            write_wheel(wheel)
            descriptor = {
                "url": "https://files.pythonhosted.org/packages/demo/demo-1.0-py3-none-any.whl",
                "size": wheel.stat().st_size,
                "hashes": {"sha256": "0" * 64},
            }
            with self.assertRaisesRegex(ValueError, "size/hash mismatch"):
                INSTALLER.validate_outer_wheel(root, descriptor)

    def test_unsupported_interpreter_and_machine_fail_closed(self):
        with mock.patch.object(INSTALLER.sys, "version_info", (3, 11, 9)):
            with self.assertRaisesRegex(ValueError, "exact Python"):
                INSTALLER.validate_runtime()
        with (
            mock.patch.object(INSTALLER.sys, "version_info", (3, 13, 16)),
            mock.patch.object(INSTALLER.sys, "platform", "linux"),
            mock.patch.object(INSTALLER.platform, "machine", return_value="aarch64"),
        ):
            with self.assertRaisesRegex(ValueError, "unsupported platform"):
                INSTALLER.validate_runtime()

    def test_real_lock_selects_exact_graph_when_reviewed_wheelhouse_is_supplied(self):
        wheelhouse_value = os.environ.get("ARWEAVE_WHEELHOUSE")
        self.assertTrue(wheelhouse_value, "ARWEAVE_WHEELHOUSE is required for the supply-chain gate")
        wheelhouse = pathlib.Path(wheelhouse_value)
        packaging_path, _installer_path, _manifest = INSTALLER.load_bootstrap(
            ROOT / "bootstrap-lock.json", wheelhouse
        )
        selected, identities, graph = INSTALLER.select_and_verify(
            ROOT / "pylock.toml", wheelhouse, packaging_path
        )
        self.assertEqual((len(selected), len(identities), graph["packages"], graph["unresolved"]), (21, 21, 21, 0))


if __name__ == "__main__":
    unittest.main()
