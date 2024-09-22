""""""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from pythion.src.models.location_models import ObjectLocation


def find_object_location(
    file_path: str, obj_name: str, obj_type: Literal["function", "class"]
) -> ObjectLocation:
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
