import json
import logging
import os
import re
import shutil
import time
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    ConversationHandler,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
QUESTIONS_DIR = Path("/home/ubuntu/questions_responses/questions")
AUDIO_DIR = Path("/home/ubuntu/questions_responses/audio")
MAPPING_FILE = QUESTIONS_DIR / "mapping.json"

def normalize_string(text: str) -> str:
    """Port of frontend normalizeString() function."""
    normalized = unicodedata.normalize('NFD', text)
    normalized = re.sub(r'[\u0300-\u036f]', '', normalized)
    normalized = normalized.lower()
    normalized = re.sub(r'[^a-z0-9\s]', ' ', normalized)
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized.strip()

def load_questions() -> List[Dict]:
    """Load questions from mapping.json."""
    try:
        with open(MAPPING_FILE) as f:
            data = json.load(f)
            return data.get("questions", [])
    except Exception as e:
        logger.error(f"Error loading questions: {e}")
        return []

def search_questions(query: str, questions: List[Dict]) -> List[Dict]:
    """Search questions using the same logic as the web app."""
    keywords = [k for k in query.lower().split() if k]
    if not keywords:
        return []
    
    results = []
    for q in questions:
        text = normalize_string(f"{q['question']} {q['author']} {q['date']}")
        if any(normalize_string(k) in text for k in keywords):
            results.append(q)
    return results

def get_audio_path(question_id: str) -> Optional[str]:
    """Get the path to the audio file for a question."""
    questions = load_questions()
    question = next((q for q in questions if q["id"] == question_id), None)
    
    if not question or not question["audio_files"]:
        return None
    
    audio_file = question["audio_files"][0]
    audio_path = AUDIO_DIR / audio_file
    
    return str(audio_path) if audio_path.exists() else None

def format_question_result(question: Dict) -> str:
    """Format a question result for Telegram display."""
    return (
        f"📅 {question['date']} - 👤 {question['author']}\n\n"
        f"❓ {question['question']}\n\n"
        f"🎵 {len(question['audio_files'])} réponse(s) audio\n"
        f"ID: {question['id']}"
    )

def handle_search_command(query: str) -> List[str]:
    """Handle /search command."""
    if not query:
        return ["Veuillez fournir un terme de recherche"]
    
    questions = load_questions()
    results = search_questions(query, questions)
    
    if not results:
        return ["Aucun résultat trouvé"]
    
    # Format results, limiting to first 5 to avoid message length limits
    formatted = [format_question_result(q) for q in results[:5]]
    if len(results) > 5:
        formatted.append(f"\n... et {len(results) - 5} autres résultats")
    
    return formatted

def handle_audio_command(question_id: str) -> Optional[str]:
    """Handle /audio command."""
    if not question_id:
        return "Veuillez fournir un ID de question"
    
    audio_path = get_audio_path(question_id)
    if not audio_path:
        return "Audio non trouvé pour cette question"
    
    return audio_path

