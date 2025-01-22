import asyncio
import logging
from telegram.ext import ApplicationBuilder
from telegram import Update
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    try:
        app = ApplicationBuilder().token('7099400053:AAGpkQ978uhK1M3GnFwNoNH04QyNVb4ufsk').build()
        logger.info("Sending test command...")
        sent_message = await app.bot.send_message(chat_id='39557300', text='/start')
        logger.info("Test command sent successfully")

        # Wait for response with timeout
        start_time = time.time()
        timeout = 30  # 30 seconds timeout
        got_response = False

        while time.time() - start_time < timeout:
            try:
                # Get updates with the message we're waiting for
                updates = await app.bot.get_updates(offset=-1, timeout=1)
                for update in updates:
                    if (update.message and update.message.reply_to_message and 
                        update.message.reply_to_message.message_id == sent_message.message_id):
                        logger.info(f"Received response: {update.message.text}")
                        got_response = True
                        break
                if got_response:
                    break
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error getting updates: {e}")
                await asyncio.sleep(1)

        if not got_response:
            logger.error("No response received from bot within timeout")
            raise TimeoutError("Bot did not respond within 30 seconds")
        else:
            logger.info("Bot responded successfully to /start command")

    except Exception as e:
        logger.error(f"Error in test: {e}")
        raise
    finally:
        # Cleanup
        try:
            await app.stop()
            await app.shutdown()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

if __name__ == "__main__":
    asyncio.run(main())
