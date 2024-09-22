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
from wrapworks import cwdtoenv

cwdtoenv()

from pythion.src.file_handler import find_object_location
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
        self.calls = set()
        self.call_names = call_names

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """"""
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        """"""
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        """"""
        if isinstance(node.func, ast.Name):
            self.call_names.add(node.func.id)


class NodeTransformer(ast.NodeTransformer):
    """"""

    def __init__(self, index: dict[str, set[SourceCode]], current_path: str) -> None:
        """"""
        self.index: dict[str, set[SourceCode]] = index
        self.current_path: str = current_path

    def clean_function(self, node: ast.FunctionDef) -> tuple[ast.FunctionDef, bool]:
        """"""
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
        """"""

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
                stmt = self.clean_function(stmt)
            if isinstance(stmt, ast.ClassDef):
                stmt = self.clean_class(stmt)

        return node, has_docstring

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        """
        Visits a function definition node in an Abstract Syntax Tree (AST).

        Args:
            node (ast.FunctionDef): The function definition node to visit.

        Returns:
            ast.FunctionDef: The processed function definition node after cleaning and visiting.

        This function cleans the input node, performs a generic visit for further processing,
        adds details of the function to an index, and finally returns the processed node.
        """
        node, has_docstring = self.clean_function(deepcopy(node))
        self.generic_visit(node)
        self.index[node.name].add(
            SourceCode(
                object_name=node.name,
                object_type="function",
                file_path=self.current_path,
                source_code=ast.unparse(node),
                has_docstring=has_docstring,
            )
        )
        return node

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.ClassDef:
        """"""
        node, has_docstring = self.clean_class(deepcopy(node))
        self.generic_visit(node)
        self.index[node.name].add(
            SourceCode(
                object_name=node.name,
                object_type="class",
                file_path=self.current_path,
                source_code=ast.unparse(node),
                has_docstring=has_docstring,
            )
        )
        return node


class NodeIndexer:
    """"""

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
        """"""
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
        """"""
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
        """"""
        call_names = set()
        call_finder = CallFinder(call_names)
        call_finder.visit(node)
        return list(call_names)

    def _get_args(self, node: ast.FunctionDef) -> list[str] | None:
        """"""
        if not isinstance(node, ast.FunctionDef):
            return None
        arg_types = set()
        for arg in node.args.args:
            if isinstance(arg.annotation, ast.Name):
                arg_types.add(arg.annotation.id)
        return list(arg_types)

    def get_dependencies(self, func_name: str) -> list[str] | None:
        """"""
        func = self.index.get(func_name)
        if not func:
            return None
        node = ast.parse(list(func)[0].source_code)
        if isinstance(node, ast.Module):
            node = node.body[0]
        call_names = self._get_call_tree(node)
        arg_types = self._get_args(node)
        dependencies: list[SourceCode] = []
        for dep in chain(call_names, arg_types or []):
            if dep in self.index:
                dependencies.extend(list(self.index[dep]))
        dependencies = [x.source_code[:3000] for x in dependencies]
        return dependencies

    def warn(self):
        """"""
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
