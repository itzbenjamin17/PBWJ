import os
import requests
import json
import sys
from google.genai import Client
from dotenv import load_dotenv


load_dotenv()


# Load API keys from environment variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
TRELLO_API_KEY = os.getenv("TRELLO_API_KEY", "")
TRELLO_API_TOKEN = os.getenv("TRELLO_API_TOKEN", "")

if not GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY is not set.")
    sys.exit(1)
elif not TRELLO_API_KEY:
    print("Error: TRELLO_API_KEY is not set.")
    sys.exit(1)
elif not TRELLO_API_TOKEN:
    print("Error: TRELLO_API_TOKEN is not set.")
    sys.exit(1)


# --- 1. Trello API Functions ---


TRELLO_API_URL = "https://api.trello.com/1/"
trello_auth = {'key': TRELLO_API_KEY, 'token': TRELLO_API_TOKEN}
board_name = "Poker Backend"


def create_board():
    print(f"Creating Trello board: {board_name}...")
    url = f"{TRELLO_API_URL}boards/"
    params = {'name': board_name, 'defaultLists': 'false', **trello_auth}
    response = requests.post(url, params=params)
    response.raise_for_status()
    print(f"✅ Board created! URL: {response.json()['shortUrl']}")
    return response.json()['id']


def create_list(board_id, list_name):
    print(f"  Creating list: {list_name}...")
    url = f"{TRELLO_API_URL}lists/"
    params = {'name': list_name, 'idBoard': board_id, **trello_auth}
    response = requests.post(url, params=params)
    response.raise_for_status()
    return response.json()['id']


def create_card(list_id, card_name, card_desc):
    print(f"    Creating card: {card_name}...")
    url = f"{TRELLO_API_URL}cards/"
    params = {'name': card_name, 'desc': card_desc,
              'idList': list_id, **trello_auth}
    response = requests.post(url, params=params)
    response.raise_for_status()
    return response.json()['id']


# --- 2. Code Scanning Function ---


def scan_codebase(root_dir="C:\\Users\\benja\\IdeaProjects\\Poker-Backend", max_file_size=10000):
    """Scans the codebase and returns a string with the file tree and key file contents."""
    file_tree = []
    file_contents = []
    # Add files/dirs to ignore
    ignore_dirs = {'.git', '.vscode', '__pycache__',
                   'node_modules', '.github', "venv", "Old Game Logic", "target", "public"}
    ignore_files = {'package-lock.json', '.env'}

    for root, dirs, files in os.walk(root_dir):
        # Filter out ignored directories
        dirs[:] = [d for d in dirs if d not in ignore_dirs]

        rel_path = os.path.relpath(root, root_dir)
        if rel_path == ".":
            level = 0
        else:
            level = rel_path.count(os.sep) + 1

        indent = "  " * level

        if level > 0:
            file_tree.append(f"{indent}📁 {os.path.basename(root)}/")

        for f in files:
            if f in ignore_files:
                continue

            file_tree.append(f"{indent}  📄 {f}")

            try:
                file_path = os.path.join(root, f)
                if os.path.getsize(file_path) > max_file_size:
                    file_contents.append(
                        f"--- Content of {file_path} (truncated) ---\nFile is too large, skipping content.\n")
                    continue

                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    file_contents.append(
                        f"--- Content of {file_path} ---\n{content}\n")
            except Exception as e:
                file_contents.append(
                    f"--- Could not read {file_path}: {e} ---\n")

    return "\n".join(file_tree), "\n".join(file_contents)


# --- 3. Gemini "Magic" JSON Function ---


def get_trello_json_from_gemini(code_tree, code_contents):
    print("Asking Gemini to design the Trello board...")

    if not GEMINI_API_KEY or GEMINI_API_KEY.startswith("PASTE_"):
        print("Error: GEMINI_API_KEY is not set or still contains placeholder.")
        sys.exit(1)

    # Initialize the new Google Gen AI client
    client = Client(api_key=GEMINI_API_KEY)

    prompt = f"""
    You are an intelligent code analysis assistant that helps developers manage their projects by analyzing codebases and generating actionable Trello cards. Your job is to
    analyze a codebase, infer the development roadmap using the provided codebase (excluding trello_script.py) and automatically generate structured Trello card recommendations.
    
    Based on the file tree and file contents below, generate a JSON object
    for a Trello board.


    The JSON must follow this exact schema:
    {{
      "boardName": "Board Name",
      "lists": [
        {{
          "name": "List Name (e.g., 'main.py', 'helper.py', 'extra.py')",
          "cards": [
            {{ 
              "name": "Name for improvement or feature", 
              "description": "One-sentence summary of the proposed improvement or feature."
            }}
          ]
        }}
      ]
    }}


    Rules:
    1.  The "description" for each card should be a concise summary.
    2.  Label suggestions should be in categories like "Bugs", "Features", "Refactor", "Testing".
    3.  Return *ONLY* the raw JSON object and nothing else. Do not wrap it in ``````.

    
    --- FILE TREE ---
    {code_tree}


    --- FILE CONTENTS ---
    {code_contents}
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )

        # Clean the response to ensure it's valid JSON
        response_text = response.text if response.text else ""
        cleaned_json = response_text.strip().replace(
            "```json", "").replace("```", "").strip()
        return json.loads(cleaned_json)
    except Exception as e:
        print(f"Error parsing Gemini response: {e}")
        if 'response' in locals() and hasattr(response, 'text'):
            print(f"Raw response: {response.text}")
        sys.exit(1)
    print(f"  Prompt tokens: {response.usage_metadata.prompt_token_count}")
    print(
        f"  Response tokens: {response.usage_metadata.candidates_token_count}")
    print(f"  Total tokens: {response.usage_metadata.total_token_count}")

# --- 4. Main Execution ---


def main():
    if not all([GEMINI_API_KEY, TRELLO_API_KEY, TRELLO_API_TOKEN]):
        print("Error: Please set all API keys in your .env file.")
        sys.exit(1)

    print("--- Starting Hackathon Code-to-Trello Script ---")

    # Step 1: Scan the codebase
    print("Scanning local directory...")
    tree, contents = scan_codebase()

    # Step 2: Get Trello structure from Gemini
    trello_data = get_trello_json_from_gemini(tree, contents)

    # Step 3: Build the Trello Board
    print("\n--- Building Trello Board ---")
    board_id = create_board()
    for trello_list in trello_data.get('lists', []):
        list_name = trello_list.get('name', 'Unnamed List')
        list_id = create_list(board_id, list_name)

        for card in trello_list.get('cards', []):
            card_name = card.get('name', 'Unnamed Card')
            card_desc = card.get('description', 'No description.')
            create_card(list_id, card_name, card_desc)

    print("\n--- DEMO COMPLETE! ---")
    print("Your Trello board is ready. Go check it out!")


if __name__ == "__main__":
    main()
