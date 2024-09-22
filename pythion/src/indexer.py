"""
Main indexer of pythion
"""

# pylint: disable=wrong-import-position

import ast
import os
from collections import defaultdict
from copy import deepcopy
from itertools import chain
from pathlib import Path

from rich import print
from wrapworks import cwdtoenv  # type: ignore

cwdtoenv()

from pythion.src.models.core_models import SourceCode


class CallFinder(ast.NodeVisitor):
    """
    Class to find function call names in Python AST.

    This class traverses the Abstract Syntax Tree (AST) of Python code
    and collects names of all function calls encountered.

    Attributes:
        calls (set): A set of unique function call names found during traversal.
        call_names (set): A set that stores names of calls added by the visit_Call method.

    Methods:
        visit_FunctionDef(node): Visits a FunctionDef node and processes it.
        visit_ClassDef(node): Visits a ClassDef node and processes it.
        visit_Call(node): Visits a Call node and adds the function name to the call_names set if it is a direct call.
    """

    def __init__(self, call_names: set[str]) -> None:
        """"""
        self.call_names: set[str] = call_names

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """
        Visits a class definition node in an Abstract Syntax Tree (AST).

        This method is part of a visitor pattern for traversing AST nodes. It calls the
        `generic_visit` method to handle the visit according to the AST structure.

        Args:
            node (ast.ClassDef): The class definition node to be visited.

        Returns:
            None: This method does not return a value but may modify the state of the
        dynamic visitor depending on its implementation.
        """
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        """
        Visits a FunctionDef node in an Abstract Syntax Tree (AST).

        This method is part of an AST visitor pattern, processing a node
        representing a function definition. It calls the generic_visit
        method to handle visits to child nodes if necessary.

        Args:
            node (ast.FunctionDef): The AST node representing a function
            definition to be visited.

        Returns:
            None: This method does not return a value.

        Note:
            This function is typically called as part of an AST traversal,
            where function definitions are processed according to specific
            visitor logic.
        """
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        """
        Visits a function call node in an AST (Abstract Syntax Tree).

        Args:
            node (ast.Call): The node representing a function call in the AST.

        This method checks if the function being called is a named function (i.e., not a method or lambda). If it is, it adds the function's name to the 'call_names' set for tracking purposes.
        """
        if isinstance(node.func, ast.Name):
            self.call_names.add(node.func.id)


