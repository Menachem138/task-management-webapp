import asyncio
import logging
import os
import pytest
from typing import AsyncGenerator, List, Tuple
from telegram import Bot, Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)
from telegram.error import TelegramError
import nest_asyncio

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

# Import bot handlers
from bot import (
    search,
    audio,
    start,
    help_command,
    error_handler,
    unknown_command
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("test_search.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Constants
BOT_TOKEN = os.environ.get("BOT_TOKEN", "7099400053:AAGpkQ978uhK1M3GnFwNoNH04QyNVb4ufsk")
CHAT_ID = os.environ.get("TELEGRAM_TEST_CHAT_ID", "39557300")

# Test cases
SEARCH_TEST_CASES = [
    ("viande", True),  # Basic word
    ("chabbat", True),  # Word with variations
    ("viande lait", True),  # Multi-word search
    ("prière", True),  # Accented word
    ("bénédiction", True),  # Another accented word
    ("cacher", True),  # Word with synonyms
    ("invalid_term_xyz", False),  # Invalid search term
]

@pytest.fixture(scope="function")
async def test_bot() -> AsyncGenerator[Application, None]:
    """Fixture that provides a configured test bot application."""
    # Initialize application
    application = None
    try:
        application = (
            ApplicationBuilder()
            .token(BOT_TOKEN)
            .concurrent_updates(True)
            .connection_pool_size(8)
            .read_timeout(30.0)
            .write_timeout(30.0)
            .connect_timeout(30.0)
            .pool_timeout(30.0)
            .build()
        )
        
        # Add command handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("search", search))
        application.add_handler(CommandHandler("audio", audio))
        
        # Add error handler
        application.add_error_handler(error_handler)
        
        # Add unknown command handler
        application.add_handler(MessageHandler(filters.COMMAND, unknown_command))
        
        # Initialize and start application
        await application.initialize()
        await application.start()
        
        # Clear any pending updates
        await application.bot.delete_webhook(drop_pending_updates=True)
        await asyncio.sleep(1)
        
        # Verify bot connection
        me = await application.bot.get_me()
        logger.info(f"Connected to bot: @{me.username}")
        
        yield application
        
    except Exception as e:
        logger.error(f"Error setting up test bot: {e}")
        raise
        
    finally:
        # Cleanup
        if application:
            try:
                if application.running:
                    await application.stop()
                await application.shutdown()
                logger.info("Test bot stopped and cleaned up")
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")
                # Don't raise here to allow other cleanup to proceed

async def wait_for_search_response(application: Application, message_id: int, search_term: str, timeout: int = 30) -> bool:
    """Wait for search results containing the search term with improved validation."""
    start_time = asyncio.get_event_loop().time()
    update_offset = 0
    
    # Split search term into keywords for validation
    keywords = [k.lower() for k in search_term.split() if len(k) >= 2]
    if not keywords:
        logger.error("No valid keywords to search for")
        return False
    
    while asyncio.get_event_loop().time() - start_time < timeout:
        try:
            updates = await application.bot.get_updates(
                offset=update_offset,
                timeout=1,
                allowed_updates=["message"]
            )
            
            for update in updates:
                update_offset = update.update_id + 1
                
                if update.message and update.message.reply_to_message:
                    if update.message.reply_to_message.message_id == message_id:
                        response_text = update.message.text
                        if not response_text:
                            logger.warning("Received empty response")
                            continue
                            
                        logger.info(f"Found response: {response_text[:100]}...")
                        
                        # Validate response format
                        if "❌" in response_text:
                            logger.info("Received error response")
                            return False
                            
                        # Count number of results (look for audio command patterns)
                        audio_commands = response_text.count("/audio")
                        if audio_commands > 5:
                            logger.error(f"Too many results: {audio_commands} > 5")
                            return False
                            
                        # Check for highlighted terms
                        highlighted_terms = []
                        for keyword in keywords:
                            if f"*{keyword}*" in response_text.lower():
                                highlighted_terms.append(keyword)
                                
                        # Validate search results
                        if highlighted_terms:
                            logger.info(f"✓ Found highlighted terms: {highlighted_terms}")
                            logger.info(f"✓ Number of results: {audio_commands}")
                            return True
                        else:
                            logger.warning(f"No highlighted terms found for keywords: {keywords}")
                            
                        # If we got here, we found a response but it didn't meet our criteria
                        return False
            
            await asyncio.sleep(0.5)
            
        except asyncio.TimeoutError:
            logger.warning("Timeout getting updates, retrying...")
            continue
        except Exception as e:
            logger.error(f"Error getting updates: {e}")
            await asyncio.sleep(1)
    
    logger.error(f"Timeout waiting for response after {timeout}s")
    return False

@pytest.mark.asyncio
@pytest.mark.parametrize("search_term,should_pass", SEARCH_TEST_CASES)
async def test_search(test_bot: Application, search_term: str, should_pass: bool) -> None:
    """Test the /search command with various test cases."""
    try:
        logger.info(f"Testing search for term: {search_term}")
        
        # Send search command
        message = await test_bot.bot.send_message(
            chat_id=CHAT_ID,
            text=f"/search {search_term}"
        )
        logger.info(f"Sent search command (message_id: {message.message_id})")
        
        # Wait for response with retries
        max_retries = 3
        retry_count = 0
        result = False
        
        while retry_count < max_retries and not result:
            try:
                result = await wait_for_search_response(test_bot, message.message_id, search_term)
                if result:
                    break
            except Exception as e:
                logger.warning(f"Attempt {retry_count + 1} failed: {e}")
            retry_count += 1
            if retry_count < max_retries:
                await asyncio.sleep(2)  # Wait before retry
        
        if should_pass:
            assert result, f"Search test failed for '{search_term}' after {retry_count} attempts"
            logger.info(f"✓ Search test passed for '{search_term}'")
        else:
            assert not result, f"Search test unexpectedly passed for '{search_term}'"
            logger.info(f"✓ Search test correctly failed for invalid term '{search_term}'")
            
    except Exception as e:
        logger.error(f"Error in test: {e}")
        raise

@pytest.mark.asyncio
@pytest.mark.parametrize("audio_id,should_pass", [
    ("2017-03-01-022", True),  # Valid audio file
    ("2017-03-09-177", True),  # Another valid audio file
    ("invalid-id", False),  # Invalid ID
])
async def test_audio(test_bot: Application, audio_id: str, should_pass: bool) -> None:
    """Test the /audio command with various test cases."""
    try:
        logger.info(f"Testing audio for ID: {audio_id}")
        
        # Send audio command
        message = await test_bot.bot.send_message(
            chat_id=CHAT_ID,
            text=f"/audio {audio_id}"
        )
        logger.info(f"Sent audio command (message_id: {message.message_id})")
        
        # Wait for response
        start_time = asyncio.get_event_loop().time()
        update_offset = 0
        found_audio = False
        
        while asyncio.get_event_loop().time() - start_time < 30:  # 30s timeout
            try:
                updates = await test_bot.bot.get_updates(offset=update_offset, timeout=1)
                
                for update in updates:
                    update_offset = update.update_id + 1
                    
                    if update.message:
                        if update.message.audio or (update.message.document and 
                            update.message.document.mime_type == "audio/opus"):
                            found_audio = True
                            logger.info(f"✓ Found audio response for ID '{audio_id}'")
                            break
                        elif "erreur" in update.message.text.lower():
                            found_audio = False
                            logger.info(f"✗ Error response for ID '{audio_id}': {update.message.text}")
                            break
                
                if found_audio:
                    break
                    
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error getting updates: {e}")
                await asyncio.sleep(1)
        
        if should_pass:
            assert found_audio, f"Audio test failed for ID '{audio_id}'"
            logger.info(f"✓ Audio test passed for ID '{audio_id}'")
        else:
            assert not found_audio, f"Audio test unexpectedly passed for invalid ID '{audio_id}'"
            logger.info(f"✓ Audio test correctly failed for invalid ID '{audio_id}'")
            
    except Exception as e:
        logger.error(f"Error in test: {e}")
        raise
