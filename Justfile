default:
    @just --list

[group('quality assurance')]
[doc('Run pre-commit hooks and the full test suite')]
check: pre-commit test

[group('quality assurance')]
[doc('Run all pre-commit hooks')]
pre-commit:
    uv run pre-commit run --all-files

[group('test')]
[doc('Run all tests; extra arguments are passed to pytest')]
test *args:
    uv run pytest {{args}}

[group('test')]
[doc('Run all tests and report code coverage; extra arguments are passed to pytest')]
coverage *args:
    uv run pytest --cov --cov-report=term --cov-report=html {{args}}

[group('test')]
[doc('Serve HTML coverage report')]
coverage-serve port="5556":
    uv run --directory=htmlcov -- python -m http.server {{port}}

[group('quality assurance')]
[doc('Lint with ruff; extra arguments are passed to ruff')]
lint *args:
    uv run ruff check --exit-non-zero-on-fix {{args}}

[group('quality assurance')]
[doc('Lint with ruff, applying fixes; extra arguments are passed to ruff')]
lint-fix *args:
    uv run ruff check --fix --exit-non-zero-on-fix {{args}}

[group('quality assurance')]
[doc('Format with ruff; extra arguments are passed to ruff')]
format *args:
    uv run ruff format {{args}}

[group('quality assurance')]
[doc('Typecheck with pyrefly; extra arguments are passed to pyrefly')]
typecheck *args:
    uv run pyrefly check {{args}}

[group('quality assurance')]
[doc('Spellcheck all source code and documentation')]
spellcheck *args:
    #!/usr/bin/env bash
    set -eou pipefail
    uv run -- codespell -i 3 src tests

    PERSONAL="{{justfile_directory()}}/.aspell"
    aspell check --personal="${PERSONAL}" README.md
    aspell check --personal="${PERSONAL}" CHANGELOG.md
    aspell check --personal="${PERSONAL}" AGENTS.md

[group('dev')]
[doc('Start an IPython session')]
repl:
    uv run ipython

[group('dev')]
[doc('Watch files and run a just command if they change')]
watch cmd="test" ext="py" *args:
    watchexec -r -c -e {{ext}} -- just {{cmd}} {{args}}

[group('docs')]
[doc("Generate docs")]
docs:
    #!/usr/bin/env bash
    set -euo pipefail
    PROJECT_NUMBER=$(git describe --tags) doxygen Doxyfile

[group('docs')]
[doc("Serve the documents")]
docs-serve port="5555":
    uv run --directory=docs/_site -- python -m http.server {{port}}
