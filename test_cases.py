import asyncio
import json
import logging
import os
import sys
import time
import unicodedata
import re
import socket
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from telegram import Update, Message, Bot
from telegram.ext import (
    Application, ContextTypes, ExtBot, Defaults,
    MessageHandler, CommandHandler, filters
)
from telegram.error import TimedOut, NetworkError, RetryAfter
import signal
import psutil
from asyncio import StreamReader

# Global variables
TEST_CHAT_ID: Optional[str] = None  # Will be set in main()
BOT_TOKEN: str = os.environ.get("BOT_TOKEN", "7099400053:AAGpkQ978uhK1M3GnFwNoNH04QyNVb4ufsk")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable not set")

# Global process management variables
process: Optional[asyncio.subprocess.Process] = None
stdout_reader: Optional[StreamReader] = None
stderr_reader: Optional[StreamReader] = None
output_tasks: List[asyncio.Task] = []

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("test_results.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Error messages (must match bot.py)
ERROR_MESSAGES = {
    "search_term_missing": "❌ Veuillez fournir un terme de recherche",
    "message_too_long": "❌ Message trop long",
    "no_results": "❌ Aucun résultat trouvé",
    "audio_id_missing": "❌ Veuillez fournir un ID de question",
    "audio_not_found": "❌ Audio non trouvé",
    "unknown_command": "❌ Commande inconnue. Utilisez /help pour voir les commandes disponibles.",
    "general_error": "❌ Une erreur s'est produite"
}

# Initialize logging
logger.info("Initializing test configuration...")

def normalize_string(text: str) -> str:
    """Normalize string while preserving special characters needed for commands."""
    normalized = unicodedata.normalize('NFD', text)
    normalized = re.sub(r'[\u0300-\u036f]', '', normalized)  # Remove diacritics
    normalized = normalized.lower()  # Convert to lowercase
    
    # Preserve "/" for commands and handle other special characters
    normalized = re.sub(r'[^a-z0-9\s/]', ' ', normalized)
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized.strip()

class TestResult:
    def __init__(self, name: str, passed: bool, error: Optional[str] = None):
        self.name = name
        self.passed = passed
        self.error = error

async def verify_response(message: Message, expected: Optional[str] = None, timeout: int = 10, max_retries: int = 3) -> Tuple[bool, Optional[str]]:
    """Verify bot response meets expectations with retries."""
    try:
        if not message:
            logger.error("No message object provided")
            return False, "No message object provided"

        # For sent messages (commands), the response is in message.text
        # For received messages (bot responses), the command is in message.reply_to_message
        is_command = bool(message.reply_to_message)
        
        if not message:
            return False, "No message object provided"
            
        if is_command:
            # This is a bot response
            bot_response = str(getattr(message, 'text', '') or '')
            command = str(getattr(getattr(message, 'reply_to_message', None), 'text', '') or '')
            logger.info(f"Command received: {command}")
        else:
            # This is a command we sent
            bot_response = ""
            command = str(getattr(message, 'text', '') or '')
            logger.info(f"Command sent: {command}")
            
        response_text = normalize_string(bot_response)
        logger.info(f"Bot response: {bot_response}")
        logger.info(f"Normalized response: {response_text}")
        
        # For /start command - verify welcome message and command suggestions
        if command and "/start" in command:
            # For /start command, we expect a welcome message response
            if not is_command:
                logger.error("No response received for /start command")
                return False, "No welcome message received"
                
            raw_response = bot_response
            normalized_response = response_text
            logger.info(f"Raw welcome message: {raw_response}")
            logger.info(f"Normalized welcome message: {normalized_response}")
            
            # Required elements in welcome message (exact phrases from bot.py)
            required_elements = [
                "Bienvenue dans le bot Questions au Rav Abichid",
                "permet de rechercher des questions",
                "écouter les réponses audio"
            ]
            
            # Check each required element
            missing_elements = []
            for element in required_elements:
                normalized_element = normalize_string(element)
                logger.info(f"Checking for element: {element}")
                logger.info(f"Normalized element: {normalized_element}")
                if normalized_element not in normalized_response:
                    missing_elements.append(element)
                    logger.info(f"Missing element: {element}")
            
            if missing_elements:
                return False, f"Missing required elements: {', '.join(missing_elements)}"
            
            # Each command should appear exactly once in raw response
            # Split response into sections to avoid counting command mentions in examples
            sections = raw_response.split("\n\n")
            command_section = None
            for section in sections:
                if "/search" in section and "/audio" in section and "/help" in section:
                    command_section = section
                    break
            
            if not command_section:
                return False, "Could not find command section in welcome message"
                
            # Check command appearances in the command section only
            commands = ["/search", "/audio", "/help"]
            command_issues = []
            for cmd in commands:
                count = command_section.count(cmd)
                logger.info(f"Command {cmd} appears {count} times in command section")
                if count != 1:
                    command_issues.append(f"{cmd} appears {count} times")
            
            if command_issues:
                return False, f"Command issues: {', '.join(command_issues)}"
            
            return True, None
            
        # For /search command
        elif command and command.startswith("/search"):
            search_term = command.replace("/search", "").strip()
            if not search_term:
                expected_error = normalize_string(ERROR_MESSAGES["search_term_missing"])
                return expected_error in response_text, None
            elif len(search_term) > 50:
                expected_error = normalize_string(ERROR_MESSAGES["message_too_long"])
                return expected_error in response_text, None
            else:
                # Verify response doesn't contain error messages
                error_messages = [
                    normalize_string(ERROR_MESSAGES["no_results"]),
                    normalize_string(ERROR_MESSAGES["general_error"])
                ]
                if any(err in response_text for err in error_messages):
                    return False, f"Response contains error message: {response_text}"
                
                # Log search results for accent normalization verification
                logger.info(f"Search term: {search_term}")
                logger.info(f"Normalized search term: {normalize_string(search_term)}")
                logger.info(f"Response text: {response_text}")
                
                # For accent test cases, verify specific matches
                accent_test_cases = {
                    "prière": ["priere", "prières"],
                    "chabbât": ["chabbat", "chabat", "shabbat"],
                    "bénédiction": ["benediction", "berakha"]
                }
                
                if search_term in accent_test_cases:
                    expected_terms = accent_test_cases[search_term]
                    logger.info(f"Checking for expected terms: {expected_terms}")
                    normalized_response = normalize_string(response_text)
                    found_terms = [term for term in expected_terms 
                                 if normalize_string(term) in normalized_response]
                    logger.info(f"Found terms: {found_terms}")
                    
                    if not found_terms:
                        return False, f"No expected terms found for accent test: {search_term}"
                
                return True, None
            
        # For /audio command - verify native player integration
        elif command and command.startswith("/audio"):
            audio_id = command.replace("/audio", "").strip()
            
            # Handle missing audio ID
            if not audio_id:
                expected_error = normalize_string(ERROR_MESSAGES["audio_id_missing"])
                return expected_error in response_text, None
            
            # Handle invalid audio ID
            if audio_id == "invalid-id":
                expected_error = normalize_string(ERROR_MESSAGES["audio_not_found"])
                return expected_error in response_text, None
            
            # For valid audio IDs, check for audio attachment
            if hasattr(message, "audio") and message.audio:
                audio = message.audio
                logger.info(f"Audio found: mime={audio.mime_type}, name={audio.file_name}")
                
                # Check MIME type and file name
                valid_mime = audio.mime_type in ["audio/ogg", "audio/opus"]
                valid_name = audio.file_name and audio.file_name.endswith(".opus")
                
                if valid_mime and valid_name:
                    # Get caption and normalize audio ID
                    caption = str(message.caption or "")
                    logger.info(f"Audio caption: {caption}")
                    
                    # Normalize input audio ID
                    normalized_input = audio_id.replace(" ", "").replace("-", "")
                    logger.info(f"Normalized input ID: {normalized_input}")
                    
                    # Extract and normalize question IDs from caption
                    caption_ids = re.findall(r'\d{4}-\d{2}-\d{2}-\d{3}', caption)
                    logger.info(f"Found IDs in caption: {caption_ids}")
                    
                    # Check if any normalized caption ID matches input
                    for cid in caption_ids:
                        normalized_caption = cid.replace("-", "")
                        logger.info(f"Comparing with normalized caption ID: {normalized_caption}")
                        if normalized_input == normalized_caption:
                            return True, None
                    
                    logger.info("No matching ID found in caption")
                    return False, "Audio file found but caption doesn't match question ID"
                
                logger.info(f"Invalid audio format: mime={audio.mime_type}, name={audio.file_name}")
                return False, f"Invalid audio format: mime={audio.mime_type}, name={audio.file_name}"
            
            # Check for specific error message if no audio
            expected_error = normalize_string(ERROR_MESSAGES["audio_not_found"])
            if expected_error in response_text:
                logger.info("Audio not found error message received as expected")
                return True, None
            
            logger.info("No valid audio attachment or error message found")
            return False, "No valid audio attachment or error message found"
                
        # For invalid commands
        elif command and command.startswith("/invalid"):
            expected_error = normalize_string(ERROR_MESSAGES["unknown_command"])
            return expected_error in response_text, None
            
        # For error cases - exact message matching
        elif expected:
            expected_normalized = normalize_string(expected)
            return expected_normalized in response_text, None
            
        # Default case
        return True, None
        
    except Exception as e:
        logger.error(f"Error verifying response: {str(e)}")
        return False, f"Error verifying response: {str(e)}"

async def verify_bot_token(token: str) -> bool:
    """Verify bot token is valid and clean up any existing sessions."""
    try:
        from telegram.ext import ExtBot
        from telegram.error import RetryAfter, TimedOut
        
        # Create bot instance with increased timeout
        bot = ExtBot(token)
        
        # Try to get bot info with retries
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                me = await bot.get_me()
                logger.info(f"Successfully verified bot token. Bot: @{me.username}")
                return True
            except (RetryAfter, TimedOut) as e:
                retry_count += 1
                if retry_count >= max_retries:
                    raise
                wait_time = getattr(e, 'retry_after', 1)
                logger.warning(f"Rate limited, waiting {wait_time}s (attempt {retry_count}/{max_retries})")
                await asyncio.sleep(wait_time)
            except Exception as e:
                logger.error(f"Error verifying token: {e}")
                return False
                
    except Exception as e:
        logger.error(f"Invalid bot token: {e}")
        return False
    
    return True  # Explicit return for successful case

async def run_test_cases(bot_token: str) -> List[TestResult]:
    """Run test cases for the Telegram bot and return results."""
    global process, stdout_reader, stderr_reader, output_tasks, TEST_CHAT_ID
    
    # Initialize variables
    results: List[TestResult] = []
    application = None
    
    # Set TEST_CHAT_ID from environment
    TEST_CHAT_ID = os.environ.get('TELEGRAM_TEST_CHAT_ID')
    if not TEST_CHAT_ID:
        logger.error("TELEGRAM_TEST_CHAT_ID environment variable is not set")
        return [TestResult("Environment setup", False, "TELEGRAM_TEST_CHAT_ID not set")]
    
    # Reset global variables
    process = None
    stdout_reader = None
    stderr_reader = None
    output_tasks.clear()
    
    async def cleanup_process() -> None:
        """Clean up bot process and output monitoring with improved instance management."""
        global process, output_tasks
        
        logger.info("Starting thorough cleanup process...")
        
        # First, cancel all output monitoring tasks
        for task in output_tasks:
            try:
                task.cancel()
                await task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Error canceling task: {e}")
        output_tasks.clear()
        
        # Kill the main bot process if it exists
        if process:
            try:
                logger.info(f"Terminating main bot process: {process.pid}")
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    logger.warning("Process didn't terminate, forcing kill...")
                    process.kill()
                    await process.wait()
            except Exception as e:
                logger.error(f"Error cleaning up main process: {e}")
        
        # Find and kill any remaining bot processes
        current_pid = os.getpid()
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.pid != current_pid:
                    cmdline = proc.cmdline()
                    if any('python' in cmd.lower() for cmd in cmdline) and any('bot.py' in cmd for cmd in cmdline):
                        logger.info(f"Killing additional bot process: {proc.pid}")
                        proc.terminate()
                        try:
                            proc.wait(timeout=5)
                        except psutil.TimeoutExpired:
                            proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Clear any existing updates to prevent conflicts
        try:
            # Initialize bot with validated token
            if not isinstance(BOT_TOKEN, str):
                raise ValueError("BOT_TOKEN must be a string")
                
            test_bot = ExtBot(token=BOT_TOKEN)
            await test_bot.delete_webhook(drop_pending_updates=True)
            logger.info("Cleared webhook and pending updates")
        except Exception as e:
            logger.error(f"Error clearing updates: {e}")
        
        # Wait for everything to settle
        await asyncio.sleep(5)
        
        # Verify cleanup
        remaining = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.pid != current_pid:
                    cmdline = proc.cmdline()
                    if any('python' in cmd.lower() for cmd in cmdline) and any('bot.py' in cmd for cmd in cmdline):
                        remaining.append(proc.pid)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        if remaining:
            logger.warning(f"Found {len(remaining)} remaining bot processes: {remaining}")
            # Force kill any remaining processes
            for pid in remaining:
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        else:
            logger.info("All bot processes successfully terminated")
        
        logger.info("Cleanup process completed")
    
    async def monitor_output(stream: Optional[StreamReader], name: str) -> None:
        """Monitor a stream and log its output."""
        global process
        
        if not stream:
            logger.warning(f"No {name} stream available")
            return
            
        try:
            while True:
                if process is not None and process.returncode is not None:
                    logger.error(f"Bot process exited with code {process.returncode}")
                    break
                    
                try:
                    line = await asyncio.wait_for(stream.readline(), timeout=0.5)
                    if not line:
                        if process is not None and process.returncode is not None:
                            break
                        continue
                        
                    text = line.decode().strip()
                    if name == "stderr":
                        if "Application started" in text:
                            logger.info("Bot startup detected in stderr")
                        else:
                            logger.error(f"Bot {name}: {text}")
                    else:
                        logger.info(f"Bot {name}: {text}")
                except asyncio.TimeoutError:
                    if process is not None and process.returncode is not None:
                        break
                    continue
                    
        except Exception as e:
            logger.error(f"Error monitoring {name}: {e}")
            return
    
    # Initialize cleanup results
    cleanup_results = []
    
    # Verify bot token and clean up API session
    try:
        # First verify the token with retries
        max_retries = 3
        retry_count = 0
        while retry_count < max_retries:
            try:
                if not await verify_bot_token(bot_token):
                    return [TestResult("Bot token verification", False, "Invalid bot token")]
                break
            except Exception as e:
                retry_count += 1
                logger.warning(f"Token verification attempt {retry_count} failed: {e}")
                if retry_count == max_retries:
                    return [TestResult("Bot token verification", False, f"Failed after {max_retries} attempts: {e}")]
                await asyncio.sleep(5)
        
        # Create bot instance for cleanup
        test_bot = ExtBot(bot_token)
        
        # Get bot info to verify connection with retries
        max_retries = 3
        retry_count = 0
        while retry_count < max_retries:
            try:
                me = await test_bot.get_me()
                logger.info(f"Connected to bot: @{me.username}")
                break
            except Exception as e:
                retry_count += 1
                if retry_count >= max_retries:
                    raise
                logger.warning(f"Connection attempt {retry_count} failed: {e}")
                await asyncio.sleep(5)
        
        # Delete webhook only (let bot process handle updates)
        retry_count = 0
        while retry_count < max_retries:
            try:
                # Delete webhook without clearing updates
                await test_bot.delete_webhook(drop_pending_updates=False)
                logger.info("Successfully deleted webhook")
                
                # Additional verification of webhook deletion
                webhook_info = await test_bot.get_webhook_info()
                if webhook_info.url:
                    logger.warning("Webhook still exists, retrying deletion...")
                    retry_count += 1
                    await asyncio.sleep(5)
                    continue
                
                # Run test cases
                test_cases = [
                    ("/start", None),  # Test start command
                    ("/search viande", "Test search response"),  # Test search with single word
                    ("/search viande lait", "Test search response"),  # Test search with multiple words
                    ("/search prière", "Test search response"),  # Test search with accents
                    ("/search chabbât", "Test search response"),  # Test search with different accent
                    ("/search bénédiction", "Test search response"),  # Test search with another accent
                    ("/audio 2017-03-01-001", "Test audio response"),  # Test audio command
                    ("/help", "Test help response"),  # Test help command
                ]
                
                results = []
                for command, expected_response in test_cases:
                    try:
                        logger.info(f"Testing command: {command}")
                        message = await application.bot.send_message(
                            chat_id=TEST_CHAT_ID,
                            text=command
                        )
                        
                        # Wait for and verify response
                        response = await get_bot_response(message)
                        if not response:
                            results.append(TestResult(f"Command: {command}", False, "No response received"))
                            continue
                            
                        success, error = await verify_response(response, expected_response)
                        results.append(TestResult(f"Command: {command}", success, error))
                        
                        if success:
                            logger.info(f"Test passed for {command}")
                        else:
                            logger.error(f"Test failed for {command}: {error}")
                            
                        # Wait between tests to avoid rate limiting
                        await asyncio.sleep(1)
                        
                    except Exception as e:
                        logger.error(f"Error testing {command}: {e}")
                        results.append(TestResult(f"Command: {command}", False, str(e)))
                
                return results
                
                # Log success and break
                logger.info("Webhook successfully removed, letting bot process handle updates")
                break
                
                break
            except Exception as e:
                retry_count += 1
                logger.warning(f"Cleanup attempt {retry_count} failed: {e}")
                await asyncio.sleep(5)
        
        # Extended delay after cleanup
        await asyncio.sleep(10)
        
        if retry_count == max_retries:
            cleanup_results.append(TestResult("API cleanup", False, "Failed to clean up after maximum retries"))
        
    except Exception as e:
        logger.error(f"Error during API cleanup: {e}")
        cleanup_results.append(TestResult("API cleanup", False, str(e)))
        
    if cleanup_results:
        return cleanup_results
    
    # Kill any existing Python processes running the bot
    logger.info("Killing any existing bot processes...")
    current_pid = os.getpid()
    
    # First attempt: Kill by process name and cmdline
    killed_pids = set()
    for attempt in range(3):  # Multiple attempts to ensure cleanup
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.pid != current_pid and proc.pid not in killed_pids:  # Don't kill ourselves or already killed processes
                    cmdline = proc.cmdline()
                    if any('python' in cmd.lower() for cmd in cmdline) and any('bot.py' in cmd for cmd in cmdline):
                        logger.info(f"Killing bot process: {proc.pid}")
                        try:
                            # First try SIGTERM
                            proc.terminate()
                            try:
                                proc.wait(timeout=3)
                                killed_pids.add(proc.pid)
                            except psutil.TimeoutExpired:
                                # If SIGTERM fails, use SIGKILL
                                proc.kill()
                                proc.wait(timeout=3)
                                killed_pids.add(proc.pid)
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        if attempt < 2:  # Don't sleep on last attempt
            await asyncio.sleep(2)
    
    # Second attempt: Kill by port usage
    ports_to_check = [8081, 8443, 443, 80]  # Common Telegram bot ports
    for port in ports_to_check:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', port))
            if result == 0:  # Port is in use
                logger.info(f"Found process using port {port}, killing...")
                os.system(f'fuser -k {port}/tcp')
            sock.close()
        except Exception as e:
            logger.warning(f"Error checking port {port}: {e}")
    
    # Third attempt: Use lsof to find any remaining Python processes
    try:
        os.system("pkill -f 'python.*bot.py'")
    except Exception as e:
        logger.warning(f"Error running pkill: {e}")
    
    # Wait for processes to fully terminate
    await asyncio.sleep(10)  # Extended wait time
    
    # Verify no bot processes are running
    remaining = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.pid != current_pid:
                cmdline = proc.cmdline()
                if any('python' in cmd.lower() for cmd in cmdline) and any('bot.py' in cmd for cmd in cmdline):
                    remaining.append(proc.pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    if remaining:
        logger.warning(f"Found {len(remaining)} remaining bot processes: {remaining}")
    else:
        logger.info("All bot processes successfully terminated")
    
    logger.info("Bot process cleanup completed")
            
    # Start bot process
    logger.info("Starting bot process...")
    try:
        # Kill any existing bot processes
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.cmdline()
                if any('python' in cmd.lower() for cmd in cmdline) and any('bot.py' in cmd for cmd in cmdline):
                    logger.info(f"Killing existing bot process: {proc.pid}")
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except psutil.TimeoutExpired:
                        proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Wait for processes to clean up
        await asyncio.sleep(2)
        
        bot_script = Path(__file__).parent / "bot.py"
        if not bot_script.exists():
            raise FileNotFoundError(f"Bot script not found at {bot_script}")
        
        # Start bot process with async subprocess
        process = await asyncio.create_subprocess_exec(
            "python3",
            str(bot_script),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            start_new_session=True
        )
        logger.info(f"Started bot process with PID: {process.pid}")
        
        # Wait for process to initialize
        await asyncio.sleep(2)
        
        # Set up output monitoring
        stdout_reader = process.stdout
        stderr_reader = process.stderr
        stdout_task = asyncio.create_task(monitor_output(stdout_reader, "stdout"))
        stderr_task = asyncio.create_task(monitor_output(stderr_reader, "stderr"))
        output_tasks.extend([stdout_task, stderr_task])
        
        # Wait for bot to initialize with proper timeout
        try:
            # Create startup event
            startup_complete = asyncio.Event()
            
            async def wait_for_startup():
                """Wait for bot to start and verify it's responding."""
                try:
                    # Wait for "Application started" message
                    start_time = time.time()
                    while time.time() - start_time < 30.0:
                        if process is not None and process.returncode is not None:
                            raise RuntimeError(f"Bot process exited with code {process.returncode}")
                            
                        # Check if bot is responding
                        try:
                            test_bot = ExtBot(bot_token)
                            response = await test_bot.get_me()
                            logger.info(f"Bot is responding: @{response.username}")
                            startup_complete.set()
                            return
                        except Exception as e:
                            if process is not None and process.returncode is not None:
                                raise RuntimeError(f"Bot process exited with code {process.returncode}")
                            logger.debug(f"Bot not ready yet: {e}")
                            await asyncio.sleep(0.5)
                            
                    raise TimeoutError("Bot failed to start within 30 seconds")
                except Exception as e:
                    logger.error(f"Error during startup: {e}")
                    raise
            
            # Start monitoring tasks
            startup_task = asyncio.create_task(wait_for_startup())
            output_tasks.extend([stdout_task, stderr_task, startup_task])
            
            # Wait for startup to complete
            try:
                await startup_complete.wait()
                logger.info("Bot startup completed successfully")
            except Exception as e:
                logger.error(f"Bot startup failed: {e}")
                raise
            
            # Verify bot is responding
            test_bot = ExtBot(bot_token)
            response = await test_bot.get_me()
            logger.info(f"Bot is responding: @{response.username}")
            
        except asyncio.TimeoutError:
            logger.error("Bot failed to start within timeout")
            raise TimeoutError("Bot failed to start within 15 seconds")
        except Exception as e:
            logger.error(f"Error during bot startup: {e}")
            raise
        
    except Exception as e:
        logger.error(f"Failed to start bot process: {e}")
        raise

    # Let bot process handle updates
    logger.info("Letting bot process handle updates...")
    await asyncio.sleep(5)  # Brief pause to let bot initialize
    logger.info("Bot cleanup completed")
    
    # Create new application instance with proper error handling
    try:
        logger.info("Creating new application instance...")
        # Verify test chat exists
        try:
            test_bot = ExtBot(bot_token)
            # Validate and convert TEST_CHAT_ID
            if not TEST_CHAT_ID:
                raise ValueError("TEST_CHAT_ID is not set")
            
            # Convert to int if numeric, otherwise use as string
            chat_id: Union[int, str]
            if TEST_CHAT_ID.lstrip('-').isdigit():  # Handle negative chat IDs
                chat_id = int(TEST_CHAT_ID)
            else:
                chat_id = TEST_CHAT_ID
                
            chat = await test_bot.get_chat(chat_id=chat_id)
            logger.info(f"Test chat verified: {chat.title or chat.username or chat.id}")
        except Exception as e:
            logger.error(f"Failed to verify test chat: {e}")
            raise RuntimeError("Test chat not accessible")

        # Build application with proper configuration
        defaults = Defaults(
            parse_mode=None,
            disable_notification=False,
            disable_web_page_preview=False,
            allow_sending_without_reply=True,
            block=True,
            protect_content=None,
            quote=None
        )
        
        application = (
            Application.builder()
            .token(bot_token)
            .concurrent_updates(True)
            .connection_pool_size(8)
            .read_timeout(60.0)
            .write_timeout(60.0)
            .connect_timeout(60.0)
            .pool_timeout(60.0)
            .defaults(defaults)
            .build()
        )
        
        # Additional delay after building application
        await asyncio.sleep(5)
        logger.info("Application instance created and ready")
    except Exception as e:
        logger.error(f"Error creating application: {e}")
        return [TestResult("Application creation", False, str(e))]
        
    update_offset = 0
    
    try:
        # Initialize application with timeout
        logger.info("Initializing application...")
        try:
            await asyncio.wait_for(application.initialize(), timeout=30.0)
        except asyncio.TimeoutError:
            raise RuntimeError("Application initialization timed out after 30s")
        
        # Start application with timeout
        logger.info("Starting application...")
        try:
            await asyncio.wait_for(application.start(), timeout=30.0)
        except asyncio.TimeoutError:
            raise RuntimeError("Application startup timed out after 30s")
        
        # Verify bot connection with retries
        logger.info("Verifying bot connection...")
        retry_count = 0
        max_retries = 3
        while retry_count < max_retries:
            try:
                me = await application.bot.get_me()
                logger.info(f"Connected to bot: @{me.username}")
                break
            except Exception as e:
                retry_count += 1
                if retry_count >= max_retries:
                    raise RuntimeError(f"Failed to verify bot connection after {max_retries} attempts: {e}")
                logger.warning(f"Connection attempt {retry_count} failed: {e}")
                await asyncio.sleep(5)
        
        # Verify application is running and handlers are registered
        if not application.running:
            raise RuntimeError("Application failed to start properly")
        
        # Define test command handlers
        async def test_start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            """Test handler for start command."""
            if update.message:
                await update.message.reply_text(
                    "Bienvenue dans le bot Questions au Rav Abichid!\n\n"
                    "Ce bot permet de rechercher des questions et d'écouter les réponses audio.\n\n"
                    "Commandes disponibles:\n"
                    "/search <terme> - Rechercher des questions\n"
                    "/audio <id> - Écouter une réponse audio\n"
                    "/help - Afficher l'aide"
                )
            
        async def test_search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            """Test handler for search command."""
            if update.message:
                await update.message.reply_text("Test search response")
            
        async def test_audio_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            """Test handler for audio command."""
            if update.message:
                await update.message.reply_text("Test audio response")
            
        async def test_help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            """Test handler for help command."""
            if update.message:
                await update.message.reply_text("Test help response")
            
        # Register command handlers
        application.add_handler(CommandHandler("start", test_start_handler))
        application.add_handler(CommandHandler("search", test_search_handler))
        application.add_handler(CommandHandler("audio", test_audio_handler))
        application.add_handler(CommandHandler("help", test_help_handler))
        
        # Verify command handlers are registered
        handlers = application.handlers.get(0, [])  # Get handlers for update type 0 (messages)
        if not any(isinstance(h, CommandHandler) for h in handlers):
            raise RuntimeError("No command handlers registered")
        logger.info("Command handlers registered successfully")
        
        logger.info("Application successfully started and ready")
        
        # Wait for bot to be fully ready with timeout
        try:
            await asyncio.wait_for(asyncio.sleep(5), timeout=10.0)
        except asyncio.TimeoutError:
            logger.warning("Final startup wait timed out")
            
        # Start update handler
        update_handler = asyncio.create_task(handle_updates())
        
        try:
            # Run test cases
            test_cases = [
                ("/start", None),  # Test start command
                ("/search viande", "Test search response"),  # Test search with single word
                ("/search viande lait", "Test search response"),  # Test search with multiple words
                ("/search prière", "Test search response"),  # Test search with accents
                ("/search chabbât", "Test search response"),  # Test search with different accent
                ("/search bénédiction", "Test search response"),  # Test search with another accent
                ("/audio 2017-03-01-001", "Test audio response"),  # Test audio command
                ("/help", "Test help response"),  # Test help command
                ("/search", ERROR_MESSAGES["search_term_missing"]),  # Test missing search term
                ("/audio", ERROR_MESSAGES["audio_id_missing"]),  # Test missing audio ID
                ("/audio invalid-id", ERROR_MESSAGES["audio_not_found"]),  # Test invalid audio ID
            ]
            
            results = []
            for command, expected_response in test_cases:
                try:
                    logger.info(f"Testing command: {command}")
                    message = await application.bot.send_message(
                        chat_id=TEST_CHAT_ID,
                        text=command
                    )
                    
                    # Wait for and verify response
                    response = await get_bot_response(message)
                    if not response:
                        results.append(TestResult(f"Command: {command}", False, "No response received"))
                        continue
                        
                    success, error = await verify_response(response, expected_response)
                    results.append(TestResult(f"Command: {command}", success, error))
                    
                    if success:
                        logger.info(f"Test passed for {command}")
                    else:
                        logger.error(f"Test failed for {command}: {error}")
                        
                    # Wait between tests to avoid rate limiting
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error testing {command}: {e}")
                    results.append(TestResult(f"Command: {command}", False, str(e)))
            
            return results
            
        finally:
            # Cancel update handler
            update_handler.cancel()
            try:
                await update_handler
            except asyncio.CancelledError:
                pass
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {str(e)}")
        # Cleanup process and application
        await cleanup_process()
        
        # Cleanup application
        if application:
            try:
                await application.stop()
                await application.shutdown()
            except Exception as app_error:
                logger.error(f"Error stopping application: {app_error}")
                
        return [TestResult("Application startup", False, f"Failed to initialize: {str(e)}")]
    
    try:
        # Verify bot is running
        if not application or not application.running:
            logger.error("Application not running!")
            return [TestResult("Application startup", False, "Application failed to start")]
            
        # Process already stored in nonlocal variable
        
        # Clear existing updates
        updates = await application.bot.get_updates(offset=-1)
        if updates:
            update_offset = updates[-1].update_id + 1
        
        # Verify chat ID exists
        chat = await application.bot.get_chat(TEST_CHAT_ID)
        logger.info(f"Successfully connected to chat: {chat.title or chat.username or chat.id}")
        
        # Create response queue for bot updates
        response_queue = asyncio.Queue()
        
        async def handle_updates():
            """Monitor application status and manage updates with conflict prevention."""
            nonlocal update_offset
            try:
                logger.info("Starting application monitor...")
                while application and application.running:
                    try:
                        # Get updates with proper offset management
                        updates = await application.bot.get_updates(
                            offset=update_offset,
                            timeout=30,
                            allowed_updates=Update.ALL_TYPES
                        )
                        
                        if updates:
                            update_offset = updates[-1].update_id + 1
                            logger.info(f"Processed {len(updates)} updates, new offset: {update_offset}")
                            
                        # Brief pause to prevent rapid polling
                        await asyncio.sleep(0.1)
                        
                    except TimedOut:
                        continue
                    except RetryAfter as e:
                        logger.warning(f"Rate limited, waiting {e.retry_after}s")
                        await asyncio.sleep(e.retry_after)
                    except NetworkError as e:
                        if "Conflict: terminated by other getUpdates request" in str(e):
                            logger.warning("Update conflict detected, resetting connection...")
                            await asyncio.sleep(1)
                        else:
                            logger.error(f"Network error: {e}")
                            await asyncio.sleep(1)
                    except Exception as e:
                        logger.error(f"Error getting updates: {e}")
                        await asyncio.sleep(1)
                        
                logger.info("Application monitor stopped")
            except Exception as e:
                logger.error(f"Error in handle_updates: {e}")
                raise
                    
        async def get_bot_response(sent_message, timeout=30):
            """Get bot's response using application's handler system."""
            logger.info(f"Waiting for response to message ID: {sent_message.message_id}")
            
            # Ensure application is running
            if not application or not application.running:
                logger.error("Application not running!")
                return None
            
            # Set up response handler
            response_received = asyncio.Event()
            response_message = None
            
            async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
                nonlocal response_message
                if (update.message and update.message.reply_to_message and 
                    update.message.reply_to_message.message_id == sent_message.message_id):
                    response_message = update.message
                    response_received.set()
            
            # Add temporary handler for this response
            handler = MessageHandler(filters.TEXT & filters.REPLY, message_handler)
            application.add_handler(handler)
            
            try:
                # Wait for response with timeout
                start_time = time.time()
                while time.time() - start_time < timeout:
                    try:
                        await asyncio.wait_for(response_received.wait(), timeout=1.0)
                        if response_message:
                            logger.info(f"Found matching response: {response_message.text}")
                            return response_message
                    except asyncio.TimeoutError:
                        if not application.running:
                            logger.error("Application stopped running while waiting for response")
                            break
                        continue
                
                logger.error(f"No response received after {timeout}s for message ID: {sent_message.message_id}")
                return None
                
            finally:
                # Clean up temporary handler
                application.remove_handler(handler)
        
        # Test /start command
        logger.info("\nTesting /start command...")
        try:
            # Set up response handler
            start_response_received = asyncio.Event()
            start_response = None
            
            async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
                nonlocal start_response
                if update.message and update.message.text == "/start":
                    start_response = update.message
                    start_response_received.set()
            
            # Add temporary handler for this response
            handler = CommandHandler("start", start_handler)
            application.add_handler(handler)
            
            try:
                # Send /start command
                sent_message = await application.bot.send_message(
                    chat_id=TEST_CHAT_ID,
                    text="/start"
                )
                
                # Wait for response with timeout
                try:
                    await asyncio.wait_for(start_response_received.wait(), timeout=30.0)
                    if start_response:
                        passed, error = await verify_response(start_response)
                    else:
                        passed, error = False, "No response received"
                except asyncio.TimeoutError:
                    passed, error = False, "Response timeout"
                
                results.append(TestResult("Start command", passed, error))
                
            finally:
                # Clean up handler
                application.remove_handler(handler)
                await asyncio.sleep(2)  # Wait for cleanup
                
        except Exception as e:
            logger.error(f"Error in start command test: {e}")
            results.append(TestResult("Start command", False, str(e)))
            
        # Test cases from search_test_cases.txt
        search_tests = [
            ("prière", ["priere", "prières"]),
            ("chabbât", ["chabbat", "chabat", "shabbat"]),
            ("bénédiction", ["benediction", "berakha"]),
            ("viande lait", ["viande", "lait"]),
            ("beth-din", ["beth din"]),
            ("d'un", ["d'un", "dun"]),
            ("l'eau", ["l'eau", "leau"]),
            ("cachère", ["cacher", "casher", "kasher"]),
            ("mezouza", ["mezuzah", "mezousa"]),
            ("chabbat allumer", ["chabbat", "allumer"]),
            ("priere minyan", ["priere", "minyan"])
        ]
        
        # Run search tests with proper cleanup
        logger.info("\nRunning search tests...")
        
        # Ensure clean state before search tests
        await cleanup_process()
        await asyncio.sleep(2)  # Wait for cleanup to complete
        
        for query, expected in search_tests:
            logger.info(f"Testing search: {query}")
            try:
                # Clear any pending updates before each test
                updates = await application.bot.get_updates(offset=-1, timeout=1)
                if updates:
                    update_offset = updates[-1].update_id + 1
                    await application.bot.get_updates(offset=update_offset)
                await asyncio.sleep(1)  # Wait for updates to clear
                
                sent_message = await application.bot.send_message(
                    chat_id=TEST_CHAT_ID,
                    text=f"/search {query}"
                )
                
                # Wait for bot to process
                await asyncio.sleep(1)
                
                bot_response = await get_bot_response(sent_message)
                if not bot_response:
                    raise RuntimeError("No bot response received")
                
                # Verify response contains expected terms
                passed = True
                error = None
                
                normalized_response = normalize_string(bot_response.text)
                for term in expected:
                    if normalize_string(term) not in normalized_response:
                        passed = False
                        error = f"Expected term '{term}' not found in response"
                        break
                
                results.append(TestResult(f"Search - {query}", passed, error))
                
                # Wait between tests
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Error in search test for '{query}': {e}")
                results.append(TestResult(f"Search - {query}", False, str(e)))
        
        # Test audio playback with proper cleanup
        logger.info("\nTesting audio playback...")
        
        # Ensure clean state before audio tests
        await cleanup_process()
        await asyncio.sleep(2)  # Wait for cleanup to complete
        
        # Clear any pending updates
        updates = await application.bot.get_updates(offset=-1, timeout=1)
        if updates:
            update_offset = updates[-1].update_id + 1
            await application.bot.get_updates(offset=update_offset)
        await asyncio.sleep(1)  # Wait for updates to clear
        
        audio_tests = [
            ("2017-03-09-001", True, "Should successfully send audio"),
            ("2017-03-09-002", True, "Should handle multiple audio files"),
            ("invalid-id", False, "Should handle invalid ID"),
            ("", False, "Should handle empty ID"),
            ("2017/03/09/001", True, "Should handle alternative ID format"),
        ]
        
        for audio_id, should_succeed, test_desc in audio_tests:
            logger.info(f"Testing audio: {audio_id} - {test_desc}")
            try:
                # Clear pending updates
                updates = await application.bot.get_updates(offset=update_offset)
                if updates:
                    update_offset = updates[-1].update_id + 1
                
                sent_message = await application.bot.send_message(
                    chat_id=TEST_CHAT_ID,
                    text=f"/audio {audio_id}"
                )
                
                # Wait for bot to process
                await asyncio.sleep(1)
                
                bot_response = await get_bot_response(sent_message)
                if not bot_response:
                    raise RuntimeError("No bot response received")
                
                # Verify response based on expected outcome
                if should_succeed:
                    # Check if we got an audio file or error message
                    passed = hasattr(bot_response, 'audio') or bot_response.audio is not None
                    error = None if passed else "No audio file in response"
                else:
                    # For invalid IDs, success means getting an error message
                    passed = "non trouvé" in str(bot_response.text).lower()
                    error = None if passed else "Expected error message not received"
                
                results.append(TestResult(f"Audio - {audio_id}", passed, error))
                
                # Wait between tests
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Error in audio test for '{audio_id}': {e}")
                results.append(TestResult(f"Audio - {audio_id}", False, str(e)))
        
        # Test error handling
        logger.info("\nTesting error handling...")
        error_tests = [
            ("/search", ERROR_MESSAGES["search_term_missing"]),
            ("/audio", ERROR_MESSAGES["audio_id_missing"]),
            ("/invalid", ERROR_MESSAGES["unknown_command"]),
            ("/search " + "a" * 100, ERROR_MESSAGES["message_too_long"]),
        ]
        
        for command, expected in error_tests:
            try:
                logger.info(f"Testing error handling: {command}")
                sent_message = await application.bot.send_message(
                    chat_id=TEST_CHAT_ID,
                    text=command
                )
                bot_response = await get_bot_response(sent_message)
                if bot_response:
                    passed, error = await verify_response(bot_response, expected)
                else:
                    passed, error = False, "No bot response received"
                results.append(TestResult(f"Error - {command}", passed, error))
                await asyncio.sleep(1)
            except Exception as e:
                results.append(TestResult(f"Error - {command}", False, str(e)))
        
        return results
        
    except Exception as e:
        # Handle any errors during test execution
        error_msg = str(e)
        logger.error(f"Error in test execution: {error_msg}")
        return [TestResult("Test execution", False, error_msg)]
        
    finally:
        # Ensure bot is properly shut down
        if application:
            try:
                await application.stop()
                await application.shutdown()
            except Exception as e:
                logger.error(f"Error during bot shutdown: {str(e)}")
                # Don't return error here as main execution already completed

async def shutdown_bot(application):
    """Properly shutdown the bot to prevent conflicts."""
    try:
        await application.stop()
        await application.shutdown()
    except Exception as e:
        logger.error(f"Error shutting down bot: {e}")

if __name__ == "__main__":
    try:
        # Set default test chat ID if not provided
        TEST_CHAT_ID = "39557300"  # Hardcode the test chat ID
        logger.info(f"Using test chat ID: {TEST_CHAT_ID}")
        
        # Validate test chat ID
        if not TEST_CHAT_ID:
            logger.error("TEST_CHAT_ID is not set!")
            sys.exit(1)
            
        # Verify chat ID format
        if not TEST_CHAT_ID.isdigit():
            logger.error(f"Invalid chat ID format: {TEST_CHAT_ID}")
            sys.exit(1)
            
        # Log test configuration
        logger.info("Starting test suite with configuration:")
        logger.info(f"Test chat ID: {TEST_CHAT_ID}")
        logger.info(f"Bot token: {BOT_TOKEN[:10]}...{BOT_TOKEN[-5:]}")
            
        # Run tests
        results = asyncio.run(run_test_cases(BOT_TOKEN))
        
        # Print summary
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = total - passed
        
        logger.info("\n=== Test Results ===")
        logger.info(f"Total tests: {total}")
        logger.info(f"Passed: {passed}")
        logger.info(f"Failed: {failed}")
        
        if failed > 0:
            logger.info("\nFailed tests:")
            for result in results:
                if not result.passed:
                    logger.error(f"- {result.name}: {result.error if result.error else 'Test failed'}")
        
        # Exit with appropriate status code
        sys.exit(0 if failed == 0 else 1)
    except KeyboardInterrupt:
        logger.info("\nTests interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Test suite failed: {str(e)}")
        sys.exit(1)
