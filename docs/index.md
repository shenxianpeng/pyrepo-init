# pyrepo-init

`pyrepo-init` creates a new Python project by copying this project itself. It
rewrites the distribution name, package name, docs, tests, and GitHub metadata
so the generated project is named after the command argument.

There is no separate template directory. The source project is the template.

## Install

```bash
pip install pyrepo-init
```

## Use

```bash
pyrepo-init hello-world
cd hello-world
nox -s test
nox -s lint
```

Use `--no-git` to skip the default `git init`.

## Generated Package Layout

```text
src/<package>/       Python package
tests/               pytest test suite
docs/                MkDocs documentation
.github/workflows/   GitHub Actions workflows
```
