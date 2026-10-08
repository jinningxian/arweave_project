"""Install the reviewed PEP 751 lock into an empty, pip-free virtualenv.

All wheels must already exist in ``--wheelhouse``.  This program validates
outer size/SHA-256, archive paths, every RECORD row, wheel compatibility,
metadata identity and dependency closure before importing the pinned PyPA
``packaging`` and ``installer`` wheels.  It never downloads artifacts.
"""

from __future__ import annotations

import argparse
import base64
import csv
import email.parser
import hashlib
import importlib.metadata
import io
import json
import os
import pathlib
import platform
import re
import runpy
import socket
import stat
import sys
import tomllib
import urllib.parse
import zipfile


ALLOWED_PYTHONS = {(3, 12, 15), (3, 13, 16), (3, 14, 8)}
EXPECTED_PACKAGES = 21
FORBIDDEN = {"pip", "setuptools", "wheel", "uv", "installer"}
DIRECT_ROOTS = {
    "flask": "3.1.3",
    "werkzeug": "3.1.9",
    "arrow": "1.4.0",
    "pyjwt": "2.15.1",
    "pycryptodome": "3.24.0",
    "cryptography": "50.0.2",
    "requests": "2.34.2",
}


def canonicalize_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _unsafe_windows_part(part: str) -> bool:
    stem = part.split(".", 1)[0].upper()
    devices = {"CON", "PRN", "AUX", "NUL"}
    devices.update({f"COM{number}" for number in range(1, 10)})
    devices.update({f"LPT{number}" for number in range(1, 10)})
    return stem in devices or part.endswith((" ", "."))


def validate_record(path: pathlib.Path) -> None:
    """Reject unsafe members and any wheel payload not bound by RECORD."""
    with zipfile.ZipFile(path) as archive:
        infos = [item for item in archive.infolist() if not item.is_dir()]
        names: dict[str, str] = {}
        expanded = 0
        for item in infos:
            name = item.filename
            parts = name.split("/")
            normalized = name.casefold()
            mode = (item.external_attr >> 16) & 0xFFFF
            if (
                not name
                or item.orig_filename != name
                or name.startswith("/")
                or "\\" in name
                or ":" in name
                or any(ord(character) < 32 or ord(character) == 127 for character in name)
                or any(part in {"", ".", ".."} or _unsafe_windows_part(part) for part in parts)
                or normalized in names
                or stat.S_ISLNK(mode)
                or (stat.S_IFMT(mode) not in {0, stat.S_IFREG})
                or item.flag_bits & 1
                or name.casefold().endswith(".pth")
            ):
                raise ValueError(f"unsafe or duplicate wheel member: {path.name}")
            names[normalized] = name
            expanded += item.file_size
            if item.file_size > 128 * 1024 * 1024 or expanded > 512 * 1024 * 1024:
                raise ValueError(f"wheel expansion bound exceeded: {path.name}")
        records = [item.filename for item in infos if item.filename.endswith(".dist-info/RECORD")]
        if len(records) != 1:
            raise ValueError(f"expected exactly one RECORD: {path.name}")
        rows = list(csv.reader(io.StringIO(archive.read(records[0]).decode("utf-8"))))
        mapping: dict[str, tuple[str, str]] = {}
        for row in rows:
            if len(row) != 3 or row[0] in mapping:
                raise ValueError(f"invalid or duplicate RECORD row: {path.name}")
            mapping[row[0]] = (row[1], row[2])
        actual_names = {item.filename for item in infos}
        if set(mapping) != actual_names:
            raise ValueError(f"RECORD membership mismatch: {path.name}")
        for name in actual_names:
            hash_field, size_field = mapping[name]
            if name == records[0]:
                if hash_field or size_field:
                    raise ValueError(f"RECORD self-row must be unsigned: {path.name}")
                continue
            if not hash_field or not size_field:
                raise ValueError(f"unsigned wheel payload: {path.name}")
            algorithm, encoded = hash_field.split("=", 1)
            if algorithm not in {"sha256", "sha384", "sha512"}:
                raise ValueError(f"weak RECORD hash: {path.name}")
            payload = archive.read(name)
            actual = base64.urlsafe_b64encode(
                hashlib.new(algorithm, payload).digest()
            ).rstrip(b"=").decode("ascii")
            if actual != encoded or len(payload) != int(size_field):
                raise ValueError(f"RECORD content mismatch: {path.name}")


