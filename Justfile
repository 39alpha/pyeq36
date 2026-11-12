default:
    @just --list

[group('quality assurance')]
[doc('Run pre-commit hooks, spell checking and the full test suite with coverage reporting')]
check: pre-commit spellcheck-batch coverage

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
[doc('Run the Hypothesis tests with a settings profile (dev, default or thorough); extra arguments are passed to pytest')]
[positional-arguments]
hypothesis profile="default" *args:
    shift; uv run pytest -m hypothesis --hypothesis-profile="{{profile}}" "$@"

[group('test')]
[doc('Run the Hypothesis tests with a settings profile and report statistics; extra arguments are passed to pytest')]
[positional-arguments]
hypothesis-stats profile="default" *args:
    shift; uv run pytest -m hypothesis --hypothesis-profile="{{profile}}" --hypothesis-show-statistics "$@"

[group('test')]
[doc('Delete the Hypothesis example database, so that previously failing examples are no longer replayed')]
hypothesis-clean:
    rm -rf .hypothesis

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
[doc('Audit GitHub workflows and Dependabot configuration with zizmor; extra arguments are passed to zizmor')]
audit-workflows *args:
    uv run zizmor {{args}} .github

[group('quality assurance')]
[doc('Spellcheck all source code and documentation')]
spellcheck:
    #!/usr/bin/env bash
    set -euo pipefail
    uv run -- codespell -w -i 3 src tests Justfile pyproject.toml .github

    PERSONAL="{{justfile_directory()}}/.aspell"
    while IFS= read -r -d '' file; do
        aspell check --dont-backup --mode=markdown --personal="${PERSONAL}" "${file}" < /dev/tty
    done < <("{{just_executable()}}" markdown-files)

[group('quality assurance')]
[doc('Spellcheck all source code and documentation without prompting, failing if any errors are found')]
spellcheck-batch:
    #!/usr/bin/env bash
    set -euo pipefail
    status=0
    uv run -- codespell src tests Justfile pyproject.toml .github || status=1

    PERSONAL="{{justfile_directory()}}/.aspell"
    while IFS= read -r -d '' file; do
        words=$(aspell list --mode=markdown --personal="${PERSONAL}" < "${file}" | sort -u)
        if [[ -n "${words}" ]]; then
            echo "${file}: unknown words"
            echo "${words}" | sed 's/^/    /'
            status=1
        fi
    done < <("{{just_executable()}}" markdown-files)
    exit "${status}"

# List the Markdown files to spellcheck, separated by NUL characters
[private]
markdown-files:
    #!/usr/bin/env bash
    set -euo pipefail
    find . -maxdepth 1 -name '*.md' -print0
    if [[ -d docs ]]; then
        find docs -name '*.md' -not -path 'docs/_site/*' -print0
    fi

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
[doc("Serve the documentation")]
docs-serve port="5555":
    uv run --directory=docs/_site -- python -m http.server {{port}}
