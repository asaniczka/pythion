# pylint: disable=wrong-import-position
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pyperclip  # type: ignore
from openai import OpenAI
from pydantic import BaseModel
from rich import print
from tqdm import tqdm  # type: ignore
from wrapworks import cwdtoenv  # type: ignore

cwdtoenv()
from pythion import NodeIndexer
from pythion.src.models.core_models import SourceCode, SourceDoc


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

    def build_doc_cache(self, use_all: bool = False):
        """
        Builds a cache of docstrings from source code objects.

        This function processes the source code objects indexed by the instance's indexer. If `use_all` is set to True, it queues all source codes; otherwise, it queues only those without existing docstrings. It utilizes a thread pool to handle docstring generation concurrently and updates a progress bar. The results are saved in a specified cache directory in JSON format.

        Args:
            use_all (bool): Indicates whether to include all source codes (default is False).

        Raises:
            Any: Captured exceptions during docstring generation are printed, but not raised.

        Returns:
            None: The function saves the results to a file rather than returning them.
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
                    if cmd in v.source_code[:30]:
                        break
                else:
                    source_codes_to_queue.append(v)

        if not source_codes_to_queue:
            print(
                "Couldn't find any objects that require docstring. Use `use_all` to generate docstrings for all objects"
            )
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

    def make_docstrings(self):
        """
        Generates docstrings for given functions or classes interactively.

        Prompts the user to input a function or class name, processes the request, and generates a corresponding docstring. The generated docstring is then copied to the clipboard for ease of use, and a success message is displayed. The function continues to request valid input until a proper name is provided that results in a generated documentation.
        """
        while True:
            func_name = input("Enter a function or class name: ")
            res = self._handle_doc_generation(func_name)
            if not res:
                continue
            pyperclip.copy(res.doc_string)
            print(
                f"Copied to clipboard. Manually paste docstring @ {res.source.location}"
            )

    def _handle_doc_generation(
        self,
        function_name: str | None = None,
        object_def: SourceCode | None = None,
        pbar: tqdm | None = None,
    ) -> SourceDoc | None:
        """
        Generates a documentation string for a specified function or object.

        Args:
            function_name (str | None): The name of the function to document. Default is None.
            object_def (SourceCode | None): An optional SourceCode object containing the definition.
            pbar (tqdm | None): An optional progress bar for tracking status during generation.

        Returns:
            SourceDoc | None: A SourceDoc object containing the generated doc string and source code,
                               or None if generation fails due to errors or missing source code.

        Raises:
            Exception: Prints error message if documentation generation fails.
        """

        if pbar:
            pbar.update(1)

        if not function_name or object_def:
            raise ValueError("Please provide a function name or an object_def")

        source_code = object_def or self._get_source_code_from_name(function_name)
        if not source_code:
            print(
                "ERROR: Unable to locate object in the index. Double check the name you entered."
            )
            return None

        obj_name = source_code.object_name
        dependencies = self.indexer.get_dependencies(obj_name)

        try:
            doc_string = self._generate_doc(
                obj_name, source_code.source_code, dependencies, silence=bool(pbar)
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

    def _get_source_code_from_name(self, obj_name: str) -> SourceCode | None:
        """
        Retrieves the source code associated with a specified object name from the index.

        Args:
            obj_name (str): The name of the object to retrieve the source code for.

        Returns:
            SourceCode | None: The source code of the object if found, or None if no object matches the name.

        Raises:
            ValueError: If multiple objects are found, prompts the user to specify which object to select.
        """

        func = list(self.indexer.index[obj_name])
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

    def _generate_doc(
        self,
        func_name: str,
        func_code: str,
        dependencies: list[str] | None,
        silence: bool = False,
    ):
        """
        Generates docstrings for Python functions using the OpenAI model.

        Args:
            func_name (str): The name of the function for which to generate the docstring.
            func_code (str): The source code of the function as a string.
            dependencies (list[str]): A list of dependencies required for the function.
            silence (bool, optional): If True, suppresses the output. Defaults to False.

        Returns:
            str: The generated docstring for the specified function.
        """
        if not silence:
            print(f"Generating docstrings for '{func_name}'")
        client = OpenAI(timeout=30)
        if not dependencies:
            dependencies = []

        class Step(BaseModel):
            """#pythion:ignore"""

            why_does_this_object_exist: str | None = None
            what_purpose_does_it_serve: str | None = None

        class DocString(BaseModel):
            """#pythion:ignore"""

            steps: list[Step]
            main_object_name: str
            main_object_docstring: str

        completion = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a Python docstring writer. Your task is to look at the main object, it's arguments, dependencies and write a docstring for the main object. Only share the the docstring for the main object.\n\nThe format I want is Google Style. Try to keep the length to less than 150 words. Format neatly",
                },
                {"role": "user", "content": "Main Object Name: " + func_name},
                {"role": "user", "content": "Main Object source code: " + func_code},
                {
                    "role": "user",
                    "content": "Dependency Source code: " + "\n\n".join(dependencies),
                },
            ],
            response_format=DocString,
        )
        ai_repsonse = completion.choices[0].message
        if not ai_repsonse.parsed:
            return None
        return ai_repsonse.parsed.main_object_docstring


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    manager = DocManager(".")
    manager.build_doc_cache(use_all=False)
    manager.iter_docs()
