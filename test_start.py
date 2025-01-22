import asyncio
import logging
import os
import sys
from telegram import Bot
from telegram.error import TelegramError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("test_start.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Constants
BOT_TOKEN = os.environ.get("BOT_TOKEN", "7099400053:AAGpkQ978uhK1M3GnFwNoNH04QyNVb4ufsk")
CHAT_ID = os.environ.get("TELEGRAM_TEST_CHAT_ID", "39557300")

async def wait_for_bot_response(bot: Bot, sent_message_id: int, timeout: int = 30) -> bool:
    """Wait for bot response to a specific message."""
    start_time = asyncio.get_event_loop().time()
    update_offset = 0
    
    while asyncio.get_event_loop().time() - start_time < timeout:
        try:
            updates = await bot.get_updates(offset=update_offset, timeout=1)
            
            for update in updates:
                logger.info(f"Processing update {update.update_id}")
                if update.message and update.message.text:
                    logger.info(f"Message: {update.message.text}")
                    # Check for welcome message in any case variation
                    if any(word in update.message.text.lower() 
                          for word in ["bienvenue", "welcome", "bonjour"]):
                        logger.info("✓ Found welcome message")
                        return True
                update_offset = update.update_id + 1
            
            await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"Error getting updates: {e}")
            await asyncio.sleep(1)
    
    return False

async def test_start() -> bool:
    """Test the /start command."""
    try:
        # Initialize bot
        bot = Bot(token=BOT_TOKEN)
        logger.info("Bot initialized")
        
        # Send /start command
        message = await bot.send_message(
            chat_id=CHAT_ID,
            text="/start"
        )
        logger.info(f"Sent /start command (message_id: {message.message_id})")
        
        # Wait for response
        if await wait_for_bot_response(bot, message.message_id):
            logger.info("✓ Start command test passed")
            return True
            
        logger.error("✗ Start command test failed - no welcome message received")
        return False
        
    except Exception as e:
        logger.error(f"Error in test: {e}")
        return False

def main():
    """Run the test."""
    try:
        # Run the test
        success = asyncio.run(test_start())
        
        if not success:
            logger.error("Test failed")
            sys.exit(1)
            
        logger.info("Test completed successfully")
        
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Test failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
