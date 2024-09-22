import click
from wrapworks import cwdtoenv # type: ignore

cwdtoenv()

from pythion.src.indexer import NodeIndexer
from pythion.src.doc_writer import DocManager


@click.group()
def pythion():
    """
    A command-line interface (CLI) application built using Click. This application serves as the entry point for various commands and functionalities, allowing users to interact with the application easily. It organizes different command groups under a unified interface and provides user-friendly command-line options.
    """
    pass


@click.command()
@click.argument("root_dir")
@click.option(
    "-ua",
    "--use_all",
    is_flag=True,
    default=False,
    help="Whether to generate doc strings for all functions, or just the ones without docstrings",
)
def build_doc_cache(root_dir: str, use_all: bool):
    """
    Builds a documentation cache for functions and methods in the specified directory.

    This command scans the Python files in the given `root_dir` and generates or updates docstrings,
    optionally including functions that already have existing docstrings based on the `use_all` flag.

    Args:
        root_dir (str): The directory path where the Python files are located.
        use_all (bool): If True, generate docstrings for all functions; otherwise, only for those without docstrings.

    Example:
        pythion /path/to/dir --use_all
    """
    manager = DocManager(root_dir=root_dir)
    manager.build_doc_cache(use_all)


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
        pythion /path/to/dir
    """

    manager = DocManager(root_dir=root_dir)
    manager.iter_docs()


@click.command()
@click.argument("root_dir")
def make_docstr(root_dir: str):
    """
    Generates documentation strings for Python files located in the specified root directory.

    This CLI command utilizes the DocManager class to create or update docstrings by examining the source code in the given `root_dir`. The process includes identifying modules that lack documentation and integrating with a caching system to store generated docstrings for efficient access.

    Args:
        root_dir (str): The path to the root directory containing the Python files to analyze.

    Example:
        pythion /path/to/dir
    """
    manager = DocManager(root_dir=root_dir)
    manager.make_docstrings()


pythion.add_command(build_doc_cache)
pythion.add_command(iter_docs)
pythion.add_command(make_docstr)

if __name__ == "__main__":
    pythion()
