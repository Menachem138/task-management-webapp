import zipfile
from pathlib import Path

def check_zip_contents(zip_path):
    print(f"Checking contents of {zip_path}")
    with zipfile.ZipFile(zip_path) as zf:
        files = zf.namelist()
        chat_files = [f for f in files if f.endswith('_chat.txt')]
        audio_files = [f for f in files if f.endswith('.opus')]
        
        print("\nFound files:")
        print(f"Chat files ({len(chat_files)}):", chat_files)
        print(f"Audio files ({len(audio_files)}):", audio_files[:5], "..." if len(audio_files) > 5 else "")
        
        return bool(chat_files and audio_files)

zip_path = Path("/home/ubuntu/attachments/512acbfa-a7fd-4afc-bb02-b0a2b27b7515/WhatsApp+Chat+-+Questions+au+Rav+Abichid+2.zip")
if check_zip_contents(zip_path):
    print("\nZIP file contains required files (_chat.txt and .opus files)")
else:
    print("\nZIP file is missing required files")
