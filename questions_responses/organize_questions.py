import json
import os
import re
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import List, Dict, Tuple, Optional

class QuestionProcessor:
    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.questions_dir = self.base_dir / "questions"
        self.audio_dir = self.base_dir / "audio"
        self.questions_dir.mkdir(parents=True, exist_ok=True)
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.existing_questions = self.load_existing_questions()
        self.next_id = self.calculate_next_id()

    def load_existing_questions(self) -> List[Dict]:
        mapping_file = self.questions_dir / "mapping.json"
        if mapping_file.exists():
            with open(mapping_file) as f:
                return json.load(f)["questions"]
        return []

    def calculate_next_id(self) -> int:
        if not self.existing_questions:
            return 1
        return max(int(q["id"].split("-")[-1]) for q in self.existing_questions) + 1

    def is_duplicate(self, new_question: Dict) -> bool:
        """Check if a question is already in the database based on content similarity."""
        for existing in self.existing_questions:
            if (existing["date"] == new_question["date"] and 
                existing["author"] == new_question["author"] and 
                existing["question"] == new_question["question"]):
                return True
        return False

    @staticmethod
    def extract_audio_files(line: str) -> List[str]:
        if "opus" not in line:
            return []
        match = re.search(r"(\d{4}-\d{2}-\d{2}-AUDIO-\d+\.opus)", line)
        if match:
            return [match.group(1)]
        return []

    @staticmethod
    def generate_id(date: str) -> str:
        parts = date.split("/")
        return f"20{parts[2]}-{parts[1]}-{parts[0]}"

    def extract_question_info(self, lines: List[str], start_index: int) -> Tuple[Optional[Dict], int]:
        """Extract question information from chat lines starting at given index."""
        current_line = lines[start_index]
        base_match = re.match(r"(\d{2}/\d{2}/\d{2}\d{2}) (\d{2}:\d{2}:\d{2}): ([^:]+): (.+)", current_line)
        if not base_match:
            return None, start_index + 1
        
        date, time, author, message_start = base_match.groups()
        
        # Skip system messages and audio-only messages
        if "fichier joint" in message_start or "ajouté" in message_start or "créé" in message_start:
            return None, start_index + 1
        
        # Collect full message text across multiple lines
        message_lines = [message_start.strip()]
        current_index = start_index + 1
        
        while current_index < len(lines):
            next_line = lines[current_index].strip()
            # Only break on clear message start patterns (date/time/author)
            if re.match(r"\d{2}/\d{2}/\d{2}\d{2} \d{2}:\d{2}:\d{2}: .+: .+", next_line):
                break
                
            # Add non-empty continuation lines to message, including those with audio references
            if next_line and not next_line.startswith("‎"):
                # Don't add the audio file line itself
                if not re.match(r"^\d{4}-\d{2}-\d{2}-AUDIO-\d+\.opus$", next_line.strip()):
                    message_lines.append(next_line)
            current_index += 1
        
        # Get audio files from the next line if it exists
        audio_files = []
        if current_index < len(lines):
            audio_files = self.extract_audio_files(lines[current_index])
            if audio_files:
                current_index += 1
        
        return {
            "date": date,
            "author": author.replace("💶", "").replace("💳", "").strip(),
            "question": " ".join(message_lines).strip(),
            "audio_files": audio_files
        }, current_index

    def save_question(self, question_entry: Dict) -> None:
        """Save a question to a text file and copy its audio files."""
        # Create question file
        with open(self.questions_dir / f"{question_entry['id']}.txt", "w") as qf:
            qf.write(f"Question {question_entry['id']}:\n\n")
            qf.write(f"Date: {question_entry['date']}\n")
            qf.write(f"Auteur: {question_entry['author']}\n\n")
            qf.write(f"Question:\n{question_entry['question']}\n\n")
            qf.write("Fichiers audio:\n")
            if question_entry["audio_files"]:
                for audio in question_entry["audio_files"]:
                    qf.write(f"- {audio}\n")
            else:
                qf.write("- Pas de fichier audio (réponse textuelle)\n")

    def copy_audio_files(self, question_entry: Dict, source_dir: Path) -> None:
        """Copy audio files for a question from source directory to audio directory."""
        for audio in question_entry["audio_files"]:
            src = source_dir / audio
            dst = self.audio_dir / audio
            if src.exists() and not dst.exists():
                shutil.copy2(src, dst)

    def process_chat_file(self, chat_file: Path, audio_source_dir: Path) -> List[Dict]:
        """Process a WhatsApp chat file and return new questions."""
        with open(chat_file, "r") as f:
            lines = f.readlines()

        new_questions = []
        i = 0
        while i < len(lines):
            info, next_i = self.extract_question_info(lines, i)
            i = next_i
            if info and not self.is_duplicate(info):
                date_id = self.generate_id(info["date"])
                question_id_str = f"{date_id}-{self.next_id:03d}"
                
                question_entry = {
                    "id": question_id_str,
                    "date": info["date"],
                    "author": info["author"],
                    "question": info["question"],
                    "audio_files": info["audio_files"],
                    "tags": []
                }
                
                self.save_question(question_entry)
                self.copy_audio_files(question_entry, audio_source_dir)
                new_questions.append(question_entry)
                self.next_id += 1

        return new_questions

    def process_zip(self, zip_path: Path) -> Dict[str, int]:
        """Process a WhatsApp export ZIP file and return statistics."""
        print(f"Processing ZIP file: {zip_path}")
        # Create temporary directory for extraction
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            print(f"Created temp directory: {temp_path}")
            
            # Extract ZIP contents
            with zipfile.ZipFile(zip_path) as zf:
                print("ZIP contents:", zf.namelist())
                zf.extractall(temp_path)
            
            # Find chat file
            chat_files = list(temp_path.glob("*_chat.txt"))
            print(f"Found chat files: {chat_files}")
            if not chat_files:
                raise ValueError("No _chat.txt file found in ZIP")
            
            # List audio files
            audio_files = list(temp_path.glob("*.opus"))
            print(f"Found {len(audio_files)} audio files")
            print("Sample audio files:", audio_files[:5])
            
            # Process chat file
            print(f"Processing chat file: {chat_files[0]}")
            new_questions = self.process_chat_file(chat_files[0], temp_path)
            print(f"Processed {len(new_questions)} new questions")
            
            # Update existing questions and save mapping
            self.existing_questions.extend(new_questions)
            mapping_file = self.questions_dir / "mapping.json"
            print(f"Saving to mapping file: {mapping_file}")
            with open(mapping_file, "w") as f:
                json.dump({"questions": self.existing_questions}, f, indent=2, ensure_ascii=False)
            
            # Return statistics
            stats = {
                "total_processed": len(new_questions),
                "with_audio": sum(1 for q in new_questions if q["audio_files"]),
                "without_audio": sum(1 for q in new_questions if not q["audio_files"])
            }
            print("Processing statistics:", stats)
            return stats

def main(zip_path: str, base_dir: str = "."):
    """Main function to process a WhatsApp export ZIP file."""
    processor = QuestionProcessor(Path(base_dir))
    stats = processor.process_zip(Path(zip_path))
    
    print(f"Total des nouvelles questions traitées : {stats['total_processed']}")
    print(f"Questions avec audio : {stats['with_audio']}")
    print(f"Questions sans audio : {stats['without_audio']}")
    print(f"Total des questions dans la base : {len(processor.existing_questions)}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python organize_questions.py <whatsapp_export.zip>")
        sys.exit(1)
    main(sys.argv[1])
