import asyncio
import logging
import os
import sys
from pathlib import Path
from telegram import Bot
from telegram.error import TelegramError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("test_audio.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Constants
BOT_TOKEN = os.environ.get("BOT_TOKEN", "7099400053:AAGpkQ978uhK1M3GnFwNoNH04QyNVb4ufsk")
CHAT_ID = os.environ.get("TELEGRAM_TEST_CHAT_ID", "39557300")
AUDIO_DIR = Path("/home/ubuntu/questions_responses/audio")

# Test cases
TEST_CASES = [
    {
        "id": "2017-03-01-022",
        "audio": "2017-03-01-AUDIO-00000022.opus",
        "description": "Known valid audio file"
    },
    {
        "id": "2017-03-09-177",
        "audio": "2017-03-09-AUDIO-00000177.opus",
        "description": "Another valid audio file"
    },
    {
        "id": "invalid-id",
        "audio": None,
        "description": "Invalid ID for error handling"
    }
]

async def wait_for_audio_response(bot: Bot, sent_message_id: int, timeout: int = 30) -> bool:
    """Wait for audio file response from bot."""
    start_time = asyncio.get_event_loop().time()
    update_offset = 0
    
    while asyncio.get_event_loop().time() - start_time < timeout:
        try:
            updates = await bot.get_updates(offset=update_offset, timeout=1)
            
            for update in updates:
                logger.info(f"Processing update {update.update_id}")
                if update.message:
                    if update.message.audio:
                        logger.info(f"✓ Found audio file: {update.message.audio.file_name}")
                        return True
                    elif update.message.document and update.message.document.mime_type == "audio/opus":
                        logger.info(f"✓ Found audio document: {update.message.document.file_name}")
                        return True
                    elif update.message.text:
                        logger.info(f"Message text: {update.message.text}")
                        if "erreur" in update.message.text.lower():
                            logger.error(f"✗ Error response: {update.message.text}")
                            return False
                update_offset = update.update_id + 1
            
            await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"Error getting updates: {e}")
            await asyncio.sleep(1)
    
    logger.error(f"✗ No audio response received after {timeout}s")
    return False

async def test_audio(test_case: dict) -> bool:
    """Test the /audio command with a specific test case."""
    try:
        # Initialize bot
        bot = Bot(token=BOT_TOKEN)
        logger.info(f"Testing audio command with ID: {test_case['id']}")
        
        # Send audio command
        message = await bot.send_message(
            chat_id=CHAT_ID,
            text=f"/audio {test_case['id']}"
        )
        logger.info(f"Sent audio command (message_id: {message.message_id})")
        
        # Wait for response
        success = await wait_for_audio_response(bot, message.message_id)
        
        # For invalid ID test case, success means we got an error message
        if test_case['audio'] is None:
            return not success  # Should fail for invalid ID
            
        if success:
            logger.info(f"✓ Audio test passed for ID '{test_case['id']}'")
        else:
            logger.error(f"✗ Audio test failed for ID '{test_case['id']}'")
            
        return success
        
    except Exception as e:
        logger.error(f"Error in test: {e}")
        return False

async def run_audio_tests():
    """Run all audio tests."""
    results = []
    for test_case in TEST_CASES:
        logger.info(f"\nTesting audio case: {test_case['description']}")
        success = await test_audio(test_case)
        results.append((test_case['id'], success))
        # Add delay between tests
        await asyncio.sleep(2)
    
    # Print summary
    print("\nAudio Test Results:")
    print("=" * 50)
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for audio_id, success in results:
        status = "✓" if success else "✗"
        print(f"{status} Audio '{audio_id}'")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    # We expect the invalid ID test to fail, so success is 2/3
    return passed == 2

def main():
    """Run the audio tests."""
    try:
        success = asyncio.run(run_audio_tests())
        
        if not success:
            logger.error("Some tests failed")
            sys.exit(1)
            
        logger.info("All audio tests completed successfully")
        
    except KeyboardInterrupt:
        logger.info("Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Tests failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
