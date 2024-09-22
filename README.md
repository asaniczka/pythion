# Pythion

Pythion is a command-line interface (CLI) tool designed to assist Python developers by generating documentation strings using AI. With an easy-to-use interface built on the [Click](https://click.palletsprojects.com/) library, Pythion provides a seamless way to enhance your Python projects with well-structured docstrings and documentation management.

## Features

- Generate documentation strings for Python functions and classes.
- Iterate through documents in specified directories.
- Flexible options to include or exclude already documented functions.

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [Commands](#commands)
- [License](#license)

## Installation

You can install Pythion via pip. Open your terminal and enter:

```bash
pip install pythion
```

## Usage

After installing Pythion, you can invoke the command-line tool as follows:

```bash
pythion [OPTIONS] COMMAND [ARGS]...
```

## Commands

### 1. `build-doc-cache`

Builds a documentation cache for functions and methods in a specified directory.

```bash
pythion build-doc-cache <root_dir> [--use_all]
```

- **Arguments:**
  - `root_dir`: The directory path where the Python files are located.
- **Options:**
  - `-ua`, `--use_all`: If set, generates docstrings for all functions; otherwise, only for those without docstrings.

**Example:**

```bash
pythion build-doc-cache /path/to/dir --use_all
```

### 2. `iter-docs`

Iterates through documents in the specified directory.

```bash
pythion iter-docs <root_dir>
```

- **Arguments:**
  - `root_dir`: The path to the directory containing documents to be iterated.

**Example:**

```bash
pythion iter-docs /path/to/dir
```

### 3. `make_docstr`

Generates documentation strings for Python files in the specified root directory.

```bash
pythion make-docstr <root_dir>
```

- **Arguments:**
  - `root_dir`: The path to the root directory containing the Python files to analyze.

**Example:**

```bash
pythion make-docstr /path/to/dir
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
