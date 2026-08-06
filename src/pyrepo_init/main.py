"""Create Python repositories by copying this project as the source template."""

from __future__ import annotations

import argparse
import io
import keyword
import re
import subprocess
import tempfile
import urllib.error
import urllib.request
import zipfile
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path


SOURCE_DISTRIBUTION_NAME = "pyrepo-init"
SOURCE_PACKAGE_NAME = "pyrepo_init"
SOURCE_REPOSITORY_URL = "https://github.com/shenxianpeng/pyrepo-init"
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
SEPARATOR_RE = re.compile(r"[-_.]+")
EXCLUDED_NAMES = {
    ".claude",
    ".git",
    ".mypy_cache",
    ".nox",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "site",
    "venv",
}
EXCLUDED_SUFFIXES = (".egg-info", ".pyc", ".pyo")


@dataclass(frozen=True)
class ProjectSpec:
    """Resolved values for the project being created."""

    distribution_name: str
    package_name: str
    target_dir: Path
    initialize_git: bool


def get_message() -> str:
    """Return a short description of the command."""
    return "pyrepo-init creates a Python project by copying itself."


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(
        prog=SOURCE_DISTRIBUTION_NAME,
        description=get_message(),
    )
    parser.add_argument(
        "project_name",
        help="Project distribution name, for example 'hello-world'.",
    )
    parser.add_argument(
        "--no-git",
        action="store_false",
        default=True,
        dest="initialize_git",
        help="Do not run git init in the generated project.",
    )
    return parser


def resolve_project(
    project_name: str,
    *,
    base_dir: Path,
    initialize_git: bool = True,
) -> ProjectSpec:
    """Validate the project name and derive package names."""
    if Path(project_name).name != project_name or project_name in {".", ".."}:
        msg = "project name must be a name, not a path"
        raise ValueError(msg)

    if NAME_RE.fullmatch(project_name) is None:
        msg = "project name may contain only letters, numbers, '.', '_' and '-'"
        raise ValueError(msg)

    distribution_name = SEPARATOR_RE.sub("-", project_name).lower()
    package_name = SEPARATOR_RE.sub("_", project_name).lower()

    if not package_name.isidentifier() or keyword.iskeyword(package_name):
        msg = f"project name {project_name!r} cannot produce a valid package name"
        raise ValueError(msg)

    return ProjectSpec(
        distribution_name=distribution_name,
        package_name=package_name,
        target_dir=base_dir / distribution_name,
        initialize_git=initialize_git,
    )


def create_project(spec: ProjectSpec) -> list[Path]:
    """Create a project by copying and rewriting this project."""
    if spec.target_dir.exists():
        msg = f"{spec.target_dir} already exists"
        raise FileExistsError(msg)

    source_root = find_source_root()
    if source_root is not None:
        return copy_source_project(source_root, spec)

    with tempfile.TemporaryDirectory(prefix=f"{SOURCE_DISTRIBUTION_NAME}-") as temp_dir:
        source_root = download_source_root(Path(temp_dir))
        return copy_source_project(source_root, spec)


def copy_source_project(source_root: Path, spec: ProjectSpec) -> list[Path]:
    """Copy source_root into the target directory with project names rewritten."""
    source_files = list(iter_source_files(source_root, spec.target_dir))
    spec.target_dir.mkdir(parents=True)
    written: list[Path] = []

    for source_path in source_files:
        relative_path = source_path.relative_to(source_root).as_posix()
        rendered_relative_path = render_project_names(relative_path, spec)
        destination = spec.target_dir / rendered_relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        write_rendered_file(source_path, destination, spec)
        written.append(destination)

    if spec.initialize_git:
        initialize_git_repository(spec.target_dir)

    return written


def find_source_root() -> Path | None:
    """Find a checkout root near this module when running from source/editable."""
    for candidate in Path(__file__).resolve().parents:
        if is_source_root(candidate):
            return candidate
    return None


def is_source_root(path: Path) -> bool:
    """Return whether path looks like the project root for this package."""
    return (
        (path / "pyproject.toml").is_file()
        and (path / "README.md").is_file()
        and (path / ".github" / "workflows").is_dir()
        and (path / "src" / SOURCE_PACKAGE_NAME).is_dir()
    )


