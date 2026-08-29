import subprocess
# Lets Python run commands such as Git commands.


def run_git(command):
    # Runs a Git command.

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
    )
    # Runs the command and captures what Git sends back.


    return result.stdout
    # Sends the Git output back to our program.


def git_status():
    # Gets the current status of the Git repository.

    return run_git(["git", "status", "--short"])
    # Runs: git status --short


def git_diff():
    # Gets the changes detected by Git.

    return run_git(["git", "diff"])
    # Runs: git diff


if __name__ == "__main__":
    # Runs this section when we execute this file directly.

    print("===== NETPILOT GIT STATUS =====")
    # Displays a heading.

    print(git_status())
    # Displays the Git status.


    print("===== NETPILOT GIT DIFF =====")
    # Displays another heading.

    print(git_diff())
    # Displays the Git configuration changes.