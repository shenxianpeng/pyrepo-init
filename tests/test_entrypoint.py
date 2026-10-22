"""Tests for running pyrepo-init as a module (``python -m pyrepo_init``)."""

from __future__ import annotations

import runpy
import subprocess
import sys

import pytest

from pyrepo_init.main import get_message, main


def test_run_as_main_prints_message(capsys: pytest.CaptureFixture[str]) -> None:
    runpy.run_module("pyrepo_init", run_name="__main__")

    assert capsys.readouterr().out == f"{get_message()}\n"


def test_importing_main_module_does_not_run(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Same as `import pyrepo_init.__main__`: __name__ is the dotted module
    # name, so the `if __name__ == "__main__"` guard must not fire.
    namespace = runpy.run_module("pyrepo_init")

    assert namespace["__name__"] == "pyrepo_init.__main__"
    assert namespace["main"] is main
    assert capsys.readouterr().out == ""


def test_python_m_pyrepo_init_in_a_subprocess() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "pyrepo_init"],
        capture_output=True,
        text=True,
        check=True,
    )

    assert proc.stdout == f"{get_message()}\n"
    assert proc.stderr == ""
