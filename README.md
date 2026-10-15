# pyrepo-init

`pyrepo-init` creates a new Python project by copying this project itself.

Running `pyrepo-init hello-world` creates `hello-world/` with the same package
layout, tests, docs, linting, Nox sessions, and GitHub workflows as this
project. Project names and import paths are rewritten, so `pyrepo-init` becomes
`hello-world` and `pyrepo_init` becomes `hello_world`.

There is no separate template directory to maintain. When run from a source
checkout or editable install, the command copies the current project tree. If a
local checkout is not available, it falls back to downloading this repository's
source archive.

## Installation

```bash
pip install pyrepo-init
```

## Usage

```bash
pyrepo-init hello-world
cd hello-world
python -m pip install --upgrade pip nox
nox -s test
nox -s lint
```

The command runs `git init` in the generated project by default. Use `--no-git`
to only write the files:

```bash
pyrepo-init hello-world --no-git
```

## Generated Layout

```text
hello-world/
├── .github/
│   ├── dependabot.yml
│   └── workflows/
├── docs/
├── src/hello_world/
├── tests/
├── .pre-commit-config.yaml
├── LICENSE
├── README.md
├── mkdocs.yml
├── noxfile.py
└── pyproject.toml
```

Local artifacts such as `.git`, virtual environments, caches, `dist/`, and
generated docs are not copied.

## Development

```bash
python -m pip install --upgrade pip nox
nox -s test
nox -s lint
nox -s docs
```

## License

MIT
