# PyEQ36

[![Deploy](https://github.com/39alpha/pyeq36/actions/workflows/deploy.yaml/badge.svg)](https://github.com/39alpha/pyeq36/actions/workflows/deploy.yaml)

This package provides both compiled binaries of EQ3/6 and a thin Python wrapper
for running those utilities.

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
penalty (~30ms for the command above compared to ~500us when executing the binary
directly). For everyday usage, this shouldn't really affect you. However, if you
cannot stand paying that penalty, you can explictly add the path to the binaries
to your `PATH`. For example:

```bash
$ export PATH="$(python -c 'import eq36.paths; print(eq36.paths.get_bin())'):$PATH"
```

## Licensing

This repo includes the source files for
[EQ3/6 v8.0a](https://www-gs.llnl.gov/energy-homeland-security/geochemistry),
a software package for geochemical modeling developed by Thomas Wolery at
Lawrence Livermore National Laboratory under the
[BSD 3-Clause License](https://github.com/39alpha/pyeq36/blob/main/eq36/LICENSE).

## References

- Wolery, T. J., and USDOE. EQ3/6 A Software Package for Geochemical Modeling.
  Computer software. December 13, 2010.
  https://www.osti.gov//servlets/purl/1231666.
  doi:https://doi.org/10.11578/dc.20210416.44.
- Wolery, T. J. and R. L. Jarek. Software User's Manual EQ36, Version 8.0. U.S.
  Tech. Rep. 2003. Department of Energy, Office of Civilian Radioactive Waste
  Management, Office of Repository Development. 10813-UM-8.0-00.
