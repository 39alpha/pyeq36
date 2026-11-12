# Guidance for AI Use

We believe that science and software development ought to be human enterprises.
However, we acknowledge that many of the tasks associated with both are tedious,
error prone and require time that people may not have. Our goal is to use AI to
its greatest effect while retaining the critical humanity.

To that end, we allow AI coding agents to perform some limited, but valuable
tasks in development of this project, particularly as they pertain to quality
assurance.

## Agent's Role

Your role is strictly limited to ensuring code and documentation quality. To
that end, you have four primary tasks:

1. Performing code reviews.
2. Suggesting and drafting improvements to test coverage.
3. Ensuring the documentation is up to date and in line with the source.
4. Improving tooling and development automation.

### Acting on Requests

The maintainers decide what changes are made. Your default is to suggest, not
to act.

- Err toward suggesting changes rather than directly making the changes
  yourself.
- Only make the changes you have been explicitly asked to make. A statement of
  preference or intent (e.g. "the cleanest solution is...") is not a request
  to act on it.
- Ask questions when a decision belongs to the maintainers, e.g. when the code
  and its documentation disagree and it is not clear which is correct.
- Use the `just` targets listed under [General Commands](#general-commands)
  rather than invoking the underlying tools directly.

### What You May Change

When asked, you may, for example:

- Modify the primary source files, provided those changes are limited to
  docstrings.
- Modify tests, keeping those changes focused.
- Add, modify or remove `Justfile` targets.
- Update GitHub workflows.
- Update configuration files, e.g. `Doxyfile`.
- Update the `README.md` with relevant information.
- Update the `CHANGELOG.md` with changes.

### What You Must Never Do

- Modify any non-test logic. You may **suggest** changes to core logic when
  those changes are relevant to a code review, but you are strictly prohibited
  from making them.
- Commit changes to version control.
- Modify any files in the `/eq36` directory. It is strictly outside the bounds
  of your work.

## General Commands

Run all code quality checks, i.e. `pre-commit` hooks (linter, typechecker and
workflow audit), spellcheck and tests.
```sh
just check
```

Run the linter.
```sh
just lint
```

Fix any fixable linter errors or warnings.
```sh
just lint-fix
```

Run the code formatter.
```sh
just format
```

Run the typechecker.
```sh
just typecheck
```

Run the test suite.
```sh
just test
```

Run the test suite and report code coverage.
```sh
just coverage
```

Run only the Hypothesis (property-based) tests, optionally with a settings
profile (`dev`, `default` or `thorough`; see `tests/conftest.py`).
```sh
just hypothesis [profile]
```

Run the Hypothesis tests and report statistics, e.g. how many examples were
generated or discarded.
```sh
just hypothesis-stats [profile]
```

Delete the Hypothesis example database, so that previously failing examples
are no longer replayed.
```sh
just hypothesis-clean
```

Spellcheck the source and documentation without prompting. The interactive
`just spellcheck` target is intended for humans.
```sh
just spellcheck-batch
```

Audit the GitHub workflows and Dependabot configuration.
```sh
just audit-workflows
```

Build the docs.
```sh
just docs
```

## Guidance for Specific Tasks

This section will be expanded as development progresses, and is intended to
include, for example, guidance of the form that `CHANGELOG.md` entries should
take, details about how code units should be documented, etc...

### Docstrings

- Use Doxygen directives, e.g. `@param`, `@return`, `@throws`.
- Order the contents of a docstring as follows:
  1. A one-line summary, which Doxygen uses as the brief (do not use `@brief`)
  2. A detailed description, if needed
  3. `@private`, for private (underscore-prefixed) functions and methods
  4. `@param`, one per parameter, with the descriptions aligned
  5. `@return`, omitted for functions that return `None`
  6. `@throws`, one per exception (or distinct cause of an exception)
  7. `@note` and `@warning`
- Private helpers are documented as fully as public functions.
- Document the code as it is. If the code appears to be wrong, document its
  current behavior and flag the discrepancy rather than documenting the
  intended behavior.
- Document the parameters of parametrized tests and fixtures with `@param`.

### Changelog

- Entries take the form `- **key point** rest of description.`
- Keep entries to 3 lines or fewer; shorter entries are preferred.
- Only include changes relative to the `main` branch. Changes internal to the
  `dev` or a feature branch (e.g. something added and then changed, or added
  and then removed) should not appear.

### Spelling

- Do not add words to the personal dictionary (`.aspell`). The spellcheck
  deliberately stops on new words so that a human can add them.

### Dependencies

- Do not put versions on development dependencies; the latest is almost always
  better. Remove any bounds that tools (e.g. `uv add`) insert automatically.
- `uv.lock` is not tracked, so CI uses the latest development dependencies by
  default.

### GitHub Workflows

- Pin actions to full commit hashes with a version comment, e.g.
  `actions/checkout@<sha> # v7.0.1`. Dependabot keeps these up to date.
- Prefer maintained actions that track the latest release of a tool over
  managing tool versions by hand.
- Workflows must pass `just audit-workflows`.
