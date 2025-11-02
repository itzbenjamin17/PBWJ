import os
import requests
import json
import sys
import subprocess
import uuid
from google.genai import Client
from dotenv import load_dotenv


load_dotenv()


# Load API keys from environment variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

if not GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY is not set.")
    sys.exit(1)



TRELLO_API_URL = "https://api.trello.com/1/"

def update_board(board_id, code_tree, code_contents, trello_auth, status):
    url = f"{TRELLO_API_URL}boards/{board_id}/lists"
    trello_lists = requests.get(url, params={**trello_auth})
    trello_lists.raise_for_status()
    status.write("Fetching existing Trello board data...")

    lists_ids = [lst['id'] for lst in trello_lists.json()]
    data = {}
    for id in lists_ids:
        url = f"{TRELLO_API_URL}lists/{id}/cards"
        cards = requests.get(url, params={**trello_auth})
        cards.raise_for_status()
        for card in cards.json():
            data[card['id']] = card['desc']

    status.write("Asking Gemini to update the Trello board...")
    if not GEMINI_API_KEY or GEMINI_API_KEY.startswith("PASTE_"):
        print("Error: GEMINI_API_KEY is not set or still contains placeholder.")
        sys.exit(1)

    client = Client(api_key=GEMINI_API_KEY)
    prompt = f"""
    You are an intelligent code analysis assistant that helps developers manage their projects by analyzing codebases and generating actionable Trello cards. Your job is to
    analyze a codebase, update the development roadmap using the provided codebase (excluding this file) and automatically generate structured Trello card recommendations.

    Based on the file tree and file contents below, generate a JSON object
    for a Trello board. If the description of a generated card roughly matches the description of an existing card in the board, update it if need be or rewrite the generated card as the existing matching card. Do not include any generated cards that have been resolved in the codebase. Otherwise, add new cards as needed.


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


    --- EXISTING CARDS ---
    {data}

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


def create_board(board_name, trello_auth, status):
    status.write(f"Creating Trello board: {board_name}...")
    url = f"{TRELLO_API_URL}boards"
    params = {'name': board_name, 'defaultLists': 'false', **trello_auth}
    response = requests.post(url, params=params)
    response.raise_for_status()
    status.update(label=f"✅ Board created! URL: {response.json()['shortUrl']}")
    status.write(f"✅ Board created! URL: {response.json()['shortUrl']}")
    return response.json()['id']


def create_list(board_id, list_name, trello_auth, status):
    status.write(f"  Creating list: {list_name}...")
    url = f"{TRELLO_API_URL}lists/"
    params = {'name': list_name, 'idBoard': board_id, **trello_auth}
    response = requests.post(url, params=params)
    response.raise_for_status()
    return response.json()['id']


def create_card(list_id, card_name, card_desc, trello_auth, status):
    status.write(f"    Creating card: {card_name}...")
    url = f"{TRELLO_API_URL}cards/"
    params = {'name': card_name, 'desc': card_desc,
              'idList': list_id, **trello_auth}
    response = requests.post(url, params=params)
    response.raise_for_status()
    return response.json()['id']



def scan_codebase(root_dir=".", max_file_size=10000):
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


def get_trello_json_from_gemini(code_tree, code_contents, status):
    status.write("Asking Gemini to design the Trello board...")

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


def main(trello_api_key, trello_token, status, github_url=None):
    trello_auth = {'key': trello_api_key, 'token': trello_token}

    if github_url:
        board_name = github_url.split('/')[-1]
        if board_name.endswith('.git'):
            board_name = board_name[:-4]
    else:
        board_name = os.getcwd().split(os.sep)[-1]

    if not GEMINI_API_KEY:
        print("Error: Please set all API keys in your .env file.")
        sys.exit(1)

    print("--- Starting Hackathon Code-to-Trello Script ---")
    status.update(expanded=True)

    if github_url:
        status.write("Cloning the repository")
        # unique repo id
        urid = str(uuid.uuid4())
        repo_destination = os.path.join("github_repos", urid)
        subprocess.run(["mkdir", "-p", repo_destination])
        subprocess.run(["git", "clone", github_url, repo_destination])
    else:
        repo_destination = "."

    # Step 1: Scan the codebase
    status.write("Scanning the codebase...")
    tree, contents = scan_codebase(repo_destination)
    if repo_destination.startswith("github_repos"):
        subprocess.run(["rm", "-rf", repo_destination])

    url = f"{TRELLO_API_URL}members/me/"
    user_id = requests.get(url, params={**trello_auth}).json()['id']
    url = f"{TRELLO_API_URL}members/{user_id}/boards"
    boards = requests.get(url, params={**trello_auth}).json()
    for board in boards:
        if board['name'] == board_name:
            cached_board_id = board['id']
            board_exists = True
            break

    if board_exists:
        status.write(f"Using cached Trello board ID: {cached_board_id}")
        board_id = cached_board_id
        try:
            url = f"{TRELLO_API_URL}boards/{board_id}"
            response = requests.get(url, params={**trello_auth})
            response.raise_for_status()
            if response.json()['name'] != board_name:
                board_exists = False
            if board_exists:
                trello_data = update_board(board_id, tree, contents, trello_auth, status)

            for trello_list in trello_data.get('lists', []):
                list_name = trello_list.get('name', 'Unnamed List')
                list_id = create_list(board_id, list_name, trello_auth, status)
                for card in trello_list.get('cards', []):
                    card_name = card.get('name', 'Unnamed Card')
                    card_desc = card.get('description', 'No description.')
                    create_card(list_id, card_name, card_desc, trello_auth, status)
            status.update(label="Trello has been updated")
        except:
            board_exists = False


    if not board_exists:
        trello_data = get_trello_json_from_gemini(tree, contents, status)
        status.write("\n--- Building Trello Board ---")
        board_id = create_board(board_name, trello_auth, status)


        for trello_list in trello_data.get('lists', []):
            list_name = trello_list.get('name', 'Unnamed List')
            list_id = create_list(board_id, list_name, trello_auth, status)

        for card in trello_list.get('cards', []):
            card_name = card.get('name', 'Unnamed Card')
            card_desc = card.get('description', 'No description.')
            create_card(list_id, card_name, card_desc, trello_auth, status)

    status.update(state="complete", expanded=False)
    print("\n--- DEMO COMPLETE! ---")
    print("Your Trello board is ready. Go check it out!")

if __name__ == "__main__":
    TRELLO_API_KEY = os.getenv("TRELLO_API_KEY", "")
    TRELLO_API_TOKEN = os.getenv("TRELLO_API_TOKEN", "")

    main(TRELLO_API_KEY, TRELLO_API_TOKEN, status=sys.stdout)
