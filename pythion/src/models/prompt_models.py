"""
This module defines profiles for documentation and commits.

- DOC_PROFILES: Profiles for generating documentation.
- COMMIT_PROFILES: Guidelines for commit messages.
"""

DOC_PROFILES = {
    "fastapi": "Write in Markdown for Swagger documentation. This is NOT internal documentation.",
    "cli": "Write documentation for a CLI tool in the format of git docs. Include relevant examples",
}
COMMIT_PROFILES = {
    "no-version": "Ignore version bumps. This is done via a precommit hook. Also ignore any import removing. This is done automactially by autoflake. Not worthy of commit mention"
}
