import os
import requests
import json
import sys
from google import genai
from dotenv import load_dotenv

load_dotenv()


# --- 1. Trello API Functions ---

TRELLO_API_URL = "https://api.trello.com/1/"
trello_auth = {'key': TRELLO_API_KEY, 'token': TRELLO_API_TOKEN}

def create_board(board_name):
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
    params = {'name': card_name, 'desc': card_desc, 'idList': list_id, **trello_auth}
    response = requests.post(url, params=params)
    response.raise_for_status()
    return response.json()['id']

# --- 2. Code Scanning Function ---

def scan_codebase(root_dir=".", max_file_size=10000):
    """Scans the codebase and returns a string with the file tree and key file contents."""
    file_tree = []
    file_contents = []
    
    # Add files/dirs to ignore
    ignore_dirs = {'.git', '.vscode', '__pycache__', 'node_modules', '.github'}
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
                    file_contents.append(f"--- Content of {file_path} (truncated) ---\nFile is too large, skipping content.\n")
                    continue

                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    file_contents.append(f"--- Content of {file_path} ---\n{content}\n")
            except Exception as e:
                file_contents.append(f"--- Could not read {file_path}: {e} ---\n")

    return "\n".join(file_tree), "\n".join(file_contents)

# --- 3. Gemini "Magic" JSON Function ---

def get_trello_json_from_gemini(code_tree, code_contents):
    print("Asking Gemini to design the Trello board...")
    
    if not GEMINI_API_KEY.startswith("PASTE_"):
        genai.configure(api_key=GEMINI_API_KEY)
    else:
        print("Error: GEMINI_API_KEY is not set.")
        sys.exit(1)
        
    model = genai.GenerativeModel('gemini-1.5-pro-latest')
    
    prompt = f"""
    You are an expert software architect and project manager. Your job is to
    analyze a codebase and automatically generate a Trello board structure for it.
    
    Based on the file tree and file contents below, generate a JSON object
    for a Trello board.

    The JSON must follow this exact schema:
    {{
      "boardName": "Project-Name Codebase Overview",
      "lists": [
        {{
          "name": "List Name (e.g., 'Core Logic', 'API/Routing', 'Database', 'Frontend')",
          "cards": [
            {{ 
              "name": "filename.ext", 
              "description": "One-sentence summary of this file's purpose and its main functions/classes."
            }}
          ]
        }}
      ]
    }}

    Rules:
    1.  Create 3-5 high-level lists that represent the core components of the app.
    2.  For each list, add cards for the most *important* files related to that component.
    3.  The "description" for each card should be a concise summary.
    4.  Return *ONLY* the raw JSON object and nothing else. Do not wrap it in ```json ... ```.

    --- FILE TREE ---
    {code_tree}

    --- FILE CONTENTS ---
    {code_contents}
    """
    
    try:
        response = model.generate_content(prompt)
        # Clean the response to ensure it's valid JSON
        cleaned_json = response.text.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned_json)
    except Exception as e:
        print(f"Error parsing Gemini response: {e}")
        print(f"Raw response: {response.text}")
        sys.exit(1)


# --- 4. Main Execution ---

def main():
    if any(k.startswith("PASTE_") for k in [GEMINI_API_KEY, TRELLO_API_KEY, TRELLO_API_TOKEN]):
        print("🔥 Error: Please paste your API keys into the script file.")
        sys.exit(1)

    print("--- 🚀 Starting Hackathon Code-to-Trello Script ---")
    
    # Step 1: Scan the codebase
    print("Scanning local directory...")
    tree, contents = scan_codebase()
    
    # Step 2: Get Trello structure from Gemini
    trello_data = get_trello_json_from_gemini(tree, contents)
    
    # Step 3: Build the Trello Board
    print("\n--- 🏗️ Building Trello Board ---")
    board_name = trello_data.get('boardName', 'Codebase Summary')
    board_id = create_board(board_name)
    
    for trello_list in trello_data.get('lists', []):
        list_name = trello_list.get('name', 'Unnamed List')
        list_id = create_list(board_id, list_name)
        
        for card in trello_list.get('cards', []):
            card_name = card.get('name', 'Unnamed Card')
            card_desc = card.get('description', 'No description.')
            create_card(list_id, card_name, card_desc)

    print("\n--- 🎉 DEMO COMPLETE! ---")
    print("Your Trello board is ready. Go check it out!")

if __name__ == "__main__":
    main()