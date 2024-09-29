# Pythion

Pythion is a command-line interface (CLI) tool designed to assist Python developers by generating documentation strings using AI. With an easy-to-use interface built on the [Click](https://click.palletsprojects.com/) library, Pythion provides a seamless way to enhance your Python projects with well-structured docstrings and documentation management.

## Features

- Generate documentation strings for Python functions and classes.
- Create and manage documentation in batches
- Flexible options to include or exclude already documented functions.
- Automatically generate intelligent commit messages based on staged changes.
- Easily bump version numbers in your projects.

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [Commands](#commands)

## Installation

You can install Pythion via pip. Open your terminal and enter:

```
pip install pythion
```

## Usage

After installing Pythion, you can invoke the command-line tool as follows:

```
pythion [OPTIONS] COMMAND [ARGS]…
```

# Commands

## 1. `docs`

Generates and manages docstrings for Python projects.

```
pythion docs <root_dir> [--custom-instruction <instruction>] [--profile <profile>]
```

- **Arguments:**
  - `root_dir`: The path to the root directory containing the Python files to analyze.
- **Options:**
  - `--custom-instruction`: Custom instructions for generating docstrings.
  - `--profile`: Choose a predefined instruction set such as `fastapi` or `cli`.

**Example:**

```
pythion docs /path/to/project --custom-instruction "Use concise language."
```

## 2. `module_docs`

Generates documentation for Python modules.

```
pythion module_docs <root_dir> [--custom-instruction <instruction>]
```

- **Arguments:**
  - `root_dir`: The root directory of the Python project.
- **Options:**
  - `--custom-instruction`: Custom instructions for module documentation generation.

**Example:**

```
pythion module_docs /path/to/project --custom-instruction "Include examples in docstrings."
```

### 3. `build-cache`

Creates a documentation cache for functions and methods in a specified directory.

```
pythion build-cache <root_dir> [--use_all] [--dry]
```

- **Arguments:**
  - `root_dir`: The directory path containing Python files.
- **Options:**
  - `--use_all`: Generates docstrings for all functions, or only those without docstrings.
  - `--dry`: Performs a dry run without generating any documentation.

**Example:**

```
pythion build-cache /path/to/dir --use_all --dry
```

### 4. `iter-docs`

Iterates through the docstring cache and apply them to objects

```
pythion iter-docs <root_dir></root_dir>
```

- **Arguments:**
  - `root_dir`: The path to the directory containing documents to be iterated.

**Example:**

```
pythion iter-docs /path/to/dir
```

### 5. `make-commit`

Generates a commit message based on staged changes.

```
pythion make-commit [--custom-instruction <instruction>] [--profile <profile>]
```

- **Options:**
  - `--custom-instruction`: Custom instructions for generating the commit message.
  - `--profile`: (Optional) Select a predefined instruction set.

**Example:**

```
pythion make-commit --custom-instruction "Don't mention version updates"
```

## 6. `bump-version`

Bumps version numbers in a specified version file.

```
pythion bump-version --version-regex <pattern> --file-path <file>
```

- **Arguments:**
  - `--version-regex`: Regex pattern to match the version string.
  - `--file-path`: Full path to the file containing the version string.

**Example:**

```
pythion bump-version --version-regex 'version="(.\*?)"' --file-path '/path/to/version_file.txt'
```

## NOTES

- You must have an OpenAI API key saved on your environment for the key `OPENAI_API_KEY`.
