"""
This module increments version numbers in files by updating the patch version. 

 Functions:
 
 - `increment_patch_version(version)`:
     - Increments the patch version of a specific semantic version string.
     - Returns the updated version.
 
 - `execute_bump_version(file_path, version_regex)`:
     - Updates the version number within the specified file based on a regex pattern.
     - Raises `SystemExit` if the current version cannot be found.
"""

import re
import sys


def increment_patch_version(version):
    """ "
    Increments the patch version of a given semantic version string.

    Args:
        version (str): A string representing the current version in the format 'major.minor.patch'.

    Returns:
        str: A string representing the new version with the incremented patch number.

    Example:
        >>> increment_patch_version('1.0.0')
        '1.0.1
    """
    major, minor, patch = map(int, version.split("."))
    patch += 1
    return f"{major}.{minor}.{patch}"


def execute_bump_version(file_path: str, version_regex: str) -> None:
    """
    Updates the version number in a specified file.

        This function searches for a version number in a given file and increments the patch version.

        Args:
            file_path (str): The path to the file containing the version number.
            version_regex (str): The regular expression used to find the version number in the file.

        Raises:
            SystemExit: If the version variable is not found in the file.
    """

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    pattern = re.compile(version_regex)
    match = re.search(pattern, content)
    if match:
        current_version = match.group(1)
        new_version = increment_patch_version(current_version)

        new_content = content.replace(current_version, new_version)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        print(f"Version incremented from {current_version} to {new_version}")
    else:
        print(
            "Version variable not found. Check your regex pattern. It needs to match the digits in the format of 1.2.3"
        )
        sys.exit(1)


if __name__ == "__main__":
    execute_bump_version("pyproject.toml", r'version = "(.*?)"')
