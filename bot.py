#!/usr/bin/env python3
import asyncio
import aiofiles
import json
import logging
import os
import re
import unicodedata
from pathlib import Path
from typing import List, Optional, Tuple, Dict

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)

# Import synonyms dictionary
SYNONYMS: Dict[str, List[str]] = {
    "chabbat": ["chabat", "shabbat", "shabat", "שבת"],
    "pessah": ["pessach", "pesach", "פסח"],
    "souccot": ["succot", "sukkot", "סוכות"],
    "pourim": ["purim", "פורים"],
    "viande": ["viandes", "basar", "bassar", "בשר"],
    "cacher": ["casher", "kasher", "cachère", "kashrout", "cacherout", "כשר"],
    "lait": ["halavi", "halav", "חלב"],
    "parve": ["pareve", "parvé", "parêve", "פרווה"],
    "priere": ["prière", "tefila", "תפילה"],
    "benediction": ["bénédiction", "berakha", "bracha", "ברכה"],
    "mezouza": ["mezuzah", "מזוזה"],
    "mitsva": ["mitsvah", "mitzvah", "מצווה"],
    "halakha": ["halacha", "הלכה"],
    "torah": ["tora", "תורה"]
}

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Error messages
ERROR_MESSAGES = {
    "search_term_missing": "❌ Veuillez fournir un terme de recherche",
    "message_too_long": "❌ Message trop long",
    "no_results": "❌ Aucun résultat trouvé",
    "audio_id_missing": "❌ Veuillez fournir un ID de question",
    "audio_not_found": "❌ Audio non trouvé",
    "unknown_command": "❌ Commande inconnue. Utilisez /help pour voir les commandes disponibles.",
    "general_error": "❌ Une erreur s'est produite"
}

# Bot configuration
BOT_TOKEN = os.environ.get("BOT_TOKEN", "7099400053:AAGpkQ978uhK1M3GnFwNoNH04QyNVb4ufsk")  # Use environment variable with fallback
QUESTIONS_DIR = Path("/home/ubuntu/questions_responses/questions")
AUDIO_DIR = Path("/home/ubuntu/questions_responses/audio")
MAPPING_FILE = QUESTIONS_DIR / "mapping.json"

# Log token configuration
logger.info("Using bot token from: " + ("environment" if "BOT_TOKEN" in os.environ else "default"))

def normalize_string(text: str) -> str:
    """Port of frontend normalizeString() function with improved accent handling."""
    # First normalize unicode characters
    normalized = unicodedata.normalize('NFD', text)
    # Remove combining diacritical marks while preserving special characters
    normalized = re.sub(r'[\u0300-\u036f]', '', normalized)
    # Convert to lowercase
    normalized = normalized.lower()
    # Replace special chars with space while preserving Hebrew characters
    normalized = re.sub(r'[^a-z0-9\s\u0590-\u05FF]', ' ', normalized)
    # Normalize spaces
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized.strip()

def get_word_variations(word: str) -> List[str]:
    """Get all variations of a word including synonyms."""
    normalized = normalize_string(word)
    variations = {normalized}
    
    # Check in keys and values of synonyms
    for key, values in SYNONYMS.items():
        if normalized == normalize_string(key) or any(normalize_string(v) == normalized for v in values):
            variations.update([key] + values)
    
    return list(variations)

