"""
This module provides functionality to generate, manage, and save Python docstrings.

Key Features:

- **DocManager Class**: Central class to handle documentation tasks.
- **Docstring Generation**: Automatic creation of docstrings using AI.
- **Cache Management**: Creates, stores, and retrieves docstrings from a local cache.
- **User Interaction**: Prompts users for input to refine docstring generation.
"""

# pylint: disable=wrong-import-position
import ast
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pyperclip  # type: ignore
from openai import OpenAI
from rich import print
from tqdm import tqdm  # type: ignore
from wrapworks import cwdtoenv

from pythion.src.models.doc_writer_models import (  # type: ignore
    ModuleDocString,
    ObjDocString,
)

cwdtoenv()
from pythion.src.indexer import NodeIndexer
from pythion.src.models.core_models import SourceCode, SourceDoc
from pythion.src.models.prompt_models import DOC_PROFILES


class DocManager:
    """
    Class to manage documentation generation for Python code files.

    This class initializes with a root directory and a list of folders to ignore. It builds a docstring cache for functions and classes by analyzing source code and allows for manual docstring copying and iterations.

    Methods include building doc caches based on specified criteria, iterating through cached docstrings, and generating new docstring content using AI assistance. The cache is saved in a designated local directory for later retrieval.

    Usage involves initializing the class with a valid directory, then invoking methods to build the cache or retrieve docstrings.
    """

    def __init__(
        self,
        root_dir: str,
        folders_to_ignore: list[str] | None = None,
        indexer: NodeIndexer | None = None,
    ) -> None:

        self.root_dir: str = root_dir
        self.cache_dir: str = ".pythion"
        self.doc_cache_file_name: str = "doc_cache.json"

        self.folders_to_ignore = [".venv", ".mypy_cache"]
        self.indexer = indexer or NodeIndexer(
            root_dir, folders_to_ignore=folders_to_ignore
        )
        if folders_to_ignore:
            self.folders_to_ignore += folders_to_ignore

        self._make_cache_dir()

    def _make_cache_dir(self):
        """
        Creates a cache directory if it does not exist.

        This method checks the path defined in the `cache_dir` attribute and creates the specified directory along with any necessary parent directories. If the directory already exists, no action is taken.

        Attributes:
            cache_dir (str): The directory path where the cache should be created.
        """

        path = Path(self.cache_dir)
        path.mkdir(parents=True, exist_ok=True)

    def build_doc_cache(self, use_all: bool = False, dry: bool = False):
        """
        Builds a cache of docstrings for objects in the indexer.

           This method gathers source code definitions that lack documentation and generates corresponding docstrings. It can filter files based on documented status and a set of ignore commands. The process can run in dry mode to preview changes without making any.

           Args:
               use_all (bool): If True, include all objects for docstring generation, regardless of existing documentation. Defaults to False.
               dry (bool): If True, perform a dry run that does not modify data; defaults to False.

           Prints:
               A message indicating the status of the docstring cache building process, including any errors encountered.
        """
        source_codes_to_queue = []
        ignore_commands = [
            "pythion:ignore",
            "pythion: ignore",
            "pythion :ignore",
            "pythion : ignore",
        ]
        for values in self.indexer.index.values():
            for v in values:
                if not use_all and v.has_docstring:
                    continue
                for cmd in ignore_commands:
                    if cmd in v.source_code[:150]:
                        break
                else:
                    source_codes_to_queue.append(v)

        if not source_codes_to_queue:
            print(
                "Couldn't find any objects that require docstring. Use `use_all` to generate docstrings for all objects"
            )

        if dry:
            print(
                f"{len(source_codes_to_queue)} candidates found for docstring generation. Retry to previous command without --dry to generate docstring cache."
            )
            return

        results: list[SourceDoc] = []
        with (
            ThreadPoolExecutor(max_workers=50) as tpe,
            tqdm(total=len(source_codes_to_queue)) as pbar,
        ):

            futures = [
                tpe.submit(self._handle_doc_generation, object_def=source, pbar=pbar)
                for source in source_codes_to_queue
            ]

            for future in as_completed(futures):
                try:
                    res = future.result()
                    if res:
                        results.append(res)
                except Exception as e:
                    print(f"Error in TPE: {type(e)} - {e}")
                    continue

        self._save_doc_cache(results)
        print(
            "Docstring cache built successfully. Use iter-docs to go through the docstrings"
        )

    def iter_docs(self):
        """
        Iterates through cached documentation strings, allowing the user to manage and save them.

        This function reads documentation strings from a cache file. If the cache file does not exist, it prompts the user to create one. For each cached documentation, it copies the string to the clipboard and prompts the user to decide
        what to do with it: paste and save, skip, or exit. If the user chooses to exit, any uncached items remain for later saving. The updated list of documentation strings is saved back to the cache file at the end of the operation.

        Raises:
            IOError: If there is an error reading from or writing to the cache file.
        """
        path = Path(self.cache_dir, self.doc_cache_file_name)
        if not path.exists():
            print(
                "No Docstring cache found. Please use build-doc-cache to build a cache file"
            )

        with open(path, "r", encoding="utf-8") as rf:
            content = json.load(rf)

        results = [SourceDoc.model_validate(x) for x in content]

        if not results:
            print(
                "No Docstring cache found. Please use build-doc-cache to build a cache file"
            )

        save_results: list[SourceDoc] = []
        for idx, result in enumerate(results):
            pyperclip.copy(result.doc_string)
            print(
                f"Copied to clipboard. Manually paste docstring @ {result.source.location}"
            )
            do_pop = input("Pop docstring from cache? [Y/N/EXIT]")

            if "exit" in do_pop.lower():
                save_results.extend(results[idx:])
                print("Exiting...")
                break
            if "n" in do_pop.lower():
                save_results.append(result)
                print("Saving current result for later...")
            else:
                continue

        self._save_doc_cache(save_results)

    def _save_doc_cache(self, save_results: list[SourceDoc]):
        """
        Saves a list of SourceDoc instances to a JSON file in the specified cache directory.

            Args:
                save_results (list[SourceDoc]): A list of SourceDoc instances to be saved.

            Raises:
                Exception: Raises an exception if writing to the file fails.

            This method constructs the full path to the cache file, opens it in write mode, and serializes the provided SourceDoc instances using their model_dump() method.
            The data is stored in a JSON format for later retrieval.
        """
        path = Path(self.cache_dir, self.doc_cache_file_name)
        with open(path, "w", encoding="utf-8") as wf:
            json.dump([x.model_dump() for x in save_results], wf)
            return

    def make_docstrings(
        self, custom_instruction: str | None = None, profile: str | None = None
    ):
        """
        Generates and copies Python docstrings for functions or classes based on user input.

        Args:
            custom_instruction (str | None): Optional instructions to customize the docstring generation.

        Usage:
            Run the script in the command line and when prompted, enter the name of the function or class. The generated docstring will be copied to the clipboard for easy pasting.
        """

        if profile:
            if profile not in DOC_PROFILES:
                print("ERROR: Commit profile not found")
                sys.exit(1)
            profile = DOC_PROFILES[profile]

        while True:
            func_name = input("Enter a function or class name: ")
            res = self._handle_doc_generation(
                func_name, custom_instruction=custom_instruction, profile=profile
            )
            if not res:
                continue
            pyperclip.copy(res.doc_string)
            print(
                f"Copied to clipboard. Manually paste docstring @ {res.source.location}"
            )

    def make_module_docstrings(self, custom_instruction: str | None = None):
        """
        Generate module docstrings based on user-provided module names.

            Args:
                custom_instruction (str | None): Optional instructions to customize the docstring generation process.

            Returns:
                None: Copies the generated docstring to clipboard and informs the user of the location.
        """

        while True:
            module_name = input("Enter a new module name: ")

            res = self._handle_module_doc_generation(
                module_name, custom_instruction=custom_instruction
            )

            if not res:
                continue

            doc_string, path = res
            pyperclip.copy(doc_string)
            print(f"Copied to clipboard. Manually paste docstring @ {path}")

    def _handle_module_doc_generation(
        self,
        module_name: str,
        custom_instruction: str | None = None,
    ):
        """
        Generates and retrieves the documentation for the specified module.

            Args:
                module_name (str): The name of the module to document.
                custom_instruction (str | None): Additional instructions for generating the docstring.

            Returns:
                tuple: A tuple containing the generated docstring and the link to the module in VS Code.

            Raises:
                SystemExit: If no modules are found or multiple modules are identified without user input.
        """

        similar_modules = [mod for mod in self.indexer.file_index if module_name in mod]

        if not similar_modules:
            print("Unable to locate module. Write using the full file path")
            return sys.exit(1)

        if len(similar_modules) > 1:
            print("Found multiple elements. Please select the proper one:")
            for idx, item in enumerate(similar_modules):
                print(f"{idx:<4}:{item}...")
            index = int(input("Type index: "))

            module_path = similar_modules[index]
        else:
            module_path = similar_modules[0]

        path = Path(module_path)
        source_code = ast.parse(path.read_text(encoding="utf-8"))

        if isinstance(source_code.body[0], ast.Expr) and isinstance(
            source_code.body[0].value, ast.Constant
        ):
            source_code.body.pop(0)

        try:
            res = self._generate_module_doc(
                path.name,
                ast.unparse(source_code),
                custom_instruction=custom_instruction,
            )
        except Exception as e:
            print(e)
            print("Unable to generate doc string")
            return None

        if not res:
            print("Unable to generate doc string")

        doc_string = res.strip(" '\"\n")
        doc_string = '"""\n' + doc_string + '\n"""'

        vs_link_path = (
            f"[link=vscode://file//{str(path.absolute())}:1]{path.name}[/link]"
        )

        return doc_string, vs_link_path

    def _handle_doc_generation(
        self,
        function_name: str | None = None,
        object_def: SourceCode | None = None,
        pbar: tqdm | None = None,
        custom_instruction: str | None = None,
        profile: str | None = None,
    ) -> SourceDoc | None:
        """"""

        if pbar:
            pbar.update(1)

        if not function_name and not object_def:
            raise ValueError("Please provide a function name or an object_def")

        source_code = object_def or NodeIndexer.get_source_code_from_name(
            self.indexer.index, function_name
        )
        if not source_code:
            print(
                "ERROR: Unable to locate object in the index. Double check the name you entered."
            )
            return None

        obj_name = source_code.object_name
        dependencies = self.indexer.get_dependencies(obj_name, source_code.object_id)

        try:
            doc_string = self._generate_doc(
                obj_name,
                source_code.source_code,
                dependencies,
                silence=bool(pbar),
                custom_instruction=custom_instruction,
                profile=profile,
            )
        except Exception as e:
            print(e)
            print("Unable to generate doc string")
            return None

        if not doc_string:
            print("Unable to generate doc string")

        doc_string = doc_string.strip(" '\"\n")
        doc_string = '"""\n' + doc_string + '\n"""'
        return SourceDoc(doc_string=doc_string, source=source_code)

    def _generate_doc(
        self,
        func_name: str,
        func_code: str,
        dependencies: list[str] | None,
        silence: bool = False,
        custom_instruction: str | None = None,
        profile: str | None = None,
    ):
        """
        Generate a docstring for the specified function.

        Args:
            func_name (str): The name of the function to generate a docstring for.
            func_code (str): The source code of the function.
            dependencies (list[str] | None): A list of dependencies used in the function. Defaults to None.
            silence (bool): If True, suppresses output messages. Defaults to False.
            custom_instruction (str | None): Any additional custom instructions for generating the docstring. Defaults to None.

        Returns:
            str | None: The generated docstring, or None if generation fails.
        """
        if not silence:
            print(f"Generating docstrings for '{func_name}'")
        client = OpenAI(timeout=30)
        if not dependencies:
            dependencies = []

        messages = [
            {
                "role": "system",
                "content": "You are a Python docstring writer. Your task is to look at the main object, it's arguments, dependencies and write a docstring for the main object. Only share the the docstring for the main object.\n\nThe format I want is Google Style. Format neatly with list items (if any). Keep documentation simple, minimal and don't repeat the obvious. Don't indent headings",
            },
            {"role": "user", "content": "Main Object Name: " + func_name},
            {"role": "user", "content": "Main Object source code: " + func_code},
            {
                "role": "user",
                "content": "Dependency Source code: " + "\n\n".join(dependencies),
            },
        ]
        if profile:
            messages.append(
                {
                    "role": "user",
                    "content": profile,
                }
            )
        if custom_instruction:
            messages.append(
                {
                    "role": "user",
                    "content": "Additional Instructions: " + custom_instruction,
                }
            )

        completion = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=messages,  # type:ignore
            response_format=ObjDocString,
        )

        ai_repsonse = completion.choices[0].message
        if not ai_repsonse.parsed:
            return None
        return ai_repsonse.parsed.main_object_docstring

    def _generate_module_doc(
        self,
        module_name: str,
        module_source_code: str,
        custom_instruction: str | None = None,
    ):
        """"""
        print(f"Generating docstrings for module '{module_name}'")
        client = OpenAI(timeout=30)

        messages = [
            {
                "role": "system",
                "content": "You are a Python module docstring writer. Your task is to look at the module source code and write a doc string to put at the top of the file.\n\nThe format I want is Google Style. Format neatly with list items (if any). Keep documentation simple and minimal. Keep sentences short and use bullet points. Max sentence length: 100 characters",
            },
            {"role": "user", "content": "Module Name: " + module_name},
            {"role": "user", "content": "Module source code: " + module_source_code},
        ]

        if custom_instruction:
            messages.append(
                {
                    "role": "user",
                    "content": "Additional Instructions: " + custom_instruction,
                }
            )

        completion = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=messages,  # type:ignore
            response_format=ModuleDocString,
        )

        ai_repsonse = completion.choices[0].message
        if not ai_repsonse.parsed:
            return None
        return ai_repsonse.parsed.module_docstring


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    manager = DocManager(".")
    manager.make_module_docstrings()
