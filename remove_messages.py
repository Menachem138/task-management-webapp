import json
from pathlib import Path
import shutil

def remove_old_messages(mapping_file):
    print(f"Processing {mapping_file}...")
    
    # Create backup (additional safety)
    backup = mapping_file.with_suffix(".json.bak")
    shutil.copy2(mapping_file, backup)
    print(f"Created backup: {backup}")
    
    with open(mapping_file) as f:
        data = json.load(f)
    
    original_count = len(data["questions"])
    print(f"\nOriginal question count: {original_count}")
    
    # Print first few messages to check date format
    print("\nChecking first few messages:")
    for q in data["questions"][:5]:
        print(f"Date: {q['date']}, Author: {q['author']}")
    
    # Filter out early messages and marker message
    filtered = []
    for q in data["questions"]:
        # Skip messages from March 1st and 2nd
        if q["date"].startswith("01/03/2017") or q["date"].startswith("02/03/2017"):
            continue
            
        # Skip the marker message specifically
        if "important a partir de maintenant" in q["question"].lower():
            continue
            
        # Keep all other messages
        filtered.append(q)
    
    removed_count = original_count - len(filtered)
    print(f"\nRemoved {removed_count} messages from early January/February")
    
    if removed_count > 0:
        print("\nRemoved messages:")
        removed = [q for q in data["questions"] if q not in filtered]
        for q in removed:
            print(f"Date: {q['date']}, Author: {q['author']}")
    
    # Save filtered data
    data["questions"] = filtered
    with open(mapping_file, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\nUpdated mapping.json saved with {len(filtered)} questions")
    
    # Remove corresponding text files
    questions_dir = mapping_file.parent
    patterns_to_remove = [
        "2017-03-01-*.txt",  # March 1st files
        "2017-03-02-*.txt",  # March 2nd files
    ]
    
    removed_files = 0
    for pattern in patterns_to_remove:
        for txt_file in questions_dir.glob(pattern):
            txt_file.unlink()
            print(f"Removed question file: {txt_file}")

if __name__ == "__main__":
    # Process all mapping files
    mapping_files = [
        Path("/home/ubuntu/QnAWebApp/public/mapping.json"),
        Path("/home/ubuntu/QnAWebApp/public/mapping_cleaned.json"),
        Path("/home/ubuntu/QnAWebApp/dist/mapping.json"),
        Path("/home/ubuntu/QnAWebApp/dist/mapping_cleaned.json"),
        Path("/home/ubuntu/mapping.json"),
        Path("/home/ubuntu/mapping_cleaned.json"),
        Path("/home/ubuntu/questions_responses/questions/mapping.json")
    ]
    
    for mapping_file in mapping_files:
        if mapping_file.exists():
            print(f"\nProcessing {mapping_file}...")
            remove_old_messages(mapping_file)
