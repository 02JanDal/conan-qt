# conan-qt

[Conan](https://conan.io/) packages for [Qt](https://qt.io/). Each module is in a separate Qt package.

[![Build Status](https://travis-ci.org/02JanDal/conan-qt.svg?branch=master)](https://travis-ci.org/02JanDal/conan-qt)
[![Build status](https://ci.appveyor.com/api/projects/status/54hgdx5pvsd4kv0t/branch/master?svg=true)](https://ci.appveyor.com/project/02JanDal/conan-qt/branch/master)

# Usage

Please see the conan documentation for how to use these packages.

Currently only CMake using the FindQt* scripts provided by Qt is supported, support for QMake and other build systems supported by conan will be added later.

To make sure you're using the FindQt* scripts from these packages, add

```cmake
list(INSERT 1 CMAKE_PREFIX_PATH "${CONAN_QT5CORE_ROOT}/lib/cmake/")
```

after including `conanbuildinfo.cmake`.

# How it works

All modules are specified in `data.yaml`, together with meta data required to construct the packages correctly.

The `generate.py` script uses this data to generate conanfiles, as well as a few support files and simple tests. It also calls `conan test_package` which builds and tests the package.

`compare.sh` compares the resulting package contents against the original, this can be used to see what files are currently not included in any package, as well as which files did get changed during the packaging process.

The `Makefile` provides a few convenience targets:

* `make initial` generates and packages all modules contained in `data.yaml`
* `make withouteverything` does the same, but does not build Qt5Everything. This is useful during development, since it means not rebuilding Qt.
* `make generate` generates the files for all packages, but doesn't build or test anything
* `make compare` just calls `compare.sh`