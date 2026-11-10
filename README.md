# PyEQ36

[![Deploy](https://github.com/39alpha/pyeq36/actions/workflows/deploy.yaml/badge.svg)](https://github.com/39alpha/pyeq36/actions/workflows/deploy.yaml)

This package provides both compiled binaries of EQ3/6 and a thin Python wrapper
for running those utilities.

## AI Usage Statement

This project uses AI agents for general quality assurance and automation,
e.g. code review, documentation, development tooling and test improvements.
Agents are strictly prohibited from modifying the logic of non-test sources,
and changes to tests should be targeted and reviewed by a human before commit.

For more information, see [`AGENTS.md`](AGENTS.md).

## Installation

```sh
$ pip install --user pyeq36
```
or
```sh
$ uv tool install pyeq36
```

## Usage

You should have the primary EQ3/6 commands on your `PATH`, i.e.

```sh
$ eqpt
 usage: eqpt <data0>
```

### Python Shims
The commands that are on you `PATH` are actually python shims in order to make
the bundled wheels self-contained. However, this introduces a small runtime
penalty (`~30ms` for the command above compared to `~500us` when executing the
binary directly). For everyday usage, this shouldn't really affect you. However,
if you cannot stand paying that penalty, you can explicitly add the path to the
binaries to your `PATH`. For example:

```bash
$ export PATH="$(python -c 'import eq36.paths; print(eq36.paths.get_bin())'):$PATH"
```

### Using Your Own Binaries
You may want to use EQ3/6 binaries other than those bundled with `pyeq36`, for
example to run a legacy version of EQ3/6 or your own fork. If you have built and
installed the binaries yourself, you can tell `pyeq36` to use them by setting
the `EQ36_BIN` environment variable to the directory containing them. For
example:

```bash
$ export EQ36_BIN="/usr/local/bin"
```

The directory must contain the `eqpt`, `eq3nr` and `eq6` binaries (with an
`.exe` suffix on Windows). Both the commands on your `PATH` and the Python
functions will then run your binaries. A leading `~` is expanded, relative
paths are resolved against the current working directory, and an empty value
is ignored.

Don't install your binaries into the same directory as the `pyeq36` commands,
e.g. `~/.local/bin` when using `pip install --user`. The two have the same
names, so one will overwrite the other.

## Licensing

This repo includes the source files for
[EQ3/6 v8.0a](https://www-gs.llnl.gov/energy-homeland-security/geochemistry),
a software package for geochemical modeling developed by Thomas Wolery at
Lawrence Livermore National Laboratory under the
[BSD 3-Clause License](https://github.com/39alpha/eq36/blob/main/LICENSE).

## References

- Wolery, T. J., and USDOE. EQ3/6 A Software Package for Geochemical Modeling.
  Computer software. December 13, 2010.
  https://www.osti.gov//servlets/purl/1231666.
  doi:https://doi.org/10.11578/dc.20210416.44.
- Wolery, T. J. and R. L. Jarek. Software User's Manual EQ36, Version 8.0. U.S.
  Tech. Rep. 2003. Department of Energy, Office of Civilian Radioactive Waste
  Management, Office of Repository Development. 10813-UM-8.0-00.