def wheel_filename(descriptor: dict[str, object]) -> str:
    parsed = urllib.parse.urlsplit(str(descriptor.get("url", "")))
    filename = pathlib.PurePosixPath(parsed.path).name
    if (
        parsed.scheme != "https"
        or parsed.hostname != "files.pythonhosted.org"
        or parsed.username
        or parsed.password
        or not filename.endswith(".whl")
        or pathlib.PurePosixPath(filename).name != filename
    ):
        raise ValueError("wheel URL is outside official PyPI files")
    return filename


def validate_outer_wheel(
    wheelhouse: pathlib.Path, descriptor: dict[str, object]
) -> pathlib.Path:
    filename = wheel_filename(descriptor)
    path = (wheelhouse / filename).resolve()
    hashes = descriptor.get("hashes")
    if hashes is None and descriptor.get("sha256"):
        hashes = {"sha256": descriptor["sha256"]}
    if (
        path.parent != wheelhouse.resolve()
        or not path.is_file()
        or path.is_symlink()
        or not isinstance(hashes, dict)
        or set(hashes) != {"sha256"}
        or not isinstance(hashes["sha256"], str)
        or len(hashes["sha256"]) != 64
        or not isinstance(descriptor.get("size"), int)
        or descriptor["size"] <= 0
    ):
        raise ValueError(f"invalid or missing exact wheel: {filename}")
    if path.stat().st_size != descriptor["size"] or sha256_file(path) != hashes["sha256"]:
        raise ValueError(f"wheel size/hash mismatch: {filename}")
    validate_record(path)
    return path


def validate_runtime() -> None:
    if sys.version_info[:3] not in ALLOWED_PYTHONS:
        raise ValueError("exact Python 3.12.15, 3.13.16 or 3.14.8 is required")
    allowed = {"AMD64"} if sys.platform == "win32" else {"x86_64"}
    if sys.platform not in {"win32", "linux"} or platform.machine() not in allowed:
        raise ValueError("unsupported platform or architecture")


def load_bootstrap(
    bootstrap_path: pathlib.Path, wheelhouse: pathlib.Path
) -> tuple[pathlib.Path, pathlib.Path, dict[str, object]]:
    manifest = json.loads(bootstrap_path.read_text(encoding="utf-8"))
    if manifest.get("format") != "arweave-stdlib-bootstrap-v1":
        raise ValueError("bootstrap manifest format changed")
    if manifest.get("network_allowed") is not False or manifest.get("third_party_import_before_hash_record_validation") is not False:
        raise ValueError("bootstrap trust boundary changed")
    packages = manifest.get("packages")
    if not isinstance(packages, list) or len(packages) != 2:
        raise ValueError("exactly two bootstrap packages are required")
    descriptors = {canonicalize_name(str(item.get("name", ""))): item for item in packages}
    if set(descriptors) != {"packaging", "installer"}:
        raise ValueError("bootstrap package identities changed")
    if descriptors["packaging"].get("version") != "26.3" or descriptors["installer"].get("version") != "1.0.1":
        raise ValueError("bootstrap versions changed")
    packaging_path = validate_outer_wheel(wheelhouse, descriptors["packaging"])
    installer_path = validate_outer_wheel(wheelhouse, descriptors["installer"])
    return packaging_path, installer_path, manifest


def _metadata(path: pathlib.Path) -> dict[str, object]:
    with zipfile.ZipFile(path) as archive:
        members = [name for name in archive.namelist() if name.endswith(".dist-info/METADATA")]
        if len(members) != 1:
            raise ValueError(f"exactly one METADATA required: {path.name}")
        message = email.parser.BytesParser().parsebytes(archive.read(members[0]))
        wheel_members = [name for name in archive.namelist() if name.endswith(".dist-info/WHEEL")]
        if len(wheel_members) != 1:
            raise ValueError(f"exactly one WHEEL metadata file required: {path.name}")
        wheel_message = email.parser.BytesParser().parsebytes(archive.read(wheel_members[0]))
        license_files = message.get_all("License-File", [])
        metadata_version = message["Metadata-Version"] or ""
        dist_info = members[0].removesuffix("METADATA")
        validated_license_members = []
        for value in license_files:
            parts = value.split("/")
            if (
                not value
                or value.startswith("/")
                or "\\" in value
                or ":" in value
                or any(part in {"", ".", ".."} or _unsafe_windows_part(part) for part in parts)
            ):
                raise ValueError(f"unsafe legacy License-File path: {path.name}")
            member = dist_info + ("licenses/" if metadata_version >= "2.4" else "") + value
            if member not in archive.namelist():
                raise ValueError(f"legacy License-File member missing: {path.name}")
            validated_license_members.append(member)
    return {
        "name": canonicalize_name(message["Name"] or ""),
        "version": message["Version"] or "",
        "requires_python": message["Requires-Python"],
        "requires_dist": message.get_all("Requires-Dist", []),
        "provides_extra": message.get_all("Provides-Extra", []),
        "metadata_version": metadata_version,
        "license_files": license_files,
        "validated_license_members": validated_license_members,
        "wheel_version": wheel_message["Wheel-Version"],
        "wheel_tags": wheel_message.get_all("Tag", []),
    }


