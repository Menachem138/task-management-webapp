import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def verify_environment():
    """Verify required environment variables are set."""
    logger.info("Checking environment variables...")
    
    test_chat_id = os.environ.get('TELEGRAM_TEST_CHAT_ID')
    logger.info(f"TELEGRAM_TEST_CHAT_ID={test_chat_id}")
    
    if not test_chat_id:
        logger.error("TELEGRAM_TEST_CHAT_ID is not set!")
        return False
        
    return True

if __name__ == "__main__":
    if not verify_environment():
        exit(1)
    logger.info("Environment verification completed successfully")
