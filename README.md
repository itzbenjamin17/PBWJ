🤖 AI Code-to-Trello Board Generator
This script uses Google's Gemini AI to automatically scan a software project (either a local directory or a remote GitHub repository) and generate a Trello board populated with actionable tasks.

It's designed to bootstrap your project management by creating initial cards for features, bugs, refactoring, and testing, based directly on your codebase.

🚀 How It Works
The script follows this logic:

Input: Takes either a GitHub URL or a local file path.

Scan:

GitHub: Clones the repo into a temporary folder.

Local: Scans the specified directory.

It reads the file structure and the contents of each file (ignoring .git, node_modules, etc.).

Check Trello: It checks your Trello account for a board that already matches the project's name.

Call Gemini AI:

If Board Exists (Update): It fetches all existing cards from that board and sends them along with the codebase to Gemini, asking for an "update" (e.g., add new tasks, identify completed ones).

If No Board Exists (Create): It sends only the codebase to Gemini, asking it to generate a brand new project board from scratch.

Build Board: The script parses the JSON response from Gemini and uses the Trello API to create the board, lists, and cards.

✨ Features
Dual Mode: Analyzes code from a local directory or a remote GitHub repository.

AI-Powered: Uses the Gemini AI to generate intelligent, context-aware tasks.

Smart Board-Matching: Automatically finds existing boards by name to avoid creating duplicates.

Contextual Updates: Provides existing card data to the AI when in "update" mode for smarter suggestions.

Configurable: Easily ignore specific files or directories via the ignore_dirs and ignore_files sets.

🛠️ Setup & Installation
1. Install Dependencies
You need Python 3 and pip. Install the required libraries:

Bash

pip install -r requirements.txt
2. Get API Keys
You need API keys from both Google and Trello.

Google Gemini API Key:

Go to Google AI Studio.

Create a new API key.

Trello API Key & Token:

Go to https://trello.com/app-key/.

This page will show your API Key.

You must also generate a Token. Click the "Token" link on that page and approve the permissions to generate one.

3. Create .env File
In the same directory as your Python script, create a file named .env and paste your keys into it:

Code snippet

GEMINI_API_KEY="YOUR_GEMINI_API_KEY_HERE"
TRELLO_API_KEY="YOUR_TRELLO_API_KEY_HERE"
TRELLO_API_TOKEN="YOUR_TRELLO_API_TOKEN_HERE"
🏃‍♀️ How to Run
You can run the script in one of two ways.

Option 1: Analyze a Local Directory
By default, the script scans the hard-coded directory in the scan_codebase function.

We recommend changing this to "." to scan the current directory.

Python

# In function scan_codebase:
def scan_codebase(root_dir=".", max_file_size=10000):
    # ...
After that, simply run the script:

Bash

python your_script_name.py
Option 2: Analyze a GitHub Repository
To analyze a remote GitHub repo, you must modify the if __name__ == "__main__": block at the bottom of the file to pass the github_url to the main function.

Python

if __name__ == "__main__":
    TRELLO_API_KEY = os.getenv("TRELLO_API_KEY", "")
    TRELLO_API_TOKEN = os.getenv("TRELLO_API_TOKEN", "")

    # --- Example for GitHub ---
    repo_url = "https://github.com/user/your-cool-repo.git"
    main(TRELLO_API_KEY, TRELLO_API_TOKEN, status=sys.stdout, github_url=repo_url)
    
    # --- Example for Local ---
    # main(TRELLO_API_KEY, TRELLO_API_TOKEN, status=sys.stdout, github_url=None)
Now, run the script. It will clone the repo, analyze it, and then delete the temporary files.

Bash

python your_script_name.py

⚠️ Known Issues / Future Improvements

TODO: A better implementation would be to ask Gemini for a plan of action (e.g., {"create": [...], "update": [...], "archive": [...]}) and then implement update_card and archive_card functions using the Trello API's PUT requests.

TODO: Implement a GitHub Action where the script is run on every pull request / push to master. Essentially contributing to CI/CD pipelining.