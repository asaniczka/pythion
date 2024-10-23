"""
This module defines profiles for documentation and commits.

- DOC_PROFILES: Profiles for generating documentation.
- COMMIT_PROFILES: Guidelines for commit messages.
"""

DOC_PROFILES = {
    "fastapi": "Write in Markdown for Swagger documentation. This is NOT internal documentation.Start with a H1 of the human readable function name followed by a 1 line description. THen describe the arguments, results, and errors. We're using fastAPI",
    "cli": "Write documentation for a CLI tool in the format of git docs. Include relevant examples",
}
COMMIT_PROFILES = {
    "no-version": "Ignore version bumps. This is done via a precommit hook. Also ignore any import removing. This is done automactially by autoflake. Not worthy of commit mention"
}
