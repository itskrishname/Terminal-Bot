#!/usr/bin/env python3
import os
import subprocess
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
try:
    from dotenv import load_dotenv
    # Load environment variables
    load_dotenv()
except ImportError:
    pass

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7660990923"))

# Store current working directory
# Change initial directory to the user's home directory
try:
    os.chdir(os.path.expanduser("~"))
except Exception:
    pass
current_dir = os.getcwd()


def is_admin(update: Update) -> bool:
    """Check if the user is the admin."""
    return update.effective_user.id == ADMIN_ID


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message when /start is issued."""
    if not is_admin(update):
        return
    await update.message.reply_text(
        "Welcome to the Terminal Bot! Send any shell command to execute it.\n"
        "Use '/cd <path>' to change directories. Current directory: " + current_dir
    )


async def cd_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /cd command to change directories."""
    if not is_admin(update):
        return
    global current_dir
    path = " ".join(context.args).strip()
    if not path:
        await update.message.reply_text("Please specify a directory. Usage: /cd <path>")
        return

    # Expand ~ to user's home directory
    path = os.path.expanduser(path)

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


async def home_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /home command to instantly jump to the home directory."""
    if not is_admin(update):
        return
    global current_dir
    path = os.path.expanduser("~")
    try:
        os.chdir(path)
        current_dir = os.getcwd()
        await update.message.reply_text(f"Changed directory to Home: {current_dir}")
    except Exception as e:
        await update.message.reply_text(f"Error changing to Home directory: {str(e)}")


async def run_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /run command to execute shell commands."""
    if not is_admin(update):
        return
    # Extract the command after /run
    command = " ".join(context.args).strip()
    if not command:
        await update.message.reply_text("Please provide a command to run. Usage: /run <command>")
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
    application.add_handler(CommandHandler("home", home_command))
    application.add_handler(CommandHandler("run", run_command))
    # Optionally keep a fallback message handler to warn the user

    async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if is_admin(update):
            await update.message.reply_text("Please use /run <command> to execute shell commands.")

    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, unknown_command))

    # Start the bot
    print("Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
