"""
Main indexer of pythion
"""

import ast
from collections import defaultdict
from copy import deepcopy
import os
from pathlib import Path
from rich import print
from itertools import chain


class CallFinder(ast.NodeVisitor):
    """This be docstring"""

    def __init__(self, call_names: set[str]) -> None:
        self.calls = set()
        self.call_names = call_names

    def visit_FunctionDef(self, node: ast.FunctionDef):
        "visit_FunctionDef doc"
        print("Visited", node.name)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        "visit_Call doc"
        print("Visited", node.name)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name):
            self.call_names.add(node.func.id)


class NodeTransformer(ast.NodeTransformer):

    def __init__(self, index: dict[str, set[str]]) -> None:
        self.index: dict[str, set[str]] = index

    def clean_function(self, node: ast.FunctionDef) -> ast.FunctionDef:
        """
        Modify the functions in a given Python file to include docstrings.
        """

        if not isinstance(node, ast.FunctionDef):
            return node

        # remove current docstring
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
        ):
            node.body.pop(0)

        return node

    def clean_class(self, node: ast.ClassDef) -> ast.ClassDef:
        """Doc clean class"""

        if not isinstance(node, ast.ClassDef):
            return node

        # remove current docstring
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
        """Doc visit functionDef"""
        node = self.clean_function(node)
        self.generic_visit(node)

        node_in_text = ast.unparse(node)
        self.index[node.name].add(node_in_text)
        return node

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.ClassDef:
        """Doc visit ClassDef"""
        node = self.clean_class(node)
        self.generic_visit(node)

        node_in_text = ast.unparse(node)
        self.index[node.name].add(node_in_text)
        return node


class NodeIndexer:

    def __init__(
        self, root_dir: str, folders_to_ignore: list[str] | None = None
    ) -> None:
        self.root_dir = root_dir
        self.index: dict[str, set[str]] = defaultdict(set)
        self.folders_to_ignore = [".venv", ".mypy_cache"]

        if folders_to_ignore:
            self.folders_to_ignore.extend(folders_to_ignore)

        self.build_index()
        self.warn()

    def build_index(self):
        """
        Modify the functions in a given Python file to include docstrings.
        """
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
                    print(file_path)
                    tree = ast.parse(file_path.read_text(encoding="utf-8"))

                    for node in ast.walk(tree):
                        node = transformer.visit(node)

        self._remove_common_syntax()

    def _remove_common_syntax(self):

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

        call_names = set()
        call_finder = CallFinder(call_names)
        call_finder.visit(node)

        return list(call_names)

    def _get_args(self, node: ast.FunctionDef) -> list[str] | None:

        if not isinstance(node, ast.FunctionDef):
            return None

        arg_types = set()
        for arg in node.args.args:
            if isinstance(arg.annotation, ast.Name):
                arg_types.add(arg.annotation.id)

        return list(arg_types)

    def get_dependencies(self, func_name: str):

        func = self.index.get(func_name)
        if not func:
            raise ModuleNotFoundError()
        node = ast.parse(list(func)[0])
        if isinstance(node, ast.Module):
            node = node.body[0]

        call_names = self._get_call_tree(node)
        arg_types = self._get_args(node)

        dependencies = []

        for dep in chain(call_names, arg_types):
            if dep in self.index:
                dependencies.extend(list(self.index[dep]))

        dependencies = [x[:3000] for x in dependencies]
        return dependencies

    def warn(self):

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
