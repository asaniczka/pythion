"""
This module contains the ObjectLocation class, which represents the location of a file along with a specific row number. It allows users to easily create links for fast access to specific points in files within Visual Studio Code.
"""

import os

from pydantic import BaseModel


class ObjectLocation(BaseModel):
    """
    Representation of a file location associated with a specific row.

    Attributes:
        name (str): The name of the object within the file.
        file_path (str): The relative path to the file.
        row (int): The specific row number in the file.

    Methods:
        vscode_link: Generates a formatted link to open the file in Visual Studio Code at the specified row.

    Example:
        object_location = ObjectLocation(name='ExampleClass', file_path='src/example.py', row=10)
        print(object_location.vscode_link)  # Output: link to vscode at row 10.
    """

    name: str
    file_path: str
    row: int

    @property
    def vscode_link(self):
        """
        Generates a link to a specific file in Visual Studio Code.

        This property constructs a vscode link using the current working directory and the specified file path.
        It includes the line number where the link points, formatted as '[link=<vscode_link>]<display_text>[/link]'.

        Returns:
            str: A formatted string that contains the markdown link to the file in VSCode, displaying the file name and line number.
        """
        vscode_link = (
            f"vscode://file//{os.path.join(os.getcwd(),self.file_path)}:{self.row}"
        )
        display_text = f"{self.file_path}:{self.name}"

        return f"[link={vscode_link}]{display_text}[/link]"