def handle_delete_question(question_id: str) -> str:
    """Handle /delete_question command."""
    if not question_id:
        return "Veuillez fournir un ID de question"
    
    try:
        # Create backup before deletion
        backup_dir = Path("/home/ubuntu/backup/questions")
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_file = backup_dir / f"mapping_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        shutil.copy2(MAPPING_FILE, backup_file)
        
        # Load current questions
        with open(MAPPING_FILE) as f:
            data = json.load(f)
        
        # Find question to delete
        questions = data["questions"]
        question = next((q for q in questions if q["id"] == question_id), None)
        if not question:
            return "Question non trouvée"
        
        # Remove question from mapping
        data["questions"] = [q for q in questions if q["id"] != question_id]
        
        # Save updated mapping
        with open(MAPPING_FILE, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Delete question text file
        question_file = QUESTIONS_DIR / f"{question_id}.txt"
        if question_file.exists():
            question_file.unlink()
        
        # Delete associated audio files
        for audio_file in question["audio_files"]:
            audio_path = AUDIO_DIR / audio_file
            if audio_path.exists():
                audio_path.unlink()
        
        return "✅ Question supprimée avec succès"
        
    except Exception as e:
        logger.error(f"Error deleting question {question_id}: {e}")
        return f"❌ Erreur lors de la suppression: {str(e)}"

def handle_delete_audio(question_id: str, audio_index: int) -> str:
    """Handle /delete_audio command."""
    if not question_id:
        return "Veuillez fournir un ID de question"
    
    try:
        # Create backup before deletion
        backup_dir = Path("/home/ubuntu/backup/questions")
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_file = backup_dir / f"mapping_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        shutil.copy2(MAPPING_FILE, backup_file)
        
        # Load current questions
        with open(MAPPING_FILE) as f:
            data = json.load(f)
        
        # Find question
        questions = data["questions"]
        question = next((q for q in questions if q["id"] == question_id), None)
        if not question:
            return "Question non trouvée"
        
        # Validate audio index
        if not question["audio_files"] or audio_index >= len(question["audio_files"]):
            return "Fichier audio non trouvé"
        
        # Get audio filename and remove from list
        audio_file = question["audio_files"].pop(audio_index)
        
        # Delete audio file
        audio_path = AUDIO_DIR / audio_file
        if audio_path.exists():
            audio_path.unlink()
        
        # Save updated mapping
        with open(MAPPING_FILE, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return "✅ Réponse audio supprimée avec succès"
        
    except Exception as e:
        logger.error(f"Error deleting audio {question_id}/{audio_index}: {e}")
        return f"❌ Erreur lors de la suppression: {str(e)}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    welcome_message = (
        "👋 Bienvenue dans le bot Questions au Rav Abichid!\n\n"
        "Commandes disponibles:\n"
        "/search <terme> - Rechercher des questions\n"
        "/audio <id> - Écouter une réponse audio\n"
        "/delete_question <id> - Supprimer une question\n"
        "/delete_audio <id> <index> - Supprimer une réponse audio\n"
        "/help - Afficher l'aide\n\n"
        "Exemple: /search chabbat"
    )
    await update.message.reply_text(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    help_text = (
        "🔍 Pour rechercher une question:\n"
        "/search <terme>\n"
        "Example: /search viande lait\n\n"
        "🎵 Pour écouter une réponse:\n"
        "/audio <id>\n"
        "Example: /audio 2017-03-09-001\n\n"
        "❌ Pour supprimer une question:\n"
        "/delete_question <id>\n"
        "Example: /delete_question 2017-03-09-001\n\n"
        "❌ Pour supprimer une réponse audio:\n"
        "/delete_audio <id> <index>\n"
        "Example: /delete_audio 2017-03-09-001 0\n\n"
        "La recherche ignore les accents et la casse."
    )
    await update.message.reply_text(help_text)

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /search command."""
    if not context.args:
        await update.message.reply_text(
            "❌ Veuillez fournir un terme de recherche\n"
            "Exemple: /search chabbat"
        )
        return

    query = " ".join(context.args)
    results = handle_search_command(query)
    
    if not results:
        await update.message.reply_text("❌ Aucun résultat trouvé")
        return
    
    for result in results:
        await update.message.reply_text(result)

async def audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /audio command."""
    if not context.args:
        await update.message.reply_text(
            "❌ Veuillez fournir l'ID de la question\n"
            "Exemple: /audio 2017-03-09-001"
        )
        return

    question_id = context.args[0]
    audio_path = handle_audio_command(question_id)
    
    if not audio_path:
        await update.message.reply_text("❌ Audio non trouvé pour cette question")
        return
    
    try:
        with open(audio_path, "rb") as audio_file:
            await update.message.reply_audio(
                audio_file,
                filename=os.path.basename(audio_path),
                caption=f"Réponse audio pour la question {question_id}"
            )
    except Exception as e:
        logger.error(f"Error sending audio: {e}")
        await update.message.reply_text("❌ Erreur lors de l'envoi de l'audio")

# States for conversation handlers
CONFIRM_DELETE_QUESTION, CONFIRM_DELETE_AUDIO = range(2)

async def delete_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the question deletion process."""
    if not context.args:
        await update.message.reply_text(
            "❌ Veuillez fournir l'ID de la question\n"
            "Exemple: /delete_question 2017-03-09-001"
        )
        return ConversationHandler.END

    question_id = context.args[0]
    context.user_data['delete_question_id'] = question_id
    
    await update.message.reply_text(
        f"⚠️ Êtes-vous sûr de vouloir supprimer la question {question_id} ?\n"
        "Cette action est irréversible.\n"
        "Répondez 'oui' pour confirmer ou 'non' pour annuler."
    )
    
    return CONFIRM_DELETE_QUESTION

async def confirm_delete_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the confirmation response for question deletion."""
    response = update.message.text.lower()
    question_id = context.user_data.get('delete_question_id')
    
    if response == 'oui':
        result = handle_delete_question(question_id)
        await update.message.reply_text(result)
    else:
        await update.message.reply_text("❌ Suppression annulée")
    
    return ConversationHandler.END

async def delete_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the audio deletion process."""
    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ Veuillez fournir l'ID de la question et l'index de l'audio\n"
            "Exemple: /delete_audio 2017-03-09-001 0"
        )
        return ConversationHandler.END

    question_id = context.args[0]
    try:
        audio_index = int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ L'index de l'audio doit être un nombre")
        return ConversationHandler.END
    
    context.user_data['delete_audio_id'] = question_id
    context.user_data['delete_audio_index'] = audio_index
    
    await update.message.reply_text(
        f"⚠️ Êtes-vous sûr de vouloir supprimer la réponse audio {audio_index + 1} "
        f"de la question {question_id} ?\n"
        "Cette action est irréversible.\n"
        "Répondez 'oui' pour confirmer ou 'non' pour annuler."
    )
    
    return CONFIRM_DELETE_AUDIO

async def confirm_delete_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the confirmation response for audio deletion."""
    response = update.message.text.lower()
    question_id = context.user_data.get('delete_audio_id')
    audio_index = context.user_data.get('delete_audio_index')
    
    if response == 'oui':
        result = handle_delete_audio(question_id, audio_index)
        await update.message.reply_text(result)
    else:
        await update.message.reply_text("❌ Suppression annulée")
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the current operation."""
    await update.message.reply_text("❌ Opération annulée.")
    return ConversationHandler.END

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors caused by Updates with detailed logging."""
    # Log the error with full context
    logger.error(
        "Error handling update:\n"
        f"Update: {update}\n"
        f"Error: {context.error}\n",
        exc_info=context.error,
        extra={
            "update_id": update.update_id if update else None,
            "chat_id": update.effective_chat.id if update and update.effective_chat else None,
            "user_id": update.effective_user.id if update and update.effective_user else None,
            "message": update.effective_message.text if update and update.effective_message else None,
        }
    )

    # Notify user based on error type
    if update and update.effective_message:
        if isinstance(context.error, TimeoutError):
            await update.effective_message.reply_text(
                "❌ Délai d'attente dépassé. Veuillez réessayer."
            )
        elif isinstance(context.error, (IOError, OSError)):
            await update.effective_message.reply_text(
                "❌ Erreur d'accès aux fichiers. Veuillez réessayer plus tard."
            )
        elif isinstance(context.error, json.JSONDecodeError):
            await update.effective_message.reply_text(
                "❌ Erreur de lecture des données. Veuillez contacter l'administrateur."
            )
        else:
            await update.effective_message.reply_text(
                "❌ Une erreur s'est produite. Veuillez réessayer plus tard."
            )

    # Log recovery attempt
    logger.info(
        "Error handler completed",
        extra={
            "update_id": update.update_id if update else None,
            "error_type": type(context.error).__name__
        }
    )

def setup_logging():
    """Configure detailed logging for the bot."""
    # Create logs directory
    log_dir = Path("/home/ubuntu/logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configure file handler
    file_handler = logging.FileHandler(log_dir / "telegram_bot.log")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - '
        '%(message)s - %(update_id)s - %(chat_id)s - %(user_id)s'
    ))
    
    # Configure console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    ))
    
    # Add handlers to root logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Set logging level
    logger.setLevel(logging.INFO)

def main() -> None:
    """Start the bot with error handling and monitoring."""
    # Set up logging
    setup_logging()
    logger.info("Starting bot...")
    
    # Create the Application with connection pool
    try:
        application = (
            Application.builder()
            .token(os.environ["TELEGRAM_BOT_TOKEN"])
            .connection_pool_size(8)  # Increase connection pool size
            .pool_timeout(30.0)       # Set pool timeout
            .connect_timeout(30.0)    # Set connect timeout
            .read_timeout(30.0)       # Set read timeout
            .write_timeout(30.0)      # Set write timeout
            .build()
        )
        logger.info("Application created successfully")
    except Exception as e:
        logger.critical(f"Failed to create application: {e}", exc_info=True)
        raise
        
    # Add basic command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("search", search))
    application.add_handler(CommandHandler("audio", audio))

    # Add conversation handler for question deletion
    delete_question_handler = ConversationHandler(
        entry_points=[CommandHandler("delete_question", delete_question)],
        states={
            CONFIRM_DELETE_QUESTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_delete_question)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(delete_question_handler)

    # Add conversation handler for audio deletion
    delete_audio_handler = ConversationHandler(
        entry_points=[CommandHandler("delete_audio", delete_audio)],
        states={
            CONFIRM_DELETE_AUDIO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_delete_audio)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(delete_audio_handler)

    # Add error handler
    application.add_error_handler(error_handler)

    # Start the Bot with error recovery
    try:
        logger.info("Starting polling...")
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,  # Ignore updates from when bot was offline
            pool_timeout=30.0,
            read_timeout=30.0,
            write_timeout=30.0,
        )
    except Exception as e:
        logger.critical(f"Bot crashed: {e}", exc_info=True)
        # In production, this would trigger monitoring alerts
        raise

if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as e:
            logger.critical(f"Bot crashed and will restart in 60 seconds: {e}", exc_info=True)
            time.sleep(60)  # Wait before restarting
