import json
import requests
import sys
from pathlib import Path

def validate_audio_files(mapping_file: Path, api_url: str):
    print(f"Loading mapping file: {mapping_file}")
    with open(mapping_file) as f:
        data = json.load(f)
    
    questions = data["questions"]
    total_questions = len(questions)
    questions_with_audio = sum(1 for q in questions if q["audio_files"])
    print(f"\nTotal questions: {total_questions}")
    print(f"Questions with audio: {questions_with_audio}")
    
    # Track missing files
    missing_files = []
    valid_questions = []
    
    for q in questions:
        valid_audio_files = []
        for audio in q.get("audio_files", []):
            url = f"{api_url}/audio/{audio}"
            try:
                response = requests.head(url)
                if response.status_code == 200:
                    valid_audio_files.append(audio)
                else:
                    missing_files.append((audio, q["id"]))
            except Exception as e:
                print(f"Error checking {audio}: {e}")
                missing_files.append((audio, q["id"]))
        
        # Update question with only valid audio files
        q["audio_files"] = valid_audio_files
        valid_questions.append(q)
    
    # Update mapping file
    print(f"\nMissing audio files: {len(missing_files)}")
    if missing_files:
        print("\nFirst 10 missing files:")
        for audio, qid in missing_files[:10]:
            print(f"- {audio} (Question {qid})")
    
    # Save updated mapping
    updated_data = {"questions": valid_questions}
    output_file = mapping_file.parent / "mapping_cleaned.json"
    with open(output_file, "w") as f:
        json.dump(updated_data, f, indent=2, ensure_ascii=False)
    
    print(f"\nUpdated mapping saved to: {output_file}")
    print(f"Removed {len(missing_files)} invalid audio file references")

if __name__ == "__main__":
    mapping_file = Path("mapping.json")
    api_url = "https://app-tnegmvca.fly.dev"
    validate_audio_files(mapping_file, api_url)
