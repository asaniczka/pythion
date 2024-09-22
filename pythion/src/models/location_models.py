import os

from pydantic import BaseModel, ConfigDict


class ObjectLocation(BaseModel):

    name: str
    file_path: str
    row: int

    @property
    def vscode_link(self):

        vscode_link = (
            f"vscode://file//{os.path.join(os.getcwd(),self.file_path)}:{self.row}"
        )
        display_text = f"{self.file_path}:{self.name}"

        return f"[link={vscode_link}]{display_text}[/link]"
