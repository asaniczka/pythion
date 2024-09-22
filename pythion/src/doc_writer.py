import ast
import os
from pathlib import Path

import pyperclip
from openai import OpenAI
from pydantic import BaseModel
from rich import print
from wrapworks import cwdtoenv

cwdtoenv()
from pythion import NodeIndexer
from pythion.src.models.core_models import SourceCode


class DocManager:
    """
    Generates docstrings for Python functions or classes by prompting the user for
    input. The function interacts with the user through the console to obtain the
    name of the target function or class and then attempts to create a docstring
    based on the existing source code and its dependencies. The resulting docstring
    is copied to the clipboard for easy pasting. If multiple definitions are found,
    the user is prompted to select the appropriate one. Errors during docstring
    creation are handled gracefully, providing feedback to the user.
    """

    def __init__(
        self,
        root_dir: str,
        folders_to_ignore: list[str] | None = None,
    ) -> None:

        self.root_dir: str = root_dir

        self.folders_to_ignore = [".venv", ".mypy_cache"]
        self.indexer = NodeIndexer(root_dir, folders_to_ignore=folders_to_ignore)
        if folders_to_ignore:
            self.folders_to_ignore += folders_to_ignore

    def build_doc_cache(self, use_all: bool = False):

        source_codes_to_queue = []
        for values in self.indexer.index.values():
            if use_all:
                source_codes_to_queue.extend(list(values))
            else:
                for v in values:
                    if v.has_docstring:
                        continue
                    source_codes_to_queue.append(v)

        print(len(source_codes_to_queue))

    def make_docstrings(self):
        """
        Prompts the user for a function or class name and generates a corresponding
        docstring. The generated docstring is then copied to the clipboard.

        This method runs in a loop, allowing the user to generate multiple
        docstrings consecutively until it is manually terminated. If no valid
        docstring is generated for the provided name, the user is prompted to
        enter a new name.

        Raises:
            KeyboardInterrupt: If the user chooses to exit the loop manually.
        """
        while True:
            func_name = input("Enter a function or class name: ")
            res = self._handle_doc_generation(func_name)
            if not res:
                continue
            doc_string, link = res
            pyperclip.copy(doc_string)
            print(f"Docstring generated for {link}")

    def _handle_doc_generation(
        self, function_name: str | None, object_def: SourceCode | None = None
    ):
        """"""

        source_code = object_def or self._get_source_code_from_name(function_name)
        if not source_code:
            print("No source code given!")
            return

        obj_name = source_code.object_name
        dependencies = self.indexer.get_dependencies(obj_name)

        try:
            doc_string = self._generate_doc(
                obj_name, source_code.source_code, dependencies
            )
        except Exception as e:
            print(e)
            print("Unable to generate doc string")
            return

        if not doc_string:
            print("Unable to generate doc string")

        doc_string = doc_string.strip(" '\"\n")
        doc_string = '"""\n' + doc_string + '\n"""'
        return doc_string, source_code.location

    def _get_source_code_from_name(self, obj_name: str) -> SourceCode | None:
        """"""

        func = list(self.indexer.index[obj_name])
        if not func:
            print("ERROR: No object found!")
            return

        if len(func) > 1:
            print("Found multiple elements. Please select the proper one:")
            for idx, item in enumerate(func):
                print(f"{idx:<4}:{item.location}...")
            index = int(input("Type index: "))

            object_def = func[index]
        else:
            object_def = func[0]

        return object_def

    def _generate_doc(self, func_name: str, func_code: str, dependencies: list[str]):
        """
        Generates a docstring for a specified Python function.

        This method uses the OpenAI API to create a structured docstring based on the function's name, code, and its dependencies. If no dependencies are provided, it initializes an empty list. The result is formatted in Google Style and tailored to a concise length.

        Args:
            func_name (str): The name of the function to document.
            func_code (str): The source code of the function.
            dependencies (list[str]): A list of dependencies related to the function. Defaults to an empty list.

        Returns:
            str: The generated docstring for the specified function.
        """

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
                    "content": "You are a Python docstring writer. Your task is to look at the main function, it's arguments, dependencies and write a docstring for the main function. Only share the the docstring for the main function.\n\nThe format I want is Google Style. Try to keep the length to less than 150 words. Format neatly",
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
    manager = DocManager(".")
    manager.build_doc_cache(use_all=True)