def select_and_verify(
    lock_path: pathlib.Path, wheelhouse: pathlib.Path, packaging_path: pathlib.Path
) -> tuple[list[pathlib.Path], list[dict[str, str]], dict[str, object]]:
    raw = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    if raw.get("lock-version") != "1.0" or raw.get("requires-python") != ">=3.12,<3.15":
        raise ValueError("lock format or Python contract changed")
    packages = raw.get("packages")
    if not isinstance(packages, list) or len(packages) != EXPECTED_PACKAGES:
        raise ValueError("lock package cardinality changed")
    if len({canonicalize_name(str(item.get("name", ""))) for item in packages}) != EXPECTED_PACKAGES:
        raise ValueError("missing or duplicate lock package")
    for package in packages:
        if any(key in package for key in ("sdist", "archive", "vcs", "directory")):
            raise ValueError("only exact binary wheels are permitted")
        wheels = package.get("wheels")
        if not isinstance(wheels, list) or not wheels:
            raise ValueError("every package requires wheels")

    sys.path.insert(0, str(packaging_path))
    try:
        from packaging.markers import default_environment
        from packaging.pylock import Pylock
        from packaging.requirements import Requirement
        from packaging.tags import parse_tag, sys_tags
        from packaging.utils import parse_wheel_filename
        from packaging.version import Version

        lock = Pylock.from_dict(raw)
        lock.validate()
        if not lock.requires_python.contains(Version(platform.python_version())):
            raise ValueError("interpreter outside lock Requires-Python")
        supported = set(sys_tags())
        selected: list[pathlib.Path] = []
        identities: list[dict[str, str]] = []
        metadata: dict[str, dict[str, object]] = {}
        for package, artifact in lock.select():
            descriptor = {
                "url": artifact.url,
                "size": artifact.size,
                "hashes": dict(artifact.hashes),
            }
            path = validate_outer_wheel(wheelhouse, descriptor)
            name, version, _build, tags = parse_wheel_filename(path.name)
            if (
                canonicalize_name(str(name)) != str(package.name)
                or version != package.version
                or not tags.intersection(supported)
            ):
                raise ValueError(f"wheel identity/tag mismatch: {path.name}")
            item = _metadata(path)
            if item["name"] != str(package.name) or item["version"] != str(package.version):
                raise ValueError(f"METADATA identity mismatch: {path.name}")
            if item["requires_python"] and not Requirement(
                f"placeholder{item['requires_python']}"
            ).specifier.contains(Version(platform.python_version())):
                raise ValueError(f"METADATA Requires-Python mismatch: {path.name}")
            recorded_tags = {
                tag for value in item["wheel_tags"] for tag in parse_tag(str(value))
            }
            if item["wheel_version"] != "1.0" or recorded_tags != set(tags):
                raise ValueError(f"WHEEL format/tag metadata mismatch: {path.name}")
            selected.append(path)
            identities.append({"name": str(package.name), "version": str(package.version), "filename": path.name, "sha256": sha256_file(path)})
            metadata[str(package.name)] = item
        if len(selected) != EXPECTED_PACKAGES or len(metadata) != EXPECTED_PACKAGES:
            raise ValueError("selected package cardinality changed")

        versions = {name: str(item["version"]) for name, item in metadata.items()}
        extras: dict[str, set[str]] = {}
        reachable: set[str] = set()
        pending = [
            Requirement(f"{name}{'[crypto]' if name == 'pyjwt' else ''}=={version}")
            for name, version in DIRECT_ROOTS.items()
        ]
        edges: set[tuple[str, str, str]] = set()
        environment = default_environment()
        while pending:
            requirement = pending.pop()
            name = canonicalize_name(requirement.name)
            if name not in versions or not requirement.specifier.contains(versions[name], prereleases=False):
                raise ValueError("missing or incompatible dependency: " + name)
            requested = set(requirement.extras)
            known = extras.setdefault(name, set())
            if name in reachable and requested.issubset(known):
                continue
            provided = set(metadata[name]["provides_extra"])
            if not requested.issubset(provided):
                raise ValueError("unknown requested extra: " + name)
            known.update(requested)
            reachable.add(name)
            for value in metadata[name]["requires_dist"]:
                child = Requirement(str(value))
                active = child.marker is None or any(
                    child.marker.evaluate(environment | {"extra": extra})
                    for extra in {"", *known}
                )
                if active:
                    edges.add((name, canonicalize_name(child.name), str(child)))
                    pending.append(child)
        if reachable != set(metadata):
            raise ValueError("lock contains unreachable or extra packages")
        residuals = [
            {
                "package": name,
                "metadata_version": item["metadata_version"],
                "license_files": item["license_files"],
                "validated_members": item["validated_license_members"],
                "raw_wheel_bytes_rewritten": False,
            }
            for name, item in sorted(metadata.items())
            if item["metadata_version"] == "2.1" and item["license_files"]
        ]
        graph = {"roots": len(DIRECT_ROOTS), "packages": len(metadata), "active_edges": len(edges), "unresolved": 0, "metadata_conformance_residuals": residuals}
        return selected, identities, graph
    finally:
        sys.path.remove(str(packaging_path))


