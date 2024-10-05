"""
Module for generating and applying Git commit messages.

This module offers functionalities to:

- Retrieve staged changes in a Git repository.
- Generate a commit message using an AI model based on the retrieved git diff.
- Execute a commit with the generated message.

Functions:
- `generate_message(git_diff: str, custom_instruction: str | None)`: Generates a commit message using the provided git diff and optional custom instructions.
- `get_staged_changes()`: Retrieves the currently staged changes in the Git repository.
- `make_commit(commit_message)`: Executes the git commit command with the specified commit message.
- `handle_commit(custom_instructions: str | None)`: Main function for handling the commit process, integrating the above functionalities.

Usage:
- Run the module directly to perform the commit process with optional custom instructions.
"""

import subprocess

from openai import OpenAI
from pydantic import BaseModel

from pythion.src.models.prompt_models import COMMIT_PROFILES


def generate_message(
    git_diff: str,
    custom_instruction: str | None = None,
) -> str | None:
    """
    Generates a git commit message based on provided git diff and optional custom instructions.

        Args:
            git_diff (str): The git diff string containing changes.
            custom_instruction (str | None): Optional custom instructions for the commit message generation.

        Returns:
            str | None: The generated commit message or None if generation fails.

        Raises:
            Any relevant exceptions from the OpenAI client or message parsing.
    """
    client = OpenAI(timeout=180)

    class Step(BaseModel):
        """#pythion:ignore"""

        what_has_changed: str | None = None
        what_was_the_purpose_of_the_change: str | None = None

    class CommitMessage(BaseModel):
        """#pythion:ignore"""

        steps: list[Step]
        commit_message: str

    messages = [
        {
            "role": "system",
            "content": "You are a Git commit message writer. Examine the provided diff and write a git commit in Contextual Style. Prefix all commits with one of ['ADD','REMOVE','UPDATE','TEST',IMPROVE','CLEANUP','REFACTOR','OPTIMIZE'... or a similer verb].\n\n Commit style would be 'ACTION VERB: Describe commit in 1 line Max 50 characters.'",
        },
        {"role": "user", "content": "GIT DIFF: \n\n" + git_diff},
    ]
    if custom_instruction:
        messages.append(
            {
                "role": "user",
                "content": "Additional Instructions: " + custom_instruction,
            }
        )

    completion = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=messages,  # type:ignore
        response_format=CommitMessage,
    )

    ai_repsonse = completion.choices[0].message
    if not ai_repsonse.parsed:
        return None
    return ai_repsonse.parsed.commit_message


def get_staged_changes() -> str | None:
    """
    Retrieves the list of staged changes in the current Git repository.

        This function uses Git's command line interface to get the differences between the staged changes and the last commit.
        If there is an error during the subprocess execution, it prints an error message with the details.

        Returns:
            str: A string containing the staged changes.
    """
    try:
        staged_diff = subprocess.check_output(
            ["git", "diff", "--cached"], stderr=subprocess.STDOUT
        ).decode("utf-8")
        return staged_diff

    except subprocess.CalledProcessError as e:
        print(f"Error getting staged changes: {e.output.decode('utf-8')}")
        return None


def make_commit(commit_message):
    """
    Creates a Git commit with the provided commit message.

        Args:
            commit_message (str): The message to be included with the commit.

        Returns:
            int: The return code from the Git command indicating success or failure.

        Raises:
            subprocess.CalledProcessError: If the Git command fails.
    """
    try:
        good_commit = subprocess.check_call(
            ["git", "commit", ".", "-m", commit_message]
        )

    except subprocess.CalledProcessError as e:
        print(f"Error making commit: {e.output.decode('utf-8')}")


def handle_commit(custom_instruction: str | None = None, profile: str | None = None):
    """
    Handles the Git commit process by generating a commit message based on staged changes.

        Args:
            custom_instruction (str | None): An optional custom instruction to guide the commit message.
            profile (str | None): An optional profile to apply predefined custom instructions.

        Raises:
            RuntimeError: If no changes are staged for commit or if the provided profile is not found.
    """
    diff = get_staged_changes()

    if not diff:
        raise RuntimeError(
            "No Diff found. Make sure to put all changes into the staging area"
        )

    if custom_instruction and profile:
        print("You cannot provide a custom instruction when providing a profile")
        return

    if profile:
        if profile not in COMMIT_PROFILES:
            print("ERROR: Commit profile not found")
            return
        custom_instruction = COMMIT_PROFILES[profile]

    commit_message = generate_message(
        diff,
        custom_instruction,
    )
    print(commit_message)
    make_commit(commit_message)


if __name__ == "__main__":
    handle_commit()