class NodeTransformer(ast.NodeTransformer):
    """
    NodeTransformer is a class that traverses and transforms AST nodes for functions and classes.

    It removes docstrings from function and class definitions, while maintaining relevant metadata. The transformed nodes are stored in an index along with their type and file path.

    Attributes:
        index (dict[str, set[SourceCode]]): A mapping from function/class names to their source code.
        current_path (str): The path to the current source file.

    Methods:
        visit_FunctionDef(node): Processes a function definition node, cleaning any docstring.
        visit_ClassDef(node): Processes a class definition node, cleaning any docstring.
    """

    def __init__(self, index: dict[str, set[SourceCode]], current_path: str) -> None:
        """"""
        self.index: dict[str, set[SourceCode]] = index
        self.current_path: str = current_path

    def clean_function(self, node: ast.FunctionDef) -> tuple[ast.FunctionDef, bool]:
        """
        Cleans the provided AST function definition by removing the docstring if present.

        Args:
            self: The instance of the class that this method is part of.
            node (ast.FunctionDef): The AST node representing a function definition.

        Returns:
            tuple: A tuple containing the cleaned node (ast.FunctionDef) and a boolean indicating
            whether a docstring was present and removed.
        """
        has_docstring = False
        if not isinstance(node, ast.FunctionDef):
            return node, has_docstring
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
        ):
            has_docstring = len(node.body[0].value.value.strip()) > 1
            node.body.pop(0)

        return node, has_docstring

    def clean_class(self, node: ast.ClassDef) -> tuple[ast.ClassDef, bool]:
        """
        Cleans up a class definition by removing its docstring and checking if it exists.

        Args:
            self: The instance of the class containing this method.
            node (ast.ClassDef): The AST node representing a class definition.

        Returns:
            tuple: A tuple containing the cleaned class definition and a boolean indicating whether a docstring was found.

        Notes:
            This method traverses the body of the class, applying the cleaning process to any contained function definitions and class definitions. It assumes that the first statement may be a docstring, which it will remove if present.
        """

        has_docstring = False
        if not isinstance(node, ast.ClassDef):
            return node, has_docstring
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
        ):
            has_docstring = len(node.body[0].value.value.strip()) > 1
            node.body.pop(0)

        for stmt in node.body:
            if isinstance(stmt, ast.FunctionDef):
                stmt = self.clean_function(stmt)  # type: ignore
            if isinstance(stmt, ast.ClassDef):
                stmt = self.clean_class(stmt)  # type: ignore

        return node, has_docstring

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        """
        Processes and cleans a FunctionDef AST node and indexes its details.

        Args:
            node (ast.FunctionDef): The AST node representing a function definition.

        Returns:
            ast.FunctionDef: The cleaned and processed function definition node.
        """
        clean_node, has_docstring = self.clean_function(deepcopy(node))
        self.generic_visit(node)
        self.index[clean_node.name].add(
            SourceCode(
                object_name=clean_node.name,
                object_type="function",
                file_path=self.current_path,
                source_code=ast.unparse(clean_node),
                has_docstring=has_docstring,
            )
        )
        return node

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.ClassDef:
        """
        Processes a class definition node in an Abstract Syntax Tree (AST).

        Args:
            node (ast.ClassDef): The class definition node to be processed.

        Returns:
            ast.ClassDef: The original class definition node after processing.

        This method cleans the provided class node and logs relevant details, such as the class's source code and whether it contains a docstring, for further analysis.
        """
        clean_node, has_docstring = self.clean_class(deepcopy(node))
        self.generic_visit(node)
        self.index[clean_node.name].add(
            SourceCode(
                object_name=clean_node.name,
                object_type="class",
                file_path=self.current_path,
                source_code=ast.unparse(clean_node),
                has_docstring=has_docstring,
            )
        )
        return node


