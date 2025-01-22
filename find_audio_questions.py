import json
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def find_questions_with_audio():
    """Find questions that have associated audio files."""
    mapping_file = Path("/home/ubuntu/questions_responses/questions/mapping.json")
    audio_dir = Path("/home/ubuntu/questions_responses/audio")
    
    try:
        with open(mapping_file) as f:
            data = json.load(f)
            
        # Find questions with audio files
        audio_questions = []
        for q in data["questions"]:
            if q["audio_files"]:
                # Verify audio file exists
                audio_path = audio_dir / q["audio_files"][0]
                if audio_path.exists():
                    logger.info(f"Found valid question with audio:")
                    logger.info(f"  ID: {q['id']}")
                    logger.info(f"  Audio: {q['audio_files'][0]}")
                    logger.info(f"  Question: {q['question'][:100]}...")
                    audio_questions.append(q)
                    if len(audio_questions) >= 3:  # Find first 3 examples
                        break
                        
        if not audio_questions:
            logger.error("No questions with valid audio files found!")
        
    except Exception as e:
        logger.error(f"Error finding audio questions: {e}")
        raise

if __name__ == "__main__":
    find_questions_with_audio()
