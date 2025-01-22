import asyncio
import logging
import time
import os
import psutil
from pathlib import Path
from telegram import Update
from telegram.ext import Application, ApplicationBuilder, ContextTypes
from telegram.error import TelegramError, TimedOut

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
BOT_TOKEN = "7099400053:AAGpkQ978uhK1M3GnFwNoNH04QyNVb4ufsk"
CHAT_ID = "39557300"
AUDIO_DIR = Path("/home/ubuntu/questions_responses/audio")
TEST_AUDIO = "2017-03-09-AUDIO-00000177.opus"  # Verified working audio file
TEST_QUESTION_ID = "202017-03-09-091"  # Verified question ID

async def test_search(application: Application) -> bool:
    """Test search functionality with various test cases."""
    search_tests = [
        ("prière", ["priere", "prières"]),
        ("chabbât", ["chabbat", "chabat", "shabbat"]),
        ("bénédiction", ["benediction", "berakha"]),
        ("viande lait", ["viande", "lait"]),
        ("beth-din", ["beth din"])
    ]
    
    for search_term, expected_matches in search_tests:
        try:
            logger.info(f"\nTesting search term: {search_term}")
            message = await application.bot.send_message(
                chat_id=CHAT_ID,
                text=f"/search {search_term}",
                parse_mode='HTML'
            )
            logger.info(f"Search command sent: {message.text}")
            
            # Wait for response with timeout
            start_time = time.time()
            while time.time() - start_time < 30:
                updates = await application.bot.get_updates(timeout=1)
                for update in updates:
                    if (update.message and update.message.reply_to_message and 
                        update.message.reply_to_message.message_id == message.message_id):
                        response_text = update.message.text.lower()
                        logger.info(f"Received response: {response_text[:100]}...")
                        
                        # Verify all expected matches are found
                        matches_found = []
                        for match in expected_matches:
                            if match in response_text:
                                matches_found.append(match)
                                logger.info(f"Found match: {match}")
                            else:
                                logger.warning(f"Missing match: {match}")
                        
                        if len(matches_found) == len(expected_matches):
                            logger.info("All expected matches found")
                            break
                        else:
                            logger.error(f"Missing matches: {set(expected_matches) - set(matches_found)}")
                            return False
                            
                # Check for timeout
                if time.time() - start_time >= 30:
                    logger.error(f"Timeout waiting for response to search term: {search_term}")
                    return False
                await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"Error testing search term '{search_term}': {e}")
            return False
    
    return True

async def test_audio_playback(application: Application) -> bool:
    """Test direct audio file playback."""
    try:
        audio_path = AUDIO_DIR / TEST_AUDIO
        
        if not audio_path.exists():
            logger.error(f"Audio file not found: {audio_path}")
            return False
            
        logger.info(f"Testing audio file: {audio_path}")
        logger.info(f"File size: {audio_path.stat().st_size} bytes")
        
        # Try sending audio directly
        try:
            with open(audio_path, "rb") as audio:
                await application.bot.send_audio(
                    chat_id=CHAT_ID,
                    audio=audio,
                    filename=TEST_AUDIO,
                    title=f"Test Audio: {TEST_AUDIO}",
                    performer="Rav Abichid",
                    caption=f"Test audio file: {TEST_AUDIO}",
                    parse_mode='HTML'
                )
            logger.info("Audio sent successfully")
            return True
            
        except TelegramError as e:
            logger.error(f"Telegram error sending audio: {e}")
            return False
            
    except Exception as e:
        logger.error(f"Error in test: {e}")
        return False

async def cleanup_processes():
    """Clean up any existing bot processes."""
    logger.info("Cleaning up existing bot processes...")
    try:
        import psutil
        current_pid = os.getpid()
        
        # Kill any Python processes running bot.py
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.pid != current_pid:
                    cmdline = proc.cmdline()
                    if any('python' in cmd.lower() for cmd in cmdline) and any('bot.py' in cmd for cmd in cmdline):
                        logger.info(f"Killing bot process: {proc.pid}")
                        proc.terminate()
                        try:
                            proc.wait(timeout=5)
                        except psutil.TimeoutExpired:
                            proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
                
        # Additional cleanup using system commands
        os.system("pkill -f 'python.*bot.py'")
        await asyncio.sleep(5)  # Wait for processes to fully terminate
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")

