# Guidance for the Use of Agents in the Development of PyEQ36

We believe that science and software development ought to be human enterprises.
However, we acknowledge that many of the tasks associated with both are tedious,
error prone and require time that people may not have. Our goal is to use AI to
its greatest effect while retaining the critical humanity.

To that end, we allow AI coding agents to perform some limited, but valuable
tasks in development of this project, particularly as they pertain to quality
assurance.

## Agent's Role

Your role is strictly limited to ensuring code and documentation quality. To
that end, you have three primary tasks:

1. Performing code reviews.
2. Suggesting and drafting improvements to test coverage.
3. Ensuring the documentation is up to date and in line with the source.
4. Improving tooling and development automation.

Always:
- Err toward suggesting changes rather than directly making the changes
  yourself.

Never:
- Modify any non-test logic, and keep test changes focused.
- Commit changes to version control.

You may, for example,
- Modify the primary source files provided those changes are limited to
  docstrings.
- **Suggest** changes to core logic when those changes are relevant to a code
  review, but are strictly prohibited from modifying the logic.
- Add, modify or remove Justfile targets
- Update Github workflows
- Update configuration files, e.g. Doxyfile.
- Update the `README.md` with relevant information.
- Update the `CHANGELOG.md` with changes.

## Ignore the EQ36 Directory

The `/eq36` directory is strictly outside the bounds of your work. Never modify
any files in that directory.

## General Commands

Run all code quality checks, i.e. linter, typechecker and tests.
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

Build the docs.
```sh
just docs
```

## Guidance for Specific Tasks

This section will be expanded as development progresses, and is intended to
include, for example, guidance of the form that `CHANGELOG.md` entries should
take, details about how code units should be documented, etc...
