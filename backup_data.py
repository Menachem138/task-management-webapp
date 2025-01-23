import shutil
from pathlib import Path
from datetime import datetime
import json

def create_backup():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_root = Path("/home/ubuntu/backup")
    backup_dir = backup_root / f"whatsapp_data_{timestamp}"
    
    # Create backup directories
    backup_dir.mkdir(parents=True, exist_ok=True)
    (backup_dir / "questions").mkdir(exist_ok=True)
    (backup_dir / "audio").mkdir(exist_ok=True)
    
    # Source directories
    source_dirs = [
        Path("/home/ubuntu/questions_responses/questions"),
        Path("/home/ubuntu/QnAWebApp/public"),
        Path("/home/ubuntu/QnAWebApp/dist"),
        Path("/home/ubuntu")
    ]
    
    print(f"Creating backup in: {backup_dir}")
    
    # Copy mapping files
    for src_dir in source_dirs:
        mapping_file = src_dir / "mapping.json"
        if mapping_file.exists():
            dest = backup_dir / "mapping_files" / f"mapping_{src_dir.name}.json"
            dest.parent.mkdir(exist_ok=True)
            shutil.copy2(mapping_file, dest)
            print(f"Backed up: {mapping_file} -> {dest}")
    
    # Copy question files and audio files
    questions_dir = Path("/home/ubuntu/questions_responses/questions")
    audio_dir = Path("/home/ubuntu/questions_responses/audio")
    
    if questions_dir.exists():
        for file in questions_dir.glob("*.txt"):
            shutil.copy2(file, backup_dir / "questions" / file.name)
        print(f"Backed up question files to: {backup_dir}/questions/")
    
    if audio_dir.exists():
        for file in audio_dir.glob("*.opus"):
            shutil.copy2(file, backup_dir / "audio" / file.name)
        print(f"Backed up audio files to: {backup_dir}/audio/")
    
    # Verify backup integrity
    def verify_json(file_path):
        try:
            with open(file_path) as f:
                json.load(f)
            return True
        except:
            return False
    
    print("\nVerifying backup integrity...")
    all_valid = True
    for json_file in (backup_dir / "mapping_files").glob("*.json"):
        if not verify_json(json_file):
            print(f"❌ Invalid JSON: {json_file}")
            all_valid = False
    
    if all_valid:
        print("✓ All JSON files verified successfully")
        print(f"✓ Backup completed: {backup_dir}")
    else:
        print("❌ Backup verification failed!")

if __name__ == "__main__":
    create_backup()