async def verify_bot_connection(application: Application, max_retries: int = 3) -> bool:
    """Verify bot connection with retries."""
    for attempt in range(max_retries):
        try:
            # Delete webhook and clear updates
            await application.bot.delete_webhook(drop_pending_updates=True)
            await asyncio.sleep(2)
            
            # Test connection
            me = await application.bot.get_me()
            logger.info(f"Connected to bot: @{me.username}")
            return True
            
        except Exception as e:
            logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(5)
            continue
            
    return False

async def main():
    """Main test function."""
    try:
        # Clean up existing processes
        await cleanup_processes()
        
        # Initialize application with proper configuration
        application = (
            ApplicationBuilder()
            .token(BOT_TOKEN)
            .concurrent_updates(True)
            .connection_pool_size(8)
            .build()
        )
        
        # Verify bot connection
        if not await verify_bot_connection(application):
            logger.error("Failed to establish bot connection")
            return
        
        # Run test suite
        test_results = []
        
        try:
            # Test direct audio playback
            logger.info("\n=== Testing Audio Playback ===")
            if await test_audio_playback(application):
                logger.info("✓ Audio playback test passed")
                test_results.append(("Audio Playback", True))
            else:
                logger.error("❌ Audio playback test failed")
                test_results.append(("Audio Playback", False))
                return
            
            # Brief pause between tests
            await asyncio.sleep(2)
            
            # Test audio command
            logger.info("\n=== Testing Audio Command ===")
            command = f"/audio {TEST_QUESTION_ID}"
            message = await application.bot.send_message(
                chat_id=CHAT_ID,
                text=command,
                parse_mode='HTML'
            )
            logger.info(f"Command sent: {command}")
            
            # Wait for response with timeout
            start_time = time.time()
            response_received = False
            
            while time.time() - start_time < 30:
                try:
                    updates = await application.bot.get_updates(timeout=1)
                    for update in updates:
                        if (update.message and update.message.reply_to_message and 
                            update.message.reply_to_message.message_id == message.message_id):
                            if update.message.audio:
                                logger.info("✓ Audio command test passed")
                                test_results.append(("Audio Command", True))
                                response_received = True
                                break
                    if response_received:
                        break
                    await asyncio.sleep(1)
                except Exception as e:
                    if "Conflict: terminated by other getUpdates request" in str(e):
                        logger.warning("Update conflict detected, retrying...")
                        await asyncio.sleep(1)
                        continue
                    raise
            
            if not response_received:
                logger.error("❌ Audio command test failed: no response received")
                test_results.append(("Audio Command", False))
                return
            
            # Brief pause between tests
            await asyncio.sleep(2)
            
            # Test search functionality
            logger.info("\n=== Testing Search Functionality ===")
            if await test_search(application):
                logger.info("✓ Search functionality test passed")
                test_results.append(("Search", True))
            else:
                logger.error("❌ Search functionality test failed")
                test_results.append(("Search", False))
                return
            
            # Print test summary
            logger.info("\n=== Test Summary ===")
            for test_name, passed in test_results:
                status = "✓" if passed else "❌"
                logger.info(f"{status} {test_name}")
            
            logger.info("\n=== All Tests Completed Successfully ===")
            
        except Exception as e:
            logger.error(f"Error during test execution: {e}")
            return
        max_wait = 30  # 30 seconds timeout
        
        while time.time() - start_time < max_wait:
            try:
                updates = await application.bot.get_updates(timeout=1)
                for update in updates:
                    if (update.message and 
                        update.message.reply_to_message and 
                        update.message.reply_to_message.message_id == message.message_id):
                        
                        # Check for audio file
                        if update.message.audio:
                            logger.info(f"Received audio response: {update.message.audio.file_name}")
                            return
                            
                        # Check for error message
                        if update.message.text:
                            logger.error(f"Received error: {update.message.text}")
                            return
                            
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error getting updates: {e}")
                await asyncio.sleep(1)
                
        logger.error("No response received within timeout")
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
        raise
    finally:
        if 'application' in locals():
            await application.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
