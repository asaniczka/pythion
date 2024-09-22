import click
from wrapworks import cwdtoenv  # type: ignore

cwdtoenv()

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
    "-ca", "--custom-instruction", help="Any custom instructions to provide to the AI"
)
def make_docs(root_dir: str, custom_instruction: str | None = None):
    """
    Generates docstrings for Python files located in the specified root directory.

    Args:
        root_dir (str): The path to the directory containing Python files.
        custom_instruction (str, optional): Custom instruction to guide the AI in generating docstrings.

    Examples:
        - pythion make-docs src -ca 'Provide detailed explanations'.
    """
    manager = DocManager(root_dir=root_dir)
    manager.make_docstrings(custom_instruction)


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
    help="Whether to generate doc strings for all functions, or just the ones without docstrings",
)
def build_doc_cache(root_dir: str, use_all: bool, dry: bool):
    """
    Generates documentation cache based on function docstrings in the specified root directory.

    Args:
        root_dir (str): The root directory containing the Python files whose functions need documentation.
        use_all (bool): Optional; if set, generates docstrings for all functions. Defaults to False, which means only functions without docstrings will be processed.
        dry (bool): Optional; if set, performs a dry run without making any changes. Defaults to False.

    Example:
        pythion src --use_all --dry
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


pythion.add_command(make_docs)
pythion.add_command(build_doc_cache)
pythion.add_command(iter_docs)

if __name__ == "__main__":
    pythion()
