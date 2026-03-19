import os
import subprocess
import telegram
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
BOT_TOKEN = "tokenhere"

# Store current working directory
current_dir = os.getcwd()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message when /start is issued."""
    await update.message.reply_text(
        "Welcome to the Terminal Bot! Send any shell command to execute it.\n"
        "Use '/cd <path>' to change directories. Current directory: " + current_dir
    )

async def cd_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /cd command to change directories."""
    global current_dir
    path = " ".join(context.args).strip()
    if not path:
        await update.message.reply_text("Please specify a directory. Usage: /cd <path>")
        return
    try:
        # Attempt to change directory
        os.chdir(path)
        current_dir = os.getcwd()
        await update.message.reply_text(f"Changed directory to: {current_dir}")
    except FileNotFoundError:
        await update.message.reply_text(f"Directory not found: {path}")
    except PermissionError:
        await update.message.reply_text(f"Permission denied: {path}")
    except Exception as e:
        await update.message.reply_text(f"Error changing directory: {str(e)}")

async def handle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming shell commands."""
    global current_dir
    command = update.message.text.strip()
    if not command:
        await update.message.reply_text("Please send a valid command.")
        return

    try:
        # Execute shell commands
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=current_dir,
            timeout=30  # Prevent hanging on long-running commands
        )
        output = result.stdout + result.stderr
        if not output:
            output = "Command executed (no output)."
        # Telegram messages have a 4096-character limit
        if len(output) > 4000:
            output = output[:4000] + "\n[Output truncated...]"
        await update.message.reply_text(output or "No output.")
    except subprocess.TimeoutExpired:
        await update.message.reply_text("Command timed out after 30 seconds.")
    except Exception as e:
        await update.message.reply_text(f"Error executing command: {str(e)}")

def main():
    """Start the bot."""
    if not BOT_TOKEN:
        print("Error: BOT_TOKEN must be set in .env file.")
        return

    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cd", cd_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_command))

    # Start the bot
    print("Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
