import re
import sys


def increment_patch_version(version):
    """str: The incremented version number in the same format."""
    major, minor, patch = map(int, version.split("."))
    patch += 1
    return f"{major}.{minor}.{patch}"


def execute_bump_version(file_path: str, version_regex: str) -> None:
    """"""

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    match = re.search(version_regex, content)
    if match:
        current_version = match.group(1)
        new_version = increment_patch_version(current_version)

        # Replace the old version with the new version
        new_content = content.replace(current_version, new_version)

        # Write the new version back to the file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        print(f"Version incremented from {current_version} to {new_version}")
    else:
        print("Version variable not found.")
        sys.exit(1)


if __name__ == "__main__":
    execute_bump_version("pyproject.toml", r'version = "(.*?)"')
