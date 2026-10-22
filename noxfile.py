from glob import glob
from shutil import rmtree

import nox


@nox.session
def lint(session: nox.Session) -> None:
    """Run linters."""
    session.install("pre-commit")
    session.run("pre-commit", "run", "--all-files", external=True)


@nox.session
def test(session: nox.Session) -> None:
    """Run tests."""
    session.install("--upgrade", "pip")
    session.install("-e", ".[test]")
    session.run("pytest", "--cov", "--cov-report=term-missing", *session.posargs)


@nox.session
def build(session: nox.Session) -> None:
    """Build and validate distribution artifacts."""
    session.install("--upgrade", "pip")
    session.install("build", "twine")
    rmtree("dist", ignore_errors=True)
    session.run("python", "-m", "build")
    session.run("twine", "check", *sorted(glob("dist/*")))


@nox.session
def docs(session: nox.Session) -> None:
    """Build docs."""
    session.install("--upgrade", "pip")
    session.install("-e", ".[docs]")
    session.run("mkdocs", "build")


@nox.session(name="docs-live")
def docs_live(session: nox.Session) -> None:
    """Live docs preview."""
    session.install("-e", ".[docs]")
    session.run("mkdocs", "serve", external=True)
