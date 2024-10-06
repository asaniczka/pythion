"""
This module provides Pydantic models for handling and representing the source code and documentation associated with Python functions and classes, facilitating discovery and management of code artifacts.
"""

from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from pythion.src.file_handler import find_object_location


class SourceCode(BaseModel):
    """
    Class representing the source code of a specific object.

    This class encapsulates details about a function or class, including its name, type, and
    source code, along with methods for locating it within a file.

    Attributes:
        object_name (str): The name of the object (function/class).
        object_type (Literal['function', 'class']): The type of the object.
        file_path (str): The path to the file containing the source code.
        source_code (str): The actual source code of the object.
        has_docstring (bool): Indicates if the object has an associated docstring.

    Methods:
        location: Returns the location of the object in a given file if found.
        __eq__: Compares two SourceCode instances for equality.
        __hash__: Returns the hash of the SourceCode instance.
        __repr__: Provides a string representation of the SourceCode instance.
    """

    object_id: str = Field(default_factory=lambda: str(uuid4()))
    object_name: str
    object_type: Literal["function"] | Literal["class"]
    file_path: str
    source_code: str
    has_docstring: bool

    @property
    def location(self) -> str | None:
        """
        Returns the link to the specified object in the source code if found.

        This property uses the file path, object name, and object type to determine the object's location by invoking the
        `find_object_location` function. If the object is located, the function returns its corresponding VSCode link; otherwise,
        it returns None.

        Returns:
            str or None: A string containing the VSCode link to the object, or None if the object is not found.
        """
        loc = find_object_location(self.file_path, self.object_name, self.object_type)

        if not loc:
            return None
        return loc.vscode_link

    def __eq__(self, value: object) -> bool:
        """
        Determines equality between the current instance and another object.

        This method checks if the given object is an instance of the SourceCode class. If it is, it compares the string representations of both objects to evaluate equality.

        Args:
            value (object): The object to compare against the current instance.

        Returns:
            bool: True if the objects are considered equal, otherwise False.
        """
        if not isinstance(value, SourceCode):
            return False
        return repr(self) == repr(value)

    def __hash__(self) -> int:
        """
        Returns a hash value for the object.

        This method computes the hash based on the string representation of the object using the built-in hash function.

        Returns:
            int: An integer hash value representing the object.
        """
        return hash(repr(self))

    def __repr__(self) -> str:
        """
        Returns a string representation of the object.

        This method provides a formatted string that includes the file path,
        object name, and the source code associated with the object.

        Returns:
            str: A formatted string in the form 'file_path:object_name:source_code'.
        """
        return f"{self.file_path}:{self.object_name}:{self.source_code[15:]}"


class SourceDoc(BaseModel):
    """
    Class representing a document source with an optional docstring.

    Attributes:
        source (SourceCode): The source code associated with the document.
        doc_string (str | None): An optional string that serves as a docstring for the source. It can be None if no docstring is provided.
    """

    model_config = ConfigDict(frozen=True)

    source: SourceCode
    doc_string: str | None


class ModuleDocSave(BaseModel):
    """
    Class for saving documentation to a specified path.

    Attributes:
        doc (str): The documentation content to be saved.
        path (str): The file path where the documentation will be saved.
    """

    doc: str
    path: str