def calculate_search_score(text: str, keywords: List[str]) -> Tuple[int, List[str]]:
    """Calculate search relevance score and matched terms with synonym support."""
    normalized_text = normalize_string(text)
    matches = []
    score = 0
    
    for keyword in keywords:
        if len(keyword) < 2:
            continue
            
        # Get all variations of the keyword
        variations = get_word_variations(keyword)
        matched = False
        
        for variation in variations:
            if normalize_string(variation) in normalized_text:
                if not matched:  # Only count score once per keyword
                    score += 1
                    matched = True
                matches.append(variation)
    
    return score, matches

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    if not update.effective_chat or not update.message:
        logger.error("Start command received without proper context")
        return

    welcome_message = (
        "Bienvenue dans le bot Questions au Rav Abichid!\n\n"
        "Ce bot permet de rechercher des questions et d'écouter les réponses audio.\n\n"
        "Commandes:\n"
        "/search <terme> - Rechercher une question\n"
        "/audio <id> - Écouter la réponse\n"
        "/help - Aide"
    )
    
    try:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=welcome_message,
            reply_to_message_id=update.message.message_id
        )
        logger.info(f"New user started bot: {update.effective_chat.id}")
    except Exception as e:
        logger.error(f"Error sending start message: {e}")
        await error_handler(update, context)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    if not update.effective_chat or not update.message:
        logger.error("Help command received without proper context")
        return

    help_text = (
        "🔍 /search <terme> - Rechercher une question (ex: chabbat, viande)\n"
        "🎵 /audio <id> - Écouter la réponse audio\n\n"
        "La recherche ignore les accents et la casse.\n"
        "Pour de meilleurs résultats, utilisez des mots-clés précis."
    )
    
    try:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=help_text,
            reply_to_message_id=update.message.message_id
        )
    except Exception as e:
        logger.error(f"Error sending help message: {e}")
        await error_handler(update, context)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors."""
    logger.error(f"Update {update} caused error {context.error}")
    
    try:
        if isinstance(update, Update) and update.effective_chat and update.message:
            error_message = "❌ Message trop long" if "Message too long" in str(context.error) else "❌ Une erreur s'est produite"
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=error_message,
                    reply_to_message_id=update.message.message_id
                )
            except Exception as send_error:
                logger.error(f"Error sending error message: {send_error}")
    except Exception as e:
        logger.error(f"Error in error handler: {e}")

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle unknown commands."""
    if not update.effective_chat or not update.message:
        logger.error("Unknown command received without proper context")
        return
        
    try:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Commande inconnue. Utilisez /help pour voir les commandes disponibles.",
            reply_to_message_id=update.message.message_id
        )
    except Exception as e:
        logger.error(f"Error sending unknown command message: {e}")
        await error_handler(update, context)

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /search command."""
    if not update.effective_message:
        logger.error("Search command received without message")
        return

    if not context.args:
        await update.effective_message.reply_text(ERROR_MESSAGES["search_term_missing"])
        return

    query = " ".join(context.args)
    if len(query) > 50:
        await update.effective_message.reply_text(ERROR_MESSAGES["message_too_long"])
        return

    try:
        with open(MAPPING_FILE) as f:
            data = json.load(f)
            questions = data.get("questions", [])

        # Split query into keywords and filter out short terms
        keywords = [k for k in query.split() if len(k) >= 2]
        if not keywords:
            await update.effective_message.reply_text("❌ Veuillez entrer au moins un mot-clé de 2 caractères minimum")
            return

        # Search with scoring
        scored_results = []
        for q in questions:
            text = f"{q['question']} {q['author']} {q['date']}"
            score, matches = calculate_search_score(text, keywords)
            if score > 0:
                scored_results.append((q, score, matches))
        
        # Sort by score (highest first)
        scored_results.sort(key=lambda x: x[1], reverse=True)
        results = [r[0] for r in scored_results]

        if not results:
            await update.effective_message.reply_text(ERROR_MESSAGES["no_results"])
            return

        # Format and send results (limit to first 5)
        for q in results[:5]:
            # Get score and matches for this result
            _, matches = calculate_search_score(
                f"{q['question']} {q['author']} {q['date']}", 
                keywords
            )
            
            # Format matches for display
            match_text = "Termes trouvés: " + ", ".join(matches) if matches else ""
            
            response = (
                f"{q['date']} - {q['author']}\n\n"
                f"{q['question']}\n\n"
                f"{len(q['audio_files'])} réponse(s) audio\n"
                f"ID: {q['id']}\n"
                f"{match_text}"
            )
            await update.effective_message.reply_text(response)

        if len(results) > 5:
            await update.effective_message.reply_text(f"\n... et {len(results) - 5} autres résultats")

    except Exception as e:
        logger.error(f"Error in search: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=ERROR_MESSAGES["general_error"],
            reply_to_message_id=update.message.message_id
        )

async def audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /audio command with improved error handling."""
    if not update.effective_chat or not update.message:
        logger.error("Audio command received without proper context")
        return

    try:
        if not context.args:
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=ERROR_MESSAGES["audio_id_missing"],
                    reply_to_message_id=update.message.message_id
                )
            except Exception as e:
                logger.error(f"Error sending missing ID message: {e}")
            return

        # Join all args to handle IDs with spaces
        question_id = " ".join(context.args)
        # Remove spaces and hyphens for comparison
        normalized_id = question_id.replace(" ", "").replace("-", "")
        logger.info(f"Processing audio request for ID: {question_id} (normalized: {normalized_id})")

        # Load questions data
        try:
            with open(MAPPING_FILE) as f:
                data = json.load(f)
                questions = data.get("questions", [])
        except Exception as e:
            logger.error(f"Error loading mapping file: {e}")
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=ERROR_MESSAGES["general_error"],
                    reply_to_message_id=update.message.message_id
                )
            except Exception as send_error:
                logger.error(f"Error sending error message: {send_error}")
            return

        # Find matching question
        question = next((q for q in questions if q["id"].replace("-", "") == normalized_id), None)
        if not question or not question["audio_files"]:
            logger.info(f"No audio found for ID: {question_id}")
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=ERROR_MESSAGES["audio_not_found"],
                    reply_to_message_id=update.message.message_id
                )
            except Exception as send_error:
                logger.error(f"Error sending not found message: {send_error}")
            return

        # Get audio file path
        audio_file = question["audio_files"][0]
        audio_path = AUDIO_DIR / audio_file
        logger.info(f"Audio file path: {audio_path}")

        if not audio_path.exists():
            logger.error(f"Audio file not found: {audio_path}")
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=ERROR_MESSAGES["audio_not_found"],
                    reply_to_message_id=update.message.message_id
                )
            except Exception as send_error:
                logger.error(f"Error sending not found message: {send_error}")
            return

        try:
            # Check file size (Telegram limit is 50MB)
            file_size = audio_path.stat().st_size
            if file_size > 50 * 1024 * 1024:  # 50MB in bytes
                try:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text="❌ Fichier audio trop volumineux (limite: 50MB)",
                        reply_to_message_id=update.message.message_id
                    )
                except Exception as send_error:
                    logger.error(f"Error sending file too large message: {send_error}")
                return

            # Verify file is valid opus
            if not audio_file.endswith('.opus'):
                logger.error(f"Invalid audio format: {audio_file}")
                try:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text="❌ Format audio invalide",
                        reply_to_message_id=update.message.message_id
                    )
                except Exception as send_error:
                    logger.error(f"Error sending invalid format message: {send_error}")
                return

            # Open and send file with proper context management
            async with aiofiles.open(audio_path, "rb") as audio_file_handle:
                audio_data = await audio_file_handle.read()
                
                # First try sending as audio
                try:
                    await context.bot.send_audio(
                        chat_id=update.effective_chat.id,
                        audio=audio_data,
                        filename=audio_file,
                        caption=f"Réponse audio pour la question {question['id']}",
                        title=f"Question {question['id']}",
                        performer="Rav Abichid",
                        reply_to_message_id=update.message.message_id
                    )
                    logger.info(f"Successfully sent as audio for question {question_id}")
                except Exception as e:
                    logger.warning(f"Failed to send as audio, trying as document: {e}")
                    # If audio fails, try sending as document
                    await context.bot.send_document(
                        chat_id=update.effective_chat.id,
                        document=audio_data,
                        filename=audio_file,
                        caption=f"Réponse audio pour la question {question['id']}",
                        reply_to_message_id=update.message.message_id
                    )
                    logger.info(f"Successfully sent as document for question {question_id}")
                    
        except FileNotFoundError:
            logger.error(f"Audio file not found: {audio_path}")
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=ERROR_MESSAGES["audio_not_found"],
                    reply_to_message_id=update.message.message_id
                )
            except Exception as send_error:
                logger.error(f"Error sending not found message: {send_error}")
        except Exception as e:
            logger.error(f"Error handling audio file: {e}")
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=ERROR_MESSAGES["general_error"],
                    reply_to_message_id=update.message.message_id
                )
            except Exception as send_error:
                logger.error(f"Error sending error message: {send_error}")

    except Exception as e:
        logger.error(f"Error in audio command: {e}")
        try:
            if update.effective_chat and update.message:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=ERROR_MESSAGES["general_error"],
                    reply_to_message_id=update.message.message_id
                )
        except Exception as send_error:
            logger.error(f"Error sending error message: {send_error}")

def main() -> None:
    """Start the bot."""
    # Create the Application with proper configuration
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .concurrent_updates(True)
        .connection_pool_size(8)
        .read_timeout(30)
        .write_timeout(30)
        .connect_timeout(30)
        .pool_timeout(30)
        .build()
    )

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("search", search))
    application.add_handler(CommandHandler("audio", audio))
    
    # Add error handlers
    application.add_error_handler(error_handler)
    
    # Add unknown command handler (must be last)
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    logger.info("Starting bot...")
    
    # Start polling with proper configuration
    logger.info("Starting bot polling...")
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )

if __name__ == "__main__":
    try:
        # Run the bot
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        raise
