"""
This module contains commands for managing Python projects with focus on documentation.

Features:
- Generate docstrings for Python projects.
- Manage module documentation.
- Create documentation caches.
- Iterate through project documents.
- Handle smart commit messages.
- Bump version numbers.
"""

# pylint: disable=wrong-import-position
import sys

import click
from wrapworks import cwdtoenv  # type: ignore

cwdtoenv()

from pythion.src.commit_writer import handle_commit
from pythion.src.doc_writer import DocManager
from pythion.src.increase_version import execute_bump_version


@click.group()
def pythion():
    """
    A command line interface (CLI) tool for Python developers.

    This CLI groups various commands and functionalities tailored for Python development.

    Example usage:

      pythion command_name [OPTIONS]

    Commands:
      command_name     Description of what this command does.

    Options:
      -h, --help       Show this help message and exit.
    """
    ...


@click.command()
@click.argument("root_dir")
@click.option(
    "-ci", "--custom-instruction", help="Any custom instructions to provide to the AI"
)
@click.option(
    "-p",
    "--profile",
    type=click.Choice(["fastapi", "cli"]),
    help="Select a predefined custom instruction set",
)
def docs(
    root_dir: str, custom_instruction: str | None = None, profile: str | None = None
):
    """
    Generate and manage docstrings for Python projects.

    This command initializes the DocManager and facilitates the creation of docstrings by accepting a root directory,
    custom instructions, and a predefined profile selection.

    Args:
        root_dir (str): The root directory of the Python project for which to generate docstrings.
        custom_instruction (str | None, optional): Any custom instructions to provide to the AI for generating docstrings.
        profile (str | None, optional): Select a predefined custom instruction set. Choices are 'fastapi' or 'cli'.

    Examples:
        To generate docstrings in the specified root directory:
            pythion docs /path/to/project

        To generate docstrings with a custom instruction:
            pythion docs /path/to/project --custom-instruction "Use concise language."

        To use a predefined profile:
            pythion docs /path/to/project --profile fastapi
    """
    manager = DocManager(root_dir=root_dir)
    manager.make_docstrings(custom_instruction, profile)


@click.command()
@click.argument("root_dir")
@click.option(
    "-ci", "--custom-instruction", help="Any custom instructions to provide to the AI"
)
def module_docs(root_dir: str, custom_instruction: str | None = None):
    """
    Generates Python module documentation as per provided parameters.

    Args:
        root_dir (str): The root directory of the Python project.
        custom_instruction (str | None): Optional custom instructions for the AI to tailor the documentation generation.

    Usage:
        To generate documentation for a specific project's modules, you can run the following command:
            pythion module_docs /path/to/project --custom-instruction "Include examples in docstrings"

    This will initiate the docstring generation process for modules in the specified directory, adhering to any custom instructions you have provided.
    """
    manager = DocManager(root_dir=root_dir)
    manager.make_module_docstrings(custom_instruction)


@click.command()
@click.argument("root_dir")
@click.option(
    "-ua",
    "--use_all",
    is_flag=True,
    default=False,
    help="Whether to generate doc strings for all functions, or just the ones without docstrings",
)
@click.option(
    "--dry",
    is_flag=True,
    default=False,
    help="Do a dry run without actually generating documentation",
)
def build_cache(root_dir: str, use_all: bool, dry: bool):
    """
    Generates documentation cache based on function docstrings in the specified root directory.

    Args:
        root_dir (str): The root directory containing the Python files whose functions need documentation.
        use_all (bool): Optional; if set, generates docstrings for all functions. Defaults to False, which means only functions without docstrings will be processed.
        dry (bool): Optional; if set, performs a dry run without making any changes. Defaults to False.

    Example:
        pythion build-cache src --use_all --dry
    """
    manager = DocManager(root_dir=root_dir)
    manager.build_doc_cache(use_all, dry)


@click.command()
@click.argument("root_dir")
def iter_docs(root_dir: str):
    """
    Command-line interface to iterate through documents in a given directory.

    Args:
        root_dir (str): The path to the directory containing documents to be iterated.

    This function initializes a document manager with the specified root directory and calls
    the iter_docs method to handle the processing of each document.

    Example:
        pythion src
    """

    manager = DocManager(root_dir=root_dir)
    manager.iter_docs()


@click.command()
@click.option(
    "-ci",
    "--custom-instruction",
    help="Any custom instructions to provide to the AI to guide the output",
)
@click.option(
    "-p",
    "--profile",
    type=click.Choice(["no-version"]),
    help="Select a predefined custom instruction set",
)
def make_commit(custom_instruction: str | None = None, profile: str | None = None):
    """
    Executes a commit by generating a commit message based on staged changes and optional custom instructions.

    Args:
        custom_instruction (str | None): Custom instructions to provide to the AI to guide the output of the commit message.

    Raises:
        RuntimeError: If no changes are found in the staging area when attempting to commit.

    Example Usage:
        - Run make_commit with no custom instructions
        pythion make-commit

        - Run make_commit with custom instructions
        pythion make-commit --custom-instruction 'Added new feature to optimize performance'
    """
    try:
        handle_commit(custom_instruction, profile)
    except RuntimeError as e:
        print(e)
        sys.exit(1)


@click.command()
@click.option("-r", "--version-regex", help="Regex pattern to match", required=True)
@click.option(
    "-f",
    "--file-path",
    help="Fullly qualified path that contains the version file",
    required=True,
)
def bump_version(version_regex: str, file_path: str):
    """
    Bump version numbers in a specified version file.

    Usage:
      bump_version --version-regex <pattern> --file-path <file>

    Args:
      version_regex (str): A regex pattern to match the version string in the file.
      file_path (str): The full path to the file that contains the version string.

    Examples:
      bump_version --version-regex 'version="(.*?)"' --file-path '/path/to/version_file.txt'

    This will search for the version format 'version="x.y.z"' in the specified file and increment the patch version.
    """

    print(file_path, version_regex)
    try:
        execute_bump_version(file_path, version_regex)
    except RuntimeError as e:
        print(e)
        sys.exit(1)


pythion.add_command(docs)
pythion.add_command(module_docs)
pythion.add_command(build_cache)
pythion.add_command(iter_docs)
pythion.add_command(make_commit)
pythion.add_command(bump_version)

if __name__ == "__main__":
    pythion()
