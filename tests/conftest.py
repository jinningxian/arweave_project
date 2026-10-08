"""Shared test constants; tests never use a real wallet or network."""

from __future__ import annotations

import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]


def deny_network(*_args, **_kwargs):
    raise AssertionError("external network is forbidden in this test suite")
