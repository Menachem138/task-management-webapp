import json
import sys
from pathlib import Path

def verify_mapping_file(file_path):
    """Verify mapping.json is valid and contains the correct number of questions."""
    print(f"Verifying {file_path}...")
    
    try:
        with open(file_path) as f:
            data = json.load(f)
        print("JSON is valid")
        
        questions = data.get('questions', [])
        total_questions = len(questions)
        print(f"\nTotal questions in mapping.json: {total_questions}")
        print(f"Expected questions (3493 - 85): 3408")
        
        if total_questions != 3408:
            print("ERROR: Question count mismatch!")
            return False
            
        print("Question count verified successfully")
        
        # Verify question structure
        if questions:
            print("\nVerifying question structure...")
            required_fields = {'id', 'date', 'author', 'question', 'audio_files', 'tags'}
            for q in questions:
                missing_fields = required_fields - set(q.keys())
                if missing_fields:
                    print(f"ERROR: Question {q.get('id', 'unknown')} is missing fields: {missing_fields}")
                    return False
                    
        print("All questions have correct structure")
        return True
        
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON format - {str(e)}")
        return False
    except Exception as e:
        print(f"ERROR: Verification failed - {str(e)}")
        return False

if __name__ == "__main__":
    mapping_file = Path("/home/ubuntu/questions_responses/questions/mapping.json")
    if not verify_mapping_file(mapping_file):
        sys.exit(1)
