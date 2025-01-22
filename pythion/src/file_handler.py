"""
This module contains functions to handle file operations related to locating
classes and functions within specified Python files.
"""

from typing import Literal

from pythion.src.models.location_models import ObjectLocation


def find_object_location(
    file_path: str, obj_name: str, obj_type: Literal["function", "class"]
) -> ObjectLocation | None:
    """
    Finds the location of a specified function or class in a given file.

    Args:
        file_path (str): The path to the file to search in.
        obj_name (str): The name of the object (function or class) to find.
        obj_type (Literal['function', 'class']): The type of object to search for.

    Returns:
        ObjectLocation: An instance of ObjectLocation containing the name, file path,
        and line number where the object is located, or None if not found.

    Raises:
        TypeError: If obj_type is not 'function' or 'class'.
    """
    with open(file_path, "r", encoding="utf-8") as rf:

        match obj_type:
            case "function":
                item_to_find = "def " + obj_name
            case "class":
                item_to_find = "class " + obj_name
            case _:
                raise TypeError(f"Unknwon type {type}")

        for idx, line in enumerate(rf.readlines(), 1):
            if item_to_find in line:
                return ObjectLocation(name=obj_name, file_path=file_path, row=idx)
        return None
