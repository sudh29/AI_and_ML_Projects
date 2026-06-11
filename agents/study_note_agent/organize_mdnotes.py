import json
import os
import shutil
from pathlib import Path
from collections import defaultdict

def extract_sender_from_rawtext(rawtext_path, base_name):
    """Find sender from corresponding JSON file in rawtext"""
    json_file = rawtext_path / f"{base_name}.json"
    if json_file.exists():
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                sender = data.get('sender', 'Unknown')
                # Extract sender name from email (e.g., "Neo Kim" from "Neo Kim <email@domain.com>")
                if '<' in sender:
                    return sender.split('<')[0].strip()
                return sender.strip()
        except Exception as e:
            print(f"Error reading {json_file}: {e}")
            return None
    return None

def organize_mdnotes():
    """Organize mdnotes folder by sender, matching rawtext organization"""
    base_dir = Path("/home/liber_primus/code/ai_and_ml_projects/agents/study_note_agent")
    mdnotes_path = base_dir / "mdnotes"
    rawtext_path = base_dir / "rawtext"
    
    if not mdnotes_path.exists():
        print(f"mdnotes folder not found!")
        return
    
    # Process all .md files
    for md_file in mdnotes_path.glob("*.md"):
        base_name = md_file.stem  # filename without .md extension
        
        # Get sender from rawtext folder
        sender_name = extract_sender_from_rawtext(rawtext_path, base_name)
        
        if sender_name:
            # Create sender directory in mdnotes
            sender_dir = mdnotes_path / sender_name
            sender_dir.mkdir(exist_ok=True)
            print(f"Created directory: {sender_dir}")
            
            # Move the md file
            try:
                new_path = sender_dir / md_file.name
                shutil.move(str(md_file), str(new_path))
                print(f"  Moved: {md_file.name} -> {sender_name}/")
            except Exception as e:
                print(f"Error moving {md_file.name}: {e}")
        else:
            print(f"Warning: Could not find sender for {md_file.name}")

if __name__ == "__main__":
    print("=" * 60)
    print("Organizing mdnotes folder by sender...")
    print("=" * 60)
    organize_mdnotes()
    print("\n" + "=" * 60)
    print("mdnotes organization complete!")
    print("=" * 60)
