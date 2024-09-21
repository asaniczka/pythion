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
        self.root_dir: str = root_dir
        self.only_new: bool = only_new
        self.folders_to_ignore = [".venv", ".mypy_cache"]
        self.indexer = NodeIndexer(root_dir, folders_to_ignore=folders_to_ignore)

        if folders_to_ignore:
            self.folders_to_ignore += folders_to_ignore

    def make_docstrings(self):

        files_to_parse = self._walk()

        for file in files_to_parse:
            self._handle_file(file)
            break

    def _walk(self):

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
                node.body.pop(0)

            func_code = ast.unparse(node)
            func_name = node.name
            dependencies = self.indexer.get_dependencies(func_name)

            doc_string = self._generate_doc(func_name, func_code, dependencies)
            doc_string = doc_string.strip().strip('"""').strip("'''")
            if not doc_string:
                continue
            node.body[0] = ast.Expr(ast.Constant(doc_string.strip()))
        file_path.write_text(ast.unparse(tree), encoding="utf-8")

    def _generate_doc(self, func_name: str, func_code: str, dependencies: list[str]):

        print(f"Generating docstrings for '{func_name}'")
        client = OpenAI()

        class Step(BaseModel):
            explanation: str
            output: str

        class DocString(BaseModel):
            steps: list[Step]
            main_func_name: str
            main_func_docstring: str

        completion = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a Python docstring writer. Your task is to look at the main function, it's arguments, dependencies and write a docstring for the main function. Only share the the docstring for the main function.\n\nThe format I want is Google Style.",
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