def install(
    lock_path: pathlib.Path,
    bootstrap_path: pathlib.Path,
    wheelhouse: pathlib.Path,
    report_path: pathlib.Path,
) -> None:
    validate_runtime()
    lock_path = lock_path.resolve()
    bootstrap_path = bootstrap_path.resolve()
    wheelhouse = wheelhouse.resolve()
    report_path = report_path.resolve()
    if report_path.exists():
        raise ValueError("refusing to overwrite an existing report")
    if list(importlib.metadata.distributions()):
        raise ValueError("target environment must be empty")
    packaging_path, installer_path, bootstrap = load_bootstrap(bootstrap_path, wheelhouse)
    wheels, identities, graph = select_and_verify(lock_path, wheelhouse, packaging_path)
    socket_events: list[str] = []

    def audit_hook(event: str, _arguments: tuple[object, ...]) -> None:
        if event.startswith("socket."):
            socket_events.append(event)
            raise RuntimeError("network use is forbidden during locked installation")

    sys.addaudithook(audit_hook)
    old_argv = sys.argv[:]
    sys.path.insert(0, str(installer_path))
    try:
        sys.argv = ["python -m installer", "--validate-record", "all", "--no-compile-bytecode", *map(str, wheels)]
        runpy.run_module("installer", run_name="__main__")
    finally:
        sys.argv = old_argv
        sys.path.remove(str(installer_path))
    actual = {canonicalize_name(item.metadata["Name"]): item.version for item in importlib.metadata.distributions()}
    expected = {item["name"]: item["version"] for item in identities}
    if actual != expected or set(actual).intersection(FORBIDDEN):
        raise ValueError("installed graph differs from reviewed lock")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("x", encoding="utf-8", newline="\n") as output:
        json.dump(
            {
                "result": "PASS",
                "python": platform.python_version(),
                "platform": sys.platform,
                "machine": platform.machine(),
                "lock_sha256": sha256_file(lock_path),
                "bootstrap_sha256": sha256_file(bootstrap_path),
                "bootstrap_packages": bootstrap["packages"],
                "installed": identities,
                "graph": graph,
                "external_request_attempts": len(socket_events),
                "compile_bytecode": False,
                "pip_or_uv_installed": False,
            },
            output,
            indent=2,
            sort_keys=True,
        )
        output.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lock", required=True, type=pathlib.Path)
    parser.add_argument("--bootstrap", required=True, type=pathlib.Path)
    parser.add_argument("--wheelhouse", required=True, type=pathlib.Path)
    parser.add_argument("--report", required=True, type=pathlib.Path)
    arguments = parser.parse_args()
    install(arguments.lock, arguments.bootstrap, arguments.wheelhouse, arguments.report)


if __name__ == "__main__":
    main()
