import json
from datetime import datetime, time
from pathlib import Path
import sys
import shutil

def parse_date(date_str):
    """Parse date string in format DD/MM/YY or DD/MM/YYYY"""
    try:
        # Try DD/MM/YY first
        return datetime.strptime(date_str, "%d/%m/%y")
    except ValueError:
        try:
            # Try DD/MM/YYYY
            return datetime.strptime(date_str, "%d/%m/%Y")
        except ValueError:
            print(f"Warning: Could not parse date: {date_str}")
            return None

def analyze_mapping_file(file_path):
    print(f"Analyzing {file_path}...")
    
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    questions = data.get('questions', [])
    print(f"\nTotal questions: {len(questions)}")
    
    # Find our target message
    target_message = None
    for q in questions:
        if (q['author'] == 'Yossef Haim' and 
            'important a partir de maintenant' in q['question']):
            target_message = q
            break
    
    if not target_message:
        print("Target message not found!")
        return
    
    print(f"\nTarget message found:")
    print(f"ID: {target_message['id']}")
    print(f"Date: {target_message['date']}")
    print(f"Author: {target_message['author']}")
    print(f"Question: {target_message['question']}")
    
    # Analyze messages before target
    target_date = parse_date(target_message['date'])
    if not target_date:
        print("Error: Could not parse target date")
        return
        
    messages_before = []
    messages_after = []
    same_date = []
    
    for q in questions:
        msg_date = parse_date(q['date'])
        if not msg_date:
            print(f"Warning: Could not parse date format: {q['date']}")
            continue
            
        if msg_date < target_date:
            messages_before.append(q)
        elif msg_date > target_date:
            messages_after.append(q)
        else:
            same_date.append(q)
            
    # Sort messages on same date by ID to determine order
    same_date.sort(key=lambda x: x['id'])
    
    # Find position of target message
    target_idx = next((i for i, q in enumerate(same_date) if q['id'] == target_message['id']), -1)
    
    if target_idx >= 0:
        # Add messages from same date before target to messages_before
        messages_before.extend(same_date[:target_idx])
        # Add messages from same date after target to messages_after
        messages_after.extend(same_date[target_idx + 1:])
    
    print(f"\nAnalysis Results:")
    print(f"- Messages to be deleted (before target): {len(messages_before)}")
    print(f"- Messages to keep (after target): {len(messages_after)}")
    print(f"- Total messages affected: {len(messages_before)}")
    
    # Analyze message IDs and structure
    print("\nMessage ID format analysis:")
    id_formats = set()
    for q in questions[:10]:  # Sample first 10 messages
        id_formats.add(q['id'].split('-')[0])  # Get prefix format
    print(f"ID formats found: {', '.join(id_formats)}")
    
    # Sample of message structure
    if questions:
        print("\nExample message structure:")
        print(json.dumps(questions[0], indent=2))
    
    # Check for message relationships
    print("\nChecking for message relationships...")
    has_parent_refs = any('parent_id' in q for q in questions)
    has_thread_refs = any('thread_id' in q for q in questions)
    has_reply_refs = any('reply_to' in q for q in questions)
    
    print(f"Has parent references: {has_parent_refs}")
    print(f"Has thread references: {has_thread_refs}")
    print(f"Has reply references: {has_reply_refs}")

