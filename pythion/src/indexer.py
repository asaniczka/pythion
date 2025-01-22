"""
Module for indexing Python source code.
    
This module defines classes and methods to:
- Analyze Python files and construct an index of functions and classes.
- Remove unnecessary docstrings from defined functions and classes.
- Retrieve dependencies and call relationships between functions and classes.

Classes:
- CallFinder: Finds function call names in the AST.
- NodeTransformer: Cleans and transforms AST nodes for functions and classes.
- NodeIndexer: Indexes Python source files and manages dependencies.
"""

# pylint: disable=wrong-import-position

import ast
import json
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

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
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

        if isinstance(node.func, ast.Attribute):
            self.call_names.add(node.func.attr)


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
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
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

    def visit_AsyncFunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
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
        self.file_index: set[str] = set()
        self.folders_to_ignore = [".venv", ".mypy_cache"]
        if folders_to_ignore:
            self.folders_to_ignore.extend(folders_to_ignore)
        self.build_index()

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
                    self.file_index.add(str(file_path))
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
            "__eq__",
            "__hash__",
            "str",
            "dict",
            "list",
            "int",
            "float",
            "setUp",
            "tearDown",
            "setUpClass",
            "tearDownClass",
        ]
        for syntax in common_syntax:
            self.index.pop(syntax, None)

    def _get_call_tree(
        self,
        node: ast.FunctionDef | ast.ClassDef | ast.Module | ast.stmt,
        visited: set[str] | None = None,
        recursive: bool = False,
    ) -> set[str]:
        """
        Retrieve the call tree for a given function or class definition.

        This method analyzes the provided AST node and collects all function and class calls,
        including those from recursively called definitions if specified.

        Args:
            node (ast.FunctionDef | ast.ClassDef): The AST node representing a function or class to analyze.
            visited (set[str], optional): A set to keep track of already visited object names to prevent duplication.
            recursive (bool, optional): If True, also include calls from definitions that are reached recursively.

        Returns:
            set[str]: A set of names for all collected function and class calls.
        """
        visited = visited or set()
        call_names: set[str] = set()
        call_finder = CallFinder(call_names)
        call_finder.visit(node)
        if recursive:
            for call in deepcopy(call_names):
                dep_node = self.index.get(call)
                if not dep_node:
                    continue
                for sub_node in dep_node:
                    if sub_node.object_name in visited:
                        continue
                    visited.add(sub_node.object_name)
                    sub_calls = self._get_call_tree(
                        ast.parse(sub_node.source_code),
                        recursive=recursive,
                        visited=visited,
                    )
                    call_names.update(sub_calls)

        return call_names

    def _get_args(self, node: ast.FunctionDef) -> set[str] | None:
        """
        Extracts argument types from a function definition node.

        Args:
            node (ast.FunctionDef): The function definition node from which to extract argument types.

        Returns:
            set[str] | None: A set of argument type names if the node is a valid function definition, otherwise None.

        Raises:
            TypeError: If the input node is not an instance of ast.FunctionDef.
        """
        if not isinstance(node, ast.FunctionDef):
            return None
        arg_types: set[str] = set()
        for arg in node.args.args:
            if isinstance(arg.annotation, ast.Name):
                arg_types.add(arg.annotation.id)
            if isinstance(arg.annotation, ast.BinOp):
                sub_types = self._get_arg_from_binop(arg.annotation)
                arg_types.update(sub_types)
            if isinstance(arg.annotation, ast.Subscript):
                if not isinstance(arg.annotation.slice, ast.Tuple):
                    continue
                for elt in arg.annotation.slice.elts:
                    if isinstance(elt, ast.Name):
                        arg_types.add(elt.id)

        return arg_types

    def _get_arg_from_binop(self, op: ast.BinOp) -> set[str]:
        """
        Retrieve argument names from a binary operation.

        Args:
            op (ast.BinOp): The binary operation from which to extract argument names.

        Returns:
            set[str]: A set of argument names found in the binary operation.
        """

        arg_types: set[str] = set()
        for nest_op in [op.left, op.right]:
            if isinstance(nest_op, ast.Name):
                arg_types.add(nest_op.id)
            if isinstance(nest_op, ast.BinOp):
                sub_types = self._get_arg_from_binop(nest_op)
                arg_types.update(sub_types)

        return arg_types

    def get_dependencies(
        self,
        obj_name: str,
        obj_id: str | None = None,
        recursive: bool = False,
    ) -> list[str] | None:
        """
        Retrieves the dependencies for a specified object name.

        Args:
            obj_name (str): The name of the object to find dependencies for.
            obj_id (str | None, optional): The unique identifier for the specific object instance. Defaults to None.
            recursive (bool, optional): Determines whether to search for dependencies recursively. Defaults to False.

        Returns:
            list[str] | None: A list of JSON strings representing the dependencies, or None if not found.

        Raises:
            TypeError: If there is a name collision and no object ID is provided.
        """
        objs = self.index.get(obj_name)
        if not objs:
            return None

        if len(objs) > 1 and not obj_id:
            raise TypeError(
                "ERROR: Name collision. Unable to get dependencies without an object ID"
            )

        for obj in objs:
            if obj.object_id == obj_id:
                node = obj
                break
        else:
            raise ValueError("Invalid Object ID")

        arg_types: set[str] = set()
        node_src: ast.Module | ast.stmt | ast.FunctionDef | ast.ClassDef = ast.parse(
            node.source_code
        )
        if isinstance(node, ast.Module):
            node = node.body[0]  # type: ignore

        call_names = self._get_call_tree(node_src, recursive=recursive)

        for call in chain([obj_name], call_names):
            source = self.index.get(call)
            if source:
                for obj in source:
                    source_code: ast.Module | ast.stmt = ast.parse(obj.source_code)
                    if isinstance(source_code, ast.Module):
                        source_code = source_code.body[0]
                    if not isinstance(source_code, ast.FunctionDef):
                        continue

                    args = self._get_args(source_code)
                    if args:
                        arg_types.update(args)
            if not recursive:
                break

        dependencies: list[SourceCode] = []
        for dep in chain(call_names, arg_types):
            if dep not in self.index:
                continue
            dependencies.extend(list(self.index[dep]))

        return [
            json.dumps(
                {
                    "object_name": x.object_name,
                    "file_path": x.file_path,
                    "source code": x.source_code[:3000],
                }
            )
            for x in dependencies
        ]

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

    @staticmethod
    def get_source_code_from_name(
        index: dict[str, set[str]], obj_name: str
    ) -> SourceCode | None:
        """
        Retrieves the source code of an object based on its name.

        Args:
            index (dict[str, set[str]]): A dictionary mapping object names to their definitions.
            obj_name (str): The name of the object for which to retrieve the source code.

        Returns:
            SourceCode | None: The source code of the specified object or None if the object is not found.
        """
        func = list(index[obj_name])
        if not func:
            return None

        if len(func) > 1:
            print("Found multiple elements. Please select the proper one:")
            for idx, item in enumerate(func):
                print(f"{idx:<4}:{item.location}...")
            index = int(input("Type index: "))

            object_def = func[index]
        else:
            object_def = func[0]

        return object_def


if __name__ == "__main__":
    indexer = NodeIndexer(".")
    print(indexer.index)
    obj_id = input("Pick an ID: ").strip()
    d = indexer.get_dependencies("make_docstrings", obj_id, recursive=True)
    print(d)
