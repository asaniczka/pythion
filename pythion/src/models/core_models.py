""""""

import os
from typing import Literal

from pydantic import BaseModel, ConfigDict

from pythion.src.file_handler import find_object_location
from pythion.src.models.location_models import ObjectLocation


class SourceCode(BaseModel):

    object_name: str
    object_type: Literal["function"] | Literal["class"]
    file_path: str
    source_code: str
    has_docstring: bool

    @property
    def location(self) -> str | None:
        """
        Returns the location of an object within a specified file.

        This property searches for the object defined by the name and type in the file located at
        file_path. If found, it returns a link to the object in the Visual Studio Code editor.

        Returns:
            str | None: A link to the object's location in Visual Studio Code if found,
            otherwise None.
        """
        loc = find_object_location(self.file_path, self.object_name, self.object_type)

        if not loc:
            return None
        return loc.vscode_link

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, SourceCode):
            return False
        return repr(self) == repr(value)

    def __hash__(self) -> int:
        return hash(repr(self))

    def __repr__(self) -> str:
        return f"{self.file_path}:{self.object_name}:{self.source_code}"


class DocCache(BaseModel):

    source: SourceCode
    doc_string: str | None
