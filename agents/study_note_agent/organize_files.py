import json
import os
import shutil
from pathlib import Path
from collections import defaultdict

def extract_sender_name(sender_email):
    """Extract the sender's name from email string (e.g., 'Neo Kim <email@domain.com>' -> 'Neo Kim')"""
    if '<' in sender_email:
        return sender_email.split('<')[0].strip()
    return sender_email.strip()

def organize_files(base_dir, folder_name):
    """Organize files in mdnotes or rawtext by sender"""
    folder_path = Path(base_dir) / folder_name
    
    if not folder_path.exists():
        print(f"Folder {folder_path} does not exist!")
        return
    
    # Dictionary to store sender -> files mapping
    sender_files = defaultdict(list)
    
    # First pass: extract all senders and their files
    for file in folder_path.glob("*.json"):
        try:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                sender = data.get('sender', 'Unknown')
                sender_name = extract_sender_name(sender)
                
                # Get the base filename without extension
                base_name = file.stem
                
                # Find both JSON and TXT versions
                json_file = file
                txt_file = folder_path / f"{base_name}.txt"
                
                sender_files[sender_name].append({
                    'json': json_file,
                    'txt': txt_file if txt_file.exists() else None
                })
        except Exception as e:
            print(f"Error reading {file}: {e}")
    
    # Second pass: create directories and move files
    for sender_name, files in sender_files.items():
        # Create sender directory
        sender_dir = folder_path / sender_name
        sender_dir.mkdir(exist_ok=True)
        print(f"Created directory: {sender_dir}")
        
        # Move files
        for file_pair in files:
            json_file = file_pair['json']
            txt_file = file_pair['txt']
            
            try:
                # Move JSON file
                new_json_path = sender_dir / json_file.name
                shutil.move(str(json_file), str(new_json_path))
                print(f"  Moved: {json_file.name} -> {sender_name}/")
                
                # Move TXT file if it exists
                if txt_file and txt_file.exists():
                    new_txt_path = sender_dir / txt_file.name
                    shutil.move(str(txt_file), str(new_txt_path))
            except Exception as e:
                print(f"Error moving {json_file.name}: {e}")

def main():
    base_dir = "/home/liber_primus/code/ai_and_ml_projects/agents/study_note_agent"
    
    print("=" * 60)
    print("Organizing mdnotes folder...")
    print("=" * 60)
    organize_files(base_dir, "mdnotes")
    
    print("\n" + "=" * 60)
    print("Organizing rawtext folder...")
    print("=" * 60)
    organize_files(base_dir, "rawtext")
    
    print("\n" + "=" * 60)
    print("Organization complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()
