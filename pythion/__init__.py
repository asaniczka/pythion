import click
from wrapworks import cwdtoenv  # type: ignore

cwdtoenv()

from pythion.src.commit_writer import handle_commit
from pythion.src.doc_writer import DocManager


@click.group()
def pythion():
    """
    Pythion is a command-line interface for managing Python documentation and version control. Use it to generate docstrings, build documentation caches, iterate through documents, and create smart commit messages, all while enhancing your development workflow.
    """
    pass


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
def make_docs(
    root_dir: str, custom_instruction: str | None = None, profile: str | None = None
):
    """
    Generates docstrings for Python code in the specified root directory.

    Args:
        root_dir (str): The root directory containing Python code files.
        custom_instruction (str | None): Optional; any specific instructions for generating docstrings.
        profile (str | None): Optional; can be 'fastapi' or 'cli' to specify the generation profile.

    Examples:
        - Generate docstrings for code in the specified directory with default settings
        make_docs /path/to/code

        - Generate docstrings with a custom instruction
        make_docs /path/to/code --custom-instruction "Focus on parameters documentation"

        - Generate docstrings using the 'fastapi' profile
        make_docs /path/to/code -p fastapi
    """
    manager = DocManager(root_dir=root_dir)
    manager.make_docstrings(custom_instruction, profile)


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


pythion.add_command(make_docs)
pythion.add_command(build_cache)
pythion.add_command(iter_docs)
pythion.add_command(make_commit)

if __name__ == "__main__":
    pythion()