def remove_old_messages(mapping_file, questions_dir):
    """Remove messages before target datetime and their corresponding files."""
    # Target datetime from the specified message
    TARGET_DATETIME = datetime(2017, 3, 2, 1, 24, 18)
    
    print(f"Processing {mapping_file}...")
    with open(mapping_file, 'r') as f:
        data = json.load(f)
    
    questions = data.get('questions', [])
    print(f"\nTotal questions before filtering: {len(questions)}")
    
    # Find target message and filter questions
    filtered_questions = []
    messages_to_remove = []
    
    for q in questions:
        msg_date = parse_date(q['date'])
        if not msg_date:
            print(f"Warning: Could not parse date for message {q['id']}")
            filtered_questions.append(q)
            continue
        
        msg_datetime = datetime.combine(msg_date.date(), time(0, 0, 0))
        if msg_datetime < TARGET_DATETIME:
            messages_to_remove.append(q)
        else:
            filtered_questions.append(q)
    
    print(f"\nMessages to remove: {len(messages_to_remove)}")
    print(f"Messages to keep: {len(filtered_questions)}")
    
    # Create backup before making changes
    backup_file = mapping_file.parent / "mapping.json.bak"
    shutil.copy2(mapping_file, backup_file)
    print(f"\nBackup created at: {backup_file}")
    
    # Remove question text files
    for q in messages_to_remove:
        txt_file = questions_dir / f"{q['id']}.txt"
        if txt_file.exists():
            txt_file.unlink()
            print(f"Removed question file: {txt_file.name}")
    
    # Save filtered questions
    data['questions'] = filtered_questions
    with open(mapping_file, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\nUpdated mapping.json saved with {len(filtered_questions)} questions")
    return filtered_questions, messages_to_remove

def remove_specific_message(mapping_file, target_id):
    """Remove a specific message by ID and its corresponding text file."""
    print(f"Processing {mapping_file}...")
    mapping_file = Path(mapping_file)
    questions_dir = mapping_file.parent
    
    # Create backup
    backup_file = mapping_file.parent / "mapping.json.bak"
    shutil.copy2(mapping_file, backup_file)
    print(f"\nBackup created at: {backup_file}")
    
    # Load and filter questions
    with open(mapping_file, 'r') as f:
        data = json.load(f)
    
    questions = data.get('questions', [])
    print(f"\nTotal questions before removal: {len(questions)}")
    
    # Remove target message
    filtered_questions = [q for q in questions if q['id'] != target_id]
    
    if len(filtered_questions) == len(questions):
        print(f"\nTarget message {target_id} not found!")
        return False
    
    # Remove corresponding text file
    txt_file = questions_dir / f"{target_id}.txt"
    if txt_file.exists():
        txt_file.unlink()
        print(f"Removed question file: {txt_file.name}")
    
    # Save updated mapping
    data['questions'] = filtered_questions
    with open(mapping_file, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\nTarget message {target_id} removed successfully")
    print(f"Total questions after removal: {len(filtered_questions)}")
    return True

def search_messages(mapping_file, date_pattern=None, author=None):
    """Search messages by date pattern and/or author."""
    with open(mapping_file, 'r') as f:
        data = json.load(f)
    
    matches = []
    for q in data.get('questions', []):
        if date_pattern and date_pattern not in q['date']:
            continue
        if author and author not in q['author']:
            continue
        matches.append(q)
    return matches

if __name__ == "__main__":
    mapping_file = Path("/home/ubuntu/questions_responses/questions/mapping.json")
    questions_dir = mapping_file.parent
    
    print("Starting message removal process...")
    print(f"Target datetime: {datetime(2017, 3, 2, 1, 24, 18)}")
    
    # First remove messages before target date
    filtered_questions, removed_messages = remove_old_messages(mapping_file, questions_dir)
    
    print(f"\nRemoved {len(removed_messages)} messages before target date")
    print(f"Remaining messages: {len(filtered_questions)}")
    
    # Now look for the specific target message
    target_message = None
    for q in filtered_questions:
        if (q['date'].startswith("02/03/") and 
            q['author'] == "Yossef Haim" and 
            "*important a partir de maintenant nous ne parlons plus entre nous ici je rajoute qlq*" in q['question']):
            target_message = q
            break
    
    if target_message:
        print("\nFound target message to remove:")
        print(f"ID: {target_message['id']}")
        print(f"Date: {target_message['date']}")
        print(f"Author: {target_message['author']}")
        print(f"Question: {target_message['question']}")
        
        # Remove the specific message
        if remove_specific_message(mapping_file, target_message['id']):
            print("Successfully removed target message")
    else:
        print("\nTarget message not found after date filtering")
