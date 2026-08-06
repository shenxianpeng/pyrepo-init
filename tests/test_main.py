"""Tests for pyrepo_init.main."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from pyrepo_init.main import (
    copy_source_project,
    create_project,
    find_source_root,
    get_message,
    main,
    resolve_project,
)

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import CaptureFixture, MonkeyPatch


def test_get_message() -> None:
    assert "copying itself" in get_message()


def test_create_project_copies_current_project_with_project_replacements(
    tmp_path: Path,
) -> None:
    spec = resolve_project("Hello.World", base_dir=tmp_path, initialize_git=False)

    written = create_project(spec)

    project = tmp_path / "hello-world"
    assert written
    assert (project / "pyproject.toml").is_file()
    assert (project / ".github/workflows/test.yml").is_file()
    assert (project / ".github/workflows/publish-pypi.yml").is_file()
    assert (project / "src/hello_world/main.py").is_file()
    assert (project / "tests/test_main.py").is_file()
    assert (project / "docs/index.md").is_file()
    assert not (project / "src/pyrepo_init").exists()
    assert not (project / ".git").exists()

    pyproject = (project / "pyproject.toml").read_text(encoding="utf-8")
    assert 'name = "hello-world"' in pyproject
    assert 'hello-world = "hello_world.main:main"' in pyproject
    assert "https://github.com/shenxianpeng/hello-world" in pyproject

    package_main = (project / "src/hello_world/main.py").read_text(encoding="utf-8")
    assert "hello-world creates a Python project by copying itself." in package_main
    assert "pyrepo-init" not in package_main
    assert "pyrepo_init" not in package_main


def test_copy_source_project_skips_local_artifacts(
    tmp_path: Path,
) -> None:
    source = find_source_root()
    assert source is not None
    spec = resolve_project("demo", base_dir=tmp_path, initialize_git=False)

    copy_source_project(source, spec)

    project = tmp_path / "demo"
    assert not (project / ".claude").exists()
    assert not (project / ".venv").exists()
    assert not (project / ".nox").exists()
    assert not (project / ".pytest_cache").exists()
    assert not (project / "dist").exists()
    assert not (project / "site").exists()
    assert not any(project.rglob("__pycache__"))
    assert not any(project.rglob("*.egg-info"))


def test_create_project_refuses_to_overwrite(tmp_path: Path) -> None:
    spec = resolve_project("demo", base_dir=tmp_path, initialize_git=False)

    create_project(spec)

    with pytest.raises(FileExistsError):
        create_project(spec)


def test_create_project_initializes_git_by_default(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    initialized_paths: list[Path] = []

    def fake_initialize_git_repository(target_dir: Path) -> None:
        initialized_paths.append(target_dir)

    monkeypatch.setattr(
        "pyrepo_init.main.initialize_git_repository",
        fake_initialize_git_repository,
    )
    spec = resolve_project("demo", base_dir=tmp_path)

    create_project(spec)

    assert initialized_paths == [tmp_path / "demo"]


@pytest.mark.parametrize("name", ["../demo", "demo/example", "bad name"])
def test_resolve_project_rejects_invalid_names(tmp_path: Path, name: str) -> None:
    with pytest.raises(ValueError):
        resolve_project(name, base_dir=tmp_path)


def test_main_creates_project_without_git(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)

    assert main(["demo-project", "--no-git"]) == 0

    captured = capsys.readouterr()
    assert "Created demo-project" in captured.out
    assert (tmp_path / "demo-project/README.md").is_file()
    assert not (tmp_path / "demo-project/.git").exists()