class NodeIndexer:
    """
    Initializes the NodeIndexer with a directory and optional folders to ignore.

    This class traverses the specified directory to build an index of Python source code files.
    It collects function and class definitions, including their dependencies, while ignoring specified folders.

    Args:
        root_dir (str): The root directory path to search for Python files.
        folders_to_ignore (list[str] | None): A list of folder names to ignore during traversal.
        Defaults to ['.venv', '.mypy_cache'].

    Raises:
        ValueError: If the root directory does not exist or is not a directory.
    """

    def __init__(
        self, root_dir: str, folders_to_ignore: list[str] | None = None
    ) -> None:
        """"""
        self.root_dir = root_dir
        self.index: dict[str, set[SourceCode]] = defaultdict(set)
        self.folders_to_ignore = [".venv", ".mypy_cache"]
        if folders_to_ignore:
            self.folders_to_ignore.extend(folders_to_ignore)
        self.build_index()
        self.warn()

    def build_index(self):
        """
        Builds an index of Python source code files within a specified directory.

        This method traverses the directory tree starting from 'root_dir'. It processes each '.py' file,
        ignoring specified folders, and utilizes the NodeTransformer to analyze the abstract syntax tree (AST) of each
        file to index functions and classes. The index generated is stored in 'self.index'. Common syntax patterns
        are removed after processing.

        Attributes:
            root_dir (str): The root directory to start searching.
            folders_to_ignore (list): List of directory names to be ignored.
            index (dict): Dictionary to store code indexes.

        Returns:
            None: This method does not return any value.
        """
        for root, _, files in os.walk(self.root_dir):
            for file in files:
                for ext in self.folders_to_ignore:
                    if ext in root:
                        break
                else:
                    if not file.endswith(".py"):
                        continue
                    file_path = Path(root, file)
                    transformer = NodeTransformer(self.index, str(file_path))
                    tree = ast.parse(file_path.read_text(encoding="utf-8"))
                    for node in ast.walk(tree):
                        node = transformer.visit(node)
        self._remove_common_syntax()

    def _remove_common_syntax(self):
        """
        Remove common syntax entries from the index.

        This method checks for predefined common syntax terms such as special methods and built-in types,
        then removes them from the index if they exist. The common syntax terms targeted for removal
        include '__init__', '__enter__', '__exit__', 'str', 'dict', 'list', 'int', and 'float'.

        Effectively streamlining the index by eliminating redundant entries helps maintain clarity
        and improves lookup efficiency for unique items.
        """
        common_syntax = [
            "__init__",
            "__enter__",
            "__exit__",
            "str",
            "dict",
            "list",
            "int",
            "float",
        ]
        for syntax in common_syntax:
            self.index.pop(syntax, None)

    def _get_call_tree(self, node: ast.FunctionDef | ast.ClassDef) -> list[str]:
        """
        Extracts names of function calls from a given AST node.

        Args:
            node (ast.FunctionDef | ast.ClassDef): The AST node to analyze, which can be a function or a class definition.

        Returns:
            list[str]: A list of names of function calls found within the specified AST node.
        """
        call_names: set[str] = set()
        call_finder = CallFinder(call_names)
        call_finder.visit(node)
        return list(call_names)

    def _get_args(self, node: ast.FunctionDef) -> list[str] | None:
        """
        Extracts the argument types from a given function definition node.

        Args:
            self: The instance of the class where this method is defined.
            node (ast.FunctionDef): The AST node representing a function definition.

        Returns:
            list[str] | None: A list of argument type names if the node is a function definition; otherwise, returns None.
        """
        if not isinstance(node, ast.FunctionDef):
            return None
        arg_types = set()
        for arg in node.args.args:
            if isinstance(arg.annotation, ast.Name):
                arg_types.add(arg.annotation.id)
        return list(arg_types)

    def get_dependencies(self, func_name: str) -> list[str] | None:
        """
        Retrieves the dependencies for a specified function name.

        This method searches for the function in an internal index and parses its source code to identify any function calls and argument types used within it. The dependencies are then gathered from the index and returned as a list of source code snippets, truncated to 3000 characters.

        Args:
            func_name (str): The name of the function for which dependencies are being retrieved.

        Returns:
            list[str] | None: A list of source code snippets representing the dependencies,
            or None if the function is not found in the index.
        """
        func = self.index.get(func_name)
        if not func:
            return None

        node = ast.parse(list(func)[0].source_code)
        if isinstance(node, ast.Module):
            node = node.body[0]  # type: ignore

        call_names = self._get_call_tree(node)  # type: ignore
        arg_types = self._get_args(node)  # type: ignore

        dependencies: list[SourceCode] = []
        for dep in chain(call_names, arg_types or []):
            if dep in self.index:
                dependencies.extend(list(self.index[dep]))
        dependencies_src: list[str] = [x.source_code[:3000] for x in dependencies]
        return dependencies_src

    def warn(self):
        """
        Generates a warning for duplicated names in the index.

        This method scans through the index attribute of the instance, identifying any names that are present more than once. If duplicates are found, it prints a warning message along with the locations of each duplicate. While this is not a critical issue, it may lead to incorrect documentation generation.

        Attributes:
            index (dict): A dictionary mapping names to their associated source code locations.

        Returns:
            None: This method does not return a value.
        """
        duplicate_names: list[SourceCode] = []
        for k, v in self.index.items():
            if len(v) > 1:
                duplicate_names.extend(list(v))
        if not duplicate_names:
            return
        print(
            "WARN: The following names are being duplicated. This is not critical, but might lead to incorrect docstrings.",
        )
        for dup in duplicate_names:
            print(dup.location)


if __name__ == "__main__":
    indexer = NodeIndexer(".")
    print(indexer.index)
