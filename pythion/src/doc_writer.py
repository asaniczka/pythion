import ast
import os
from pathlib import Path

from openai import OpenAI
from pydantic import BaseModel
from rich import print
from wrapworks import cwdtoenv

cwdtoenv()
from pythion import NodeIndexer


class DocManager:
    def __init__(
        self,
        root_dir: str,
        only_new: bool = True,
        folders_to_ignore: list[str] | None = None,
    ) -> None:
        """Initializes a new instance of the class.

        This constructor sets up the root directory, configuration for
        the indexing process, and initializes the NodeIndexer.

        Args:
            root_dir (str): The path to the root directory to be indexed.
            only_new (bool, optional): If True, only index new files. Defaults to True.
            folders_to_ignore (list[str] | None, optional): A list of folder names to ignore
        during indexing. Defaults to None. The standard folders ignored are '.venv' and
        '.mypy_cache', which are always included in the ignore list if not specified.

        Returns:
            None: This method does not return any value."""
        self.root_dir: str = root_dir
        self.only_new: bool = only_new
        self.folders_to_ignore = [".venv", ".mypy_cache"]
        self.indexer = NodeIndexer(root_dir, folders_to_ignore=folders_to_ignore)
        if folders_to_ignore:
            self.folders_to_ignore += folders_to_ignore

    def make_docstrings(self):
        """Generates docstrings for Python source files in the specified
        path.

        This function retrieves all files to parse using a private method,
        _walk(), and processes each file through the _handle_file method.

        It does not return any value; instead, it modifies the existing files or
        creates new ones with the appropriate docstring format."""
        files_to_parse = self._walk()
        for file in files_to_parse:
            self._handle_file(file)

    def _walk(self):
        """Walks through the directory tree starting from the specified root directory
        and collects paths of all Python files while ignoring certain folders.

        Returns:
            list[Path]: A list of Path objects representing Python files found within
        the specified directory tree."""
        files_to_parse: list[Path] = []
        for root, _, files in os.walk(self.root_dir):
            for file in files:
                for ext in self.folders_to_ignore:
                    if ext in root:
                        break
                else:
                    if not file.endswith(".py"):
                        continue
                    file_path = Path(root, file)
                    files_to_parse.append(file_path)
        return files_to_parse

    def _handle_file(self, file_path: Path):
        """Handles loading a Python file, processing its functions and classes to add or
        update their docstrings based on existing content and generated documentation.

        Args:
            file_path (Path): The path to the Python file to be processed.

        This method reads the specified file, parses its Abstract Syntax Tree (AST), and
        iterates through its nodes. It checks for existing docstrings in functions and
        classes, and either retains or generates new docstrings if needed. The
        processed tree is then written back to the original file."""
        print(f"Loading file '{file_path}'")
        tree = ast.parse(file_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                continue
            have_doc = False
            if isinstance(node.body[0], ast.Expr) and isinstance(
                node.body[0].value, ast.Constant
            ):
                current_doc = node.body[0].value.value.strip()
                have_doc = bool(current_doc)
            if self.only_new and have_doc:
                continue
            if isinstance(node.body[0], ast.Expr) and isinstance(
                node.body[0].value, ast.Constant
            ):
                _ = node.body.pop(0)
            func_code = ast.unparse(node)
            func_name = node.name
            dependencies = self.indexer.get_dependencies(func_name)
            try:
                doc_string = self._generate_doc(func_name, func_code, dependencies)
            except Exception as e:
                print(e)
                continue
            doc_string = doc_string.strip(" '\"")
            if not doc_string:
                continue
            node.body.insert(0, ast.Expr(ast.Constant(doc_string.strip())))
        file_path.write_text(ast.unparse(tree), encoding="utf-8")

    def _generate_doc(self, func_name: str, func_code: str, dependencies: list[str]):
        """Generates a docstring for a given function.

        This function accepts the name and code of a target function, along with any relevant
        dependencies. It utilizes the OpenAI API to create a structured docstring in the
        Google Style format. If no dependencies are provided, an empty list is assigned.

        Args:
            func_name (str): The name of the function for which the docstring is generated.
            func_code (str): The source code of the function.
            dependencies (list[str]): A list of dependencies that the function relies on.

        Returns:
            str: The generated docstring for the specified function."""
        print(f"Generating docstrings for '{func_name}'")
        client = OpenAI(timeout=30)
        if not dependencies:
            dependencies = []

        class Step(BaseModel):
            """Represents a step in a process with an explanation and expected output.

            Attributes:
                explanation (str): A brief description of the step."""

            explanation: str

        class DocString(BaseModel):
            """Generates a structured docstring for a given Python function."""

            steps: list[Step]
            main_func_name: str
            main_func_docstring: str

        completion = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a Python docstring writer. Your task is to look at the main function, it's arguments, dependencies and write a docstring for the main function. Only share the the docstring for the main function.\n\nThe format I want is Google Style. Try to keep the length to less than 150 words. Max line length=88 characters",
                },
                {"role": "user", "content": "Main Function Name: " + func_name},
                {"role": "user", "content": "Main function source code: " + func_code},
                {
                    "role": "user",
                    "content": "Dependency Source code: " + "\n\n".join(dependencies),
                },
            ],
            response_format=DocString,
        )
        ai_repsonse = completion.choices[0].message
        return ai_repsonse.parsed.main_func_docstring


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    manager = DocManager(".", only_new=False)
    manager.make_docstrings()
