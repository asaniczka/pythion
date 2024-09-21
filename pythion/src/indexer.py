"""
Main indexer of pythion
"""

import ast
import os
from collections import defaultdict
from copy import deepcopy
from itertools import chain
from pathlib import Path

from rich import print


class CallFinder(ast.NodeVisitor):
    """Class that traverses an Abstract Syntax Tree (AST) to find function
    calls.

    This class inherits from `ast.NodeVisitor` and overrides visit methods to
    specifically process function and class definitions, as well as function
    call nodes. It stores the names of called functions that match the
    specified criteria in a provided set.

    Args:
        call_names (set[str]): A set of names to store function calls found in
    the AST.

    Attributes:
        calls (set): A set that accumulates the names of all found function
        calls."""

    def __init__(self, call_names: set[str]) -> None:
        """Initializes the object with a set of call names.

        Args:
            call_names (set[str]): A set of names for the calls managed by this
            instance.

        Attributes:
            calls (set): A set to track calls, initialized as empty.
            call_names (set): The input set of call names assigned to the instance."""
        self.calls = set()
        self.call_names = call_names

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Visits a FunctionDef node in an Abstract Syntax Tree (AST).

        This method processes a FunctionDef node by calling the generic_visit
        method, allowing for traversal of the AST tree.

        Args:
            node (ast.FunctionDef): The FunctionDef node to visit, which encapsulates
            details about a function definition in the source code being analyzed.

        Returns:
            None: This method does not return anything, as it is intended to traverse
            and process the AST."""
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        """Visits a class definition node in an Abstract Syntax Tree (AST).

        This method is part of a visitor pattern implementation,
        allowing traversal of class definitions and performing any
        defined operations on them. It leverages the generic_visit
        method to handle any additional processing or visiting
        of child nodes automatically.

        Args:
            node (ast.ClassDef): An instance of ast.ClassDef,
            representing a class definition in the AST."""
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        """Processes a function call node in an abstract syntax tree (AST).

        This method checks if the called function is identified by a name. If it is,
        the name of the function is added to the call_names set for later analysis.

        Args:
            node (ast.Call): The AST node representing the function call."""
        if isinstance(node.func, ast.Name):
            self.call_names.add(node.func.id)


class NodeTransformer(ast.NodeTransformer):
    """Transform AST nodes for functions and classes to include docstrings and
    maintain an index.

    Args:
        node (ast.FunctionDef | ast.ClassDef): An AST node representing a function or
        class definition.

    Returns:
        ast.FunctionDef | ast.ClassDef: The transformed AST node after cleaning and
        index updating."""

    def __init__(self, index: dict[str, set[str]]) -> None:
        """Initializes the instance with an index.

        This constructor takes a dictionary
        that maps string keys to sets of strings, allowing the storage of a
        collection of related strings for each key.

        Args:
            index (dict[str, set[str]]): A mapping of string keys to sets of
                strings used for indexing. This structure is ideal for cases
                where multiple values need to be associated with a single key."""
        self.index: dict[str, set[str]] = index

    def clean_function(self, node: ast.FunctionDef) -> ast.FunctionDef:
        """Cleans the AST representation of a function definition by removing an
        initial expression if it is a constant. This is particularly useful for
        refactoring or cleaning up code generated for abstract syntax trees (AST).

        Args:
            node (ast.FunctionDef): The AST node representing a function definition.

        Returns:
            ast.FunctionDef: The cleaned function definition node, with the
            initial expression removed if it was a constant. If the input
            node is not a FunctionDef, it is returned unchanged."""
        if not isinstance(node, ast.FunctionDef):
            return node
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
        ):
            node.body.pop(0)
        return node

    def clean_class(self, node: ast.ClassDef) -> ast.ClassDef:
        """Cleans up an abstract syntax tree (AST) representation of a class by removing
        certain elements and applying transformations to its body.

        Args:
            node (ast.ClassDef): The ClassDef node in the AST to be cleaned.

        Returns:
            ast.ClassDef: The modified class node after cleaning.

        This method checks if the provided node is an instance of ast.ClassDef. If the first
        statement in the class body is an expression containing a constant, it removes it.
        It then iterates through the class body statements, applying the clean_function if
        the statement is a function definition or recursively calling clean_class if it's
        another class definition within the class body."""
        if not isinstance(node, ast.ClassDef):
            return node
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
        ):
            node.body.pop(0)
        for stmt in node.body:
            if isinstance(stmt, ast.FunctionDef):
                stmt = self.clean_function(stmt)
            if isinstance(stmt, ast.ClassDef):
                stmt = self.clean_class(stmt)
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        """Visits a function definition node in the Abstract Syntax Tree (AST).

        This method cleans the function node, processes any child nodes, and indexes
        its textual representation. It returns the modified function node.

        Args:
            node (ast.FunctionDef): The function definition node to visit.

        Returns:
            ast.FunctionDef: The processed and cleaned function definition node."""
        node = self.clean_function(node)
        self.generic_visit(node)
        node_in_text = ast.unparse(node)
        self.index[node.name].add(node_in_text)
        return node

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.ClassDef:
        """Process a class definition node in the AST.

        This method cleans the class node, performs a generic visit for further
        processing, and indexes its source representation. The indexed data can be
        used for analysis or transformations of the class structure.

        Args:
            node (ast.ClassDef): The class definition node to process.

        Returns:
            ast.ClassDef: The processed and cleaned class definition node."""
        node = self.clean_class(node)
        self.generic_visit(node)
        node_in_text = ast.unparse(node)
        self.index[node.name].add(node_in_text)
        return node


class NodeIndexer:
    """Initializes the NodeIndexer with the specified root directory and optional
    folders to ignore.

    Args:
        root_dir (str): The root directory to index.
        folders_to_ignore (list[str] | None): Optional list of folders to ignore during
        indexing.

    Returns:
        None

    Raises:
        None"""

    def __init__(
        self, root_dir: str, folders_to_ignore: list[str] | None = None
    ) -> None:
        """Initializes the object with the specified root directory and optional
        ignored folders.

        Args:
            root_dir (str): The path to the root directory to index.
            folders_to_ignore (list[str] | None): A list of folder names to ignore,
                defaulting to None. If provided, these will be appended to a
                predefined list of ignored folders.

        Returns:
            None: This constructor does not return any value.

        Raises:
            None: This function does not raise exceptions explicitly but may raise
                any exceptions from dependent methods like build_index and warn."""
        self.root_dir = root_dir
        self.index: dict[str, set[str]] = defaultdict(set)
        self.folders_to_ignore = [".venv", ".mypy_cache"]
        if folders_to_ignore:
            self.folders_to_ignore.extend(folders_to_ignore)
        self.build_index()
        self.warn()

    def build_index(self):
        """Builds an index of Python function and class definitions found in the
        specified directory.

        This function recursively traverses the root directory, ignoring specified
        folders, and processes Python files to extract function and class
        definitions. The extracted elements are processed using a
        NodeTransformer to clean up the syntax and are then added to the
        index. It also removes common syntax elements after processing.

        Attributes:
            self.index (dict): A dictionary for collecting function and class
            definitions.
            self.root_dir (str): The root directory where the search begins.
            self.folders_to_ignore (list): A list of folder names to ignore during
            traversal."""
        transformer = NodeTransformer(self.index)
        for root, _, files in os.walk(self.root_dir):
            for file in files:
                for ext in self.folders_to_ignore:
                    if ext in root:
                        break
                else:
                    if not file.endswith(".py"):
                        continue
                    file_path = Path(root, file)
                    tree = ast.parse(file_path.read_text(encoding="utf-8"))
                    for node in ast.walk(tree):
                        node = transformer.visit(node)
        self._remove_common_syntax()

    def _remove_common_syntax(self):
        """Removes common syntax elements from the index.

        This function iterates over a predefined list of common
        syntax elements and removes each from the index if it exists.
        These elements include special methods and built-in types such as
        '__init__', '__enter__', '__exit__', 'str', 'dict', 'list', 'int',
        and 'float'.

        It does not return any value."""
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
        """Extracts unique function or method call names from a given AST node.

        Args:
            node (ast.FunctionDef | ast.ClassDef): The AST node representing a
            function or class definition from which to extract call names.

        Returns:
            list[str]: A list of unique call names found within the specified
            AST node."""
        call_names = set()
        call_finder = CallFinder(call_names)
        call_finder.visit(node)
        return list(call_names)

    def _get_args(self, node: ast.FunctionDef) -> list[str] | None:
        """Extracts the argument types from a function definition node.

        Args:
            node (ast.FunctionDef): The function definition node from which to extract
            argument types.

        Returns:
            list[str] | None: A list of argument types as strings if the node is a
            valid FunctionDef, otherwise None."""
        if not isinstance(node, ast.FunctionDef):
            return None
        arg_types = set()
        for arg in node.args.args:
            if isinstance(arg.annotation, ast.Name):
                arg_types.add(arg.annotation.id)
        return list(arg_types)

    def get_dependencies(self, func_name: str) -> list[str] | None:
        """Retrieve a list of dependencies for a specified function name from an index.

        This method parses the function's Abstract Syntax Tree (AST),
        extracts function calls and argument types, and returns a list
        of dependencies found in the index. If the function is not present,
        it returns None.

        Args:
            func_name (str): The name of the function for which dependencies are being
                retrieved.

        Returns:
            list[str] | None: A list of dependencies or None if the function is not
                found in the index."""
        func = self.index.get(func_name)
        if not func:
            return None
        node = ast.parse(list(func)[0])
        if isinstance(node, ast.Module):
            node = node.body[0]
        call_names = self._get_call_tree(node)
        arg_types = self._get_args(node)
        dependencies = []
        for dep in chain(call_names, arg_types or []):
            if dep in self.index:
                dependencies.extend(list(self.index[dep]))
        dependencies = [x[:3000] for x in dependencies]
        return dependencies

    def warn(self):
        """Checks for duplicate names in the index.

        This method iterates through the index attribute and identifies any names that appear more than once. It collects these duplicate names and, if any are found, prints a warning message indicating the duplicates. This warning serves as a notification to the user that while not critical, the presence of duplicate names may lead to incorrect docstring generation or other issues.

        Attributes:
            index (dict): A dictionary where keys are names and values are associated data (e.g., docstring).

        Returns:
            None: This method does not return any value."""
        duplicate_names = []
        for k, v in self.index.items():
            if len(v) > 1:
                duplicate_names.append(k)
        if not duplicate_names:
            return
        print(
            "WARN: The following names are being duplicated. This is not critical, but might lead to incorrect docstrings.",
            duplicate_names,
        )


if __name__ == "__main__":
    indexer = NodeIndexer(".")
    deps = indexer.get_dependencies("entry_cluster_post")
    print(deps)
