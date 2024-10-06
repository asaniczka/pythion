"""
Defines Pydantic models for module and object documentation strings.
"""

# MODULE DOC CONFIG
from pydantic import BaseModel


class ModuleStep(BaseModel):
    """#pythion:ignore"""

    why_does_this_module_exist: str | None = None
    what_purpose_does_it_serve: str | None = None


class ModuleDocString(BaseModel):
    """#pythion:ignore"""

    steps: list[ModuleStep]
    module_name: str
    module_docstring: str


# OBJECT DOC CONFIG
class ObjStep(BaseModel):
    """#pythion:ignore"""

    why_does_this_object_exist: str | None = None
    what_purpose_does_it_serve: str | None = None


class ObjDocString(BaseModel):
    """#pythion:ignore"""

    steps: list[ObjStep]
    main_object_name: str
    main_object_docstring: str
