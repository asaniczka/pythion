import subprocess

import pyperclip
from openai import OpenAI
from pydantic import BaseModel


def generate_message(
    git_diff: str,
    custom_instruction: str | None = None,
):
    """"""
    client = OpenAI(timeout=30)

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
            "content": "You are a Git commit message writer. Examine the provided diff and write a git commit in Contextual Style. Prefix all commits with one of ['ADD','REMOVE','UPDATE','TEST',IMPROVE','CLEANUP','REFACTOR','OPTIMIZE'... or a similer verb].\n\n Commit style would be 'ACTION VERB: Describe commit in 1 line.",
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


def get_staged_changes():
    try:
        staged_diff = subprocess.check_output(
            ["git", "diff", "--cached"], stderr=subprocess.STDOUT
        ).decode("utf-8")
        return staged_diff

    except subprocess.CalledProcessError as e:
        print(f"Error getting staged changes: {e.output.decode('utf-8')}")


def make_commit(commit_message):
    try:
        staged_diff = subprocess.check_call(
            ["git", "commit", ".", "-m", commit_message]
        )
        return staged_diff

    except subprocess.CalledProcessError as e:
        print(f"Error making commit: {e.output.decode('utf-8')}")


def handle_commit(custom_instructions: str | None = None):

    diff = get_staged_changes()

    if not diff:
        raise RuntimeError(
            "No Diff found. Make sure to put all changes into the staging area"
        )

    commit_message = generate_message(
        diff,
        custom_instructions,
    )
    print(commit_message)
    make_commit(commit_message)


if __name__ == "__main__":
    handle_commit()