def download_source_root(target_dir: Path) -> Path:
    """Download the source repository when no local checkout is available."""
    archive_url = f"{SOURCE_REPOSITORY_URL}/archive/refs/heads/main.zip"

    try:
        with urllib.request.urlopen(archive_url, timeout=30) as response:
            archive = response.read()
    except urllib.error.URLError as exc:
        msg = (
            "could not find a local source checkout and failed to download "
            f"{archive_url}: {exc}"
        )
        raise RuntimeError(msg) from exc

    with zipfile.ZipFile(io.BytesIO(archive)) as zip_file:
        zip_file.extractall(target_dir)

    for candidate in target_dir.iterdir():
        if candidate.is_dir() and is_source_root(candidate):
            return candidate

    msg = f"downloaded archive from {archive_url} does not contain a source project"
    raise RuntimeError(msg)


def iter_source_files(source_root: Path, target_dir: Path) -> Iterator[Path]:
    """Yield project files that should be copied into a generated project."""
    resolved_target = target_dir.resolve()
    git_files = list_git_source_files(source_root)

    candidates: Iterable[Path]
    if git_files is not None:
        candidates = (source_root / path for path in git_files)
    else:
        candidates = sorted(source_root.rglob("*"))

    for path in candidates:
        if not path.is_file():
            continue
        if is_excluded(path, source_root):
            continue
        try:
            path.resolve().relative_to(resolved_target)
        except ValueError:
            pass
        else:
            continue
        yield path


def list_git_source_files(source_root: Path) -> list[Path] | None:
    """Return non-ignored git files when source_root is a checkout."""
    if not (source_root / ".git").exists():
        return None

    try:
        result = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=source_root,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None

    if result.returncode != 0:
        return None

    return [Path(line) for line in result.stdout.splitlines() if line]


def is_excluded(path: Path, source_root: Path) -> bool:
    """Return whether a source path is a local artifact, not project source."""
    relative_parts = path.relative_to(source_root).parts
    if any(part in EXCLUDED_NAMES for part in relative_parts):
        return True
    return any(part.endswith(EXCLUDED_SUFFIXES) for part in relative_parts)


def write_rendered_file(
    source_path: Path, destination: Path, spec: ProjectSpec
) -> None:
    """Write a copied file, rewriting project names for text files."""
    data = source_path.read_bytes()
    try:
        content = data.decode("utf-8")
    except UnicodeDecodeError:
        destination.write_bytes(data)
        return

    destination.write_text(render_project_names(content, spec), encoding="utf-8")


def render_project_names(value: str, spec: ProjectSpec) -> str:
    """Replace this project's names with the generated project's names."""
    return (
        value.replace(SOURCE_PACKAGE_NAME, spec.package_name)
        .replace(SOURCE_DISTRIBUTION_NAME, spec.distribution_name)
        .replace("Pyrepo Init", title_from_distribution_name(spec.distribution_name))
    )


def title_from_distribution_name(distribution_name: str) -> str:
    """Convert a distribution name into a title."""
    return distribution_name.replace("-", " ").title()


def initialize_git_repository(target_dir: Path) -> None:
    """Initialize a git repository when git is available."""
    try:
        subprocess.run(
            ["git", "init", "-q"],
            cwd=target_dir,
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return


def format_next_steps(spec: ProjectSpec, written: list[Path]) -> str:
    """Build the success message printed after generation."""
    return "\n".join(
        [
            f"Created {spec.distribution_name} at {spec.target_dir} ({len(written)} files).",
            "",
            "Next steps:",
            f"  cd {spec.distribution_name}",
            "  python -m pip install --upgrade pip nox",
            "  nox -s test",
            "  nox -s lint",
        ],
    )


def main(argv: list[str] | None = None) -> int:
    """Run the command-line program."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        spec = resolve_project(
            args.project_name,
            base_dir=Path.cwd(),
            initialize_git=args.initialize_git,
        )
        written = create_project(spec)
    except ValueError as exc:
        parser.error(str(exc))
    except (FileExistsError, RuntimeError) as exc:
        parser.exit(1, f"error: {exc}\n")

    print(format_next_steps(spec, written))
    return 0
