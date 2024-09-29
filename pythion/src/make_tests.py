""""""

# pylint: disable=wrong-import-position
import sys
from typing import Literal

import pyperclip  # type: ignore
from openai import OpenAI
from rich import print
from wrapworks import cwdtoenv

cwdtoenv()

from pythion.src.indexer import NodeIndexer
from pythion.src.models.core_models import SourceCode
from pythion.src.models.test_maker_models import CombinedTests


class TestManager:
    """"""

    def __init__(
        self,
        root_dir: str,
        folders_to_ignore: list[str] | None = None,
        indexer: NodeIndexer | None = None,
    ) -> None:

        self.root_dir: str = root_dir
        self.folders_to_ignore = [".venv", ".mypy_cache"]
        self.indexer = indexer or NodeIndexer(
            root_dir, folders_to_ignore=folders_to_ignore
        )
        if folders_to_ignore:
            self.folders_to_ignore += folders_to_ignore

    def make_tests(
        self,
        style: Literal["pytest", "unittest"] = "pytest",
        test_type: Literal["unit", "integration"] = "unit",
        custom_instruction: str | None = None,
    ):
        """"""
        func_name = input("Enter a function or class name: ")
        tests = self._handle_test_generation(
            func_name, test_type, style, custom_instruction=custom_instruction
        )
        if not tests:
            print("Not tests generated")
            sys.exit(1)

        pyperclip.copy(tests.all_test_cases_combined_to_a_single_file)
        print("Copied to clipboard!")
        print(tests)

    def _handle_test_generation(
        self,
        function_name: str,
        test_type: Literal["unit", "intergration"],
        style: Literal["pytest", "unittest"],
        custom_instruction: str | None = None,
    ) -> CombinedTests | None:
        """"""

        source_code = NodeIndexer.get_source_code_from_name(
            self.indexer.index, function_name
        )
        if not source_code:
            print(
                "ERROR: Unable to locate object in the index. Double check the name you entered."
            )
            sys.exit(1)

        obj_name = source_code.object_name
        dependencies = self.indexer.get_dependencies(
            obj_name, source_code.object_id, recursive=True
        )

        try:
            tests = self._generate_test(
                source_code,
                dependencies,
                custom_instruction=custom_instruction,
                test_type=test_type,
                style=style,
            )
        except Exception as e:
            print(e)
            print("Unable to generate doc string")
            sys.exit(1)

        return tests

    def _generate_test(
        self,
        source_code: SourceCode,
        dependencies: list[str] | None,
        test_type: Literal["unit", "intergration"],
        style: Literal["pytest", "unittest"],
        custom_instruction: str | None = None,
    ) -> CombinedTests | None:

        print(f"Generating tests for '{source_code.object_name}'")
        client = OpenAI(timeout=30)
        if not dependencies:
            dependencies = []

        match test_type:
            case "unit":
                messages = [
                    {
                        "role": "system",
                        "content": f"You are a python test writer. Write unittests tests with python {style} package. All test cases whether it be functions or classes needs to contain google style docstrings. Write isolated tests only for the Main Object. Do not write tests for the dependencies. They are for reference only",
                    }
                ]
            case "intergration":
                messages = [
                    {
                        "role": "system",
                        "content": f"You are a python test writer. Write intergration tests with python {style} package. All test cases whether it be functions or classes needs to contain google style docstrings. Write full intergration tests with each test starting on the Main Object entry point. Mock any required external calls, but do not mock or patch the actual dependency unless it makes a external call to a DB or a HTTP request",
                    },
                ]
            case _:
                raise TypeError(f"Unknown test type {test_type}")

        messages.extend(
            [
                {
                    "role": "user",
                    "content": "Main Object: \n\n" + source_code.model_dump_json(),
                },
                {
                    "role": "user",
                    "content": "Dependency Source code: \n\n"
                    + "\n\n".join(dependencies),
                },
            ]
        )

        if custom_instruction:
            messages.append(
                {
                    "role": "user",
                    "content": "Additional Instructions: " + custom_instruction,
                }
            )

        completion = client.beta.chat.completions.parse(
            model="gpt-4o-2024-08-06",
            messages=messages,  # type:ignore
            response_format=CombinedTests,
        )

        ai_repsonse = completion.choices[0].message
        if not ai_repsonse.parsed:
            return None
        return ai_repsonse.parsed


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    manager = TestManager(".")
    manager.make_tests()
