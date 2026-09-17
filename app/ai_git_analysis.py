from app.git_manager import git_diff
# Imports our Git function so NetPilot can get the configuration changes.


from app.ollama_client import ask_ollama
# Imports the function that sends information to Ollama.


def analyze_git_changes():
    # Creates a function that asks AI to analyze Git changes.


    diff = git_diff()
    # Gets the current changes detected by Git.


    if not diff.strip():
        # Checks whether Git found any changes.

        print("No configuration changes detected.")
        # Tells us that there is nothing for AI to analyze.

        return
        # Stops the function because there is nothing to analyze.


    prompt = f"""
You are NetPilot, an AI network operations assistant.

Analyze the following network configuration change.

Explain:

1. What changed?
2. Which router appears to be affected?
3. Which interface appears to be affected?
4. What network technology is involved?
5. What could be the impact?
6. What is the risk level?
7. What would you recommend?

Do not make any configuration changes.

Git configuration change:

{diff}
"""
    # Creates the instructions that will be sent to Ollama.


    print("===== SENDING GIT CHANGES TO AI =====")
    # Shows that NetPilot is sending the information to AI.


    diagnosis = ask_ollama(prompt)
    # Sends the Git information to Ollama and receives the AI response.


    print()
    # Adds a blank line to make the output easier to read.


    print("===== NETPILOT AI GIT ANALYSIS =====")
    # Displays a heading for the AI response.


    print(diagnosis)
    # Displays the AI's analysis.


if __name__ == "__main__":
    # Checks whether this script is being run directly.


    analyze_git_changes()
    # Starts the AI analysis.