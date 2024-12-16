#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

from architecture import is_wrong_architecture

TEST_MANIFEST = """
    bases:
        - architectures:
            - {arch}
          channel: '22.04'
          name: ubuntu
"""


def test_wrong_architecture_file_not_found(monkeypatch):
    """Tests if the function returns False when the charm file doesn't exist."""
    monkeypatch.setattr("os.environ", {"CHARM_DIR": "/tmp"})
    monkeypatch.setattr("pathlib.Path.exists", lambda *args, **kwargs: False)
    assert not is_wrong_architecture()


def test_wrong_architecture_amd64(monkeypatch):
    """Tests if the function correctly identifies arch when charm is AMD."""
    manifest = TEST_MANIFEST.format(arch="amd64")
    monkeypatch.setattr("os.environ", {"CHARM_DIR": "/tmp"})
    monkeypatch.setattr("pathlib.Path.exists", lambda *args, **kwargs: True)
    monkeypatch.setattr("pathlib.Path.read_text", lambda *args, **kwargs: manifest)

    monkeypatch.setattr("platform.machine", lambda *args, **kwargs: "x86_64")
    assert not is_wrong_architecture()

    monkeypatch.setattr("platform.machine", lambda *args, **kwargs: "aarch64")
    assert is_wrong_architecture()


def test_wrong_architecture_arm64(monkeypatch):
    """Tests if the function correctly identifies arch when charm is ARM."""
    manifest = TEST_MANIFEST.format(arch="arm64")
    monkeypatch.setattr("os.environ", {"CHARM_DIR": "/tmp"})
    monkeypatch.setattr("pathlib.Path.exists", lambda *args, **kwargs: True)
    monkeypatch.setattr("pathlib.Path.read_text", lambda *args, **kwargs: manifest)

    monkeypatch.setattr("platform.machine", lambda *args, **kwargs: "x86_64")
    assert is_wrong_architecture()

    monkeypatch.setattr("platform.machine", lambda *args, **kwargs: "aarch64")
    assert not is_wrong_architecture()
