# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **`eqpt`, `eq3nr` and `eq6`** functions to run the binaries from Python,
  returning their `stdout` and `stderr`.
- **`Eq36Error`** exception, raised when a binary reports an error, exits with
  a non-zero code or times out.
- **`RunCode`** enum of the error codes carried by `Eq36Error`.
- **`EQ36_BIN`** environment variable to use EQ3/6 binaries installed outside of
  the package.
- **`typing_extensions`** runtime dependency.
- **Doxygen documentation**, built with `just docs` and served with
  `just docs-serve`.
- **Code coverage** reports with `just coverage` and `just coverage-serve`.
- **Test suite** covering the full `eq36` package.
- **AI agents policy** in `AGENTS.md`, summarized in `README.md`.

### Changed

- **`eq36.paths`** functions raise `RuntimeError` rather than `Exception`.
- **CI workflows** consolidated into one, which also tests the built wheels.
- **`just spellcheck`** also checks the Markdown documents with `aspell`.
- **Ruff and Pyrefly** target Python 3.10, the minimum supported version.

## [v0.1.0]

### Added

- **EQ3/6** build and binaries.
- **`eq36`** package with the `eq36.paths` submodule to provide absolute paths
  to installed binaries.
