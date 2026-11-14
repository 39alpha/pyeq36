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
- **`eq36.data1`** module with the `Data1` class, a structured representation
  of a data1 file, and its species and solid solution types.
- **`eq36.libpyeq36`** module, a thin `ctypes` wrapper around the new
  `libpyeq36` Fortran library, which reads data1 files.
- **`eq36.curves`** module with the `TPCurve` class, a pressure-temperature
  curve made of polynomial pieces.
- **`eq36.typing`** module of type aliases.
- **`get_lib` and `get_libpath`** in `eq36.paths` to locate bundled libraries.
- **Type information**, with a `py.typed` marker.
- **`numpy` and `typing_extensions`** runtime dependencies.
- **Doxygen documentation**, built with `just docs`, served with
  `just docs-serve` and deployed to GitHub Pages on release.
- **Code coverage** reports with `just coverage` and `just coverage-serve`.
- **Test suite** covering the full `eq36` package, including Hypothesis tests
  run with `just hypothesis`.
- **Workflow auditing** with `just audit-workflows`, and a Dependabot
  configuration.
- **Project metadata**, including license, classifiers and project URLs.
- **AI agents policy** in `AGENTS.md`, summarized in `README.md`.

### Changed

- **`eq36.paths`** functions raise `RuntimeError` rather than `Exception`.
- **`get_execpath`** checks for the `.exe` extension case-insensitively.
- **Wheels** are tagged `py3-none-<platform>`, so one wheel per platform
  serves every Python version.
- **CI** runs tests on feature branches; releases are tested, installed and
  wheel-tested before deploying. Actions are pinned to commit hashes.
- **`just check`** also runs the spellcheck and reports coverage.
- **`just spellcheck`** also checks the Markdown documents with `aspell`.
- **Ruff and Pyrefly** target Python 3.10, the minimum supported version.

### Removed

- **Windows on ARM** support, until a native ARM64 Fortran compiler is
  available. The `win_arm64` wheels contained x86-64 binaries.

## [v0.1.0]

### Added

- **EQ3/6** build and binaries.
- **`eq36`** package with the `eq36.paths` submodule to provide absolute paths
  to installed binaries.
