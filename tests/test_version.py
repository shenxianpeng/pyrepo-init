"""Tests for the package version exposed by pyrepo_init."""

from __future__ import annotations

import importlib
import importlib.metadata
from collections.abc import Iterator
from importlib.metadata import PackageNotFoundError

import pytest

import pyrepo_init


@pytest.fixture
def restore_package() -> Iterator[None]:
    """Re-import pyrepo_init after the test so patched metadata cannot leak."""
    yield
    importlib.reload(pyrepo_init)


def test_version_matches_installed_metadata() -> None:
    assert isinstance(pyrepo_init.__version__, str)
    assert pyrepo_init.__version__ == importlib.metadata.version("pyrepo-init")


def test_all_exports_only_version() -> None:
    assert pyrepo_init.__all__ == ["__version__"]


@pytest.mark.usefixtures("restore_package")
def test_version_is_looked_up_by_distribution_name() -> None:
    seen: list[str] = []

    def fake_version(name: str) -> str:
        seen.append(name)
        return "1.2.3"

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(importlib.metadata, "version", fake_version)
        reloaded = importlib.reload(pyrepo_init)

    assert reloaded is pyrepo_init
    assert seen == ["pyrepo-init"]
    assert reloaded.__version__ == "1.2.3"


@pytest.mark.usefixtures("restore_package")
def test_version_falls_back_when_package_is_not_installed() -> None:
    def missing(name: str) -> str:
        raise PackageNotFoundError(name)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(importlib.metadata, "version", missing)
        reloaded = importlib.reload(pyrepo_init)

    assert reloaded.__version__ == "0.0.0"


@pytest.mark.usefixtures("restore_package")
def test_other_metadata_errors_are_not_swallowed() -> None:
    def broken(name: str) -> str:
        raise RuntimeError("metadata backend exploded")

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(importlib.metadata, "version", broken)
        with pytest.raises(RuntimeError, match="metadata backend exploded"):
            importlib.reload(pyrepo_init)
