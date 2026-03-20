#!/usr/bin/env python3
import asyncio
import os
import subprocess
import sys
import psutil
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

try:
    from dotenv import load_dotenv
    # Load environment variables
    load_dotenv()
except ImportError:
    pass

BOT_TOKEN = os.getenv("BOT_TOKEN", "8701460956:AAFuXdXSr46z_2CeFexRlVZS1LQ3NUsmiyw")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7660990923"))

# Global variable to store the currently running process (for /kill)
current_process = None

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


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command to check system resources."""
    if not is_admin(update):
        return
    try:
        cpu_usage = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        stats_message = (
            "📊 *System Stats*\n\n"
            f"💻 *CPU Usage:* {cpu_usage}%\n"
            f"🧠 *RAM Usage:* {memory.percent}% ({memory.used // (1024**2)}MB / {memory.total // (1024**2)}MB)\n"
            f"💾 *Disk Usage:* {disk.percent}% ({disk.used // (1024**3)}GB / {disk.total // (1024**3)}GB)"
        )
        await update.message.reply_text(stats_message, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"Error getting stats: {str(e)}")


async def bg_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /bg command to execute long-running shell commands in the background."""
    if not is_admin(update):
        return
    global current_process
    command = " ".join(context.args).strip()
    if not command:
        await update.message.reply_text("Please provide a command. Usage: /bg <command>")
        return

    try:
        current_process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=current_dir,
            preexec_fn=os.setsid  # Allow killing process group
        )
        await update.message.reply_text(f"Started background process PID: {current_process.pid}")

        # Run communication in a separate thread so it doesn't block the bot
        def wait_for_process():
            stdout, stderr = current_process.communicate()
            return stdout, stderr

        # Wait asynchronously
        loop = asyncio.get_running_loop()
        stdout, stderr = await loop.run_in_executor(None, wait_for_process)

        output = stdout + stderr
        if not output:
            output = "Background command finished (no output)."
        if len(output) > 4000:
            output = output[:4000] + "\n[Output truncated...]"

        await update.message.reply_text(f"Background Process Finished:\n{output}")
        current_process = None

    except Exception as e:
        current_process = None
        await update.message.reply_text(f"Error executing background command: {str(e)}")


async def kill_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /kill command to terminate the running process."""
    if not is_admin(update):
        return
    global current_process
    if current_process is None:
        await update.message.reply_text("No active process to kill.")
        return
    try:
        import signal
        os.killpg(os.getpgid(current_process.pid), signal.SIGTERM)
        current_process = None
        await update.message.reply_text("The running process has been terminated.")
    except Exception as e:
        await update.message.reply_text(f"Error terminating process: {str(e)}")


async def restart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /restart command to restart the bot."""
    if not is_admin(update):
        return
    await update.message.reply_text("Restarting bot...")
    try:
        os.execv(sys.executable, ['python3'] + sys.argv)
    except Exception as e:
        await update.message.reply_text(f"Error restarting bot: {str(e)}")


async def logs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /logs command to send the last 50 lines of the bot.log file."""
    if not is_admin(update):
        return
    try:
        with open("bot.log", "r") as file:
            lines = file.readlines()
            last_lines = lines[-50:]
            logs_output = "".join(last_lines)
            if not logs_output:
                logs_output = "No logs available."
            elif len(logs_output) > 4000:
                logs_output = logs_output[-4000:]
            await update.message.reply_text(f"Last 50 lines of bot.log:\n```\n{logs_output}\n```", parse_mode='Markdown')
    except FileNotFoundError:
        await update.message.reply_text("Log file not found.")
    except Exception as e:
        await update.message.reply_text(f"Error reading logs: {str(e)}")


async def run_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /run command to execute shell commands."""
    if not is_admin(update):
        return
    global current_process
    # Extract the command after /run
    command = " ".join(context.args).strip()
    if not command:
        await update.message.reply_text("Please provide a command to run. Usage: /run <command>")
        return

    try:
        # Execute shell commands
        current_process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=current_dir,
            preexec_fn=os.setsid
        )
        try:
            # Wait for up to 30 seconds
            stdout, stderr = current_process.communicate(timeout=30)
            output = stdout + stderr
            if not output:
                output = "Command executed (no output)."
            # Telegram messages have a 4096-character limit
            if len(output) > 4000:
                output = output[:4000] + "\n[Output truncated...]"
            await update.message.reply_text(output or "No output.")
            current_process = None
        except subprocess.TimeoutExpired:
            # Don't kill it automatically, let the user know it's still running
            # Or if it's /run, it's better to kill it so they can use /bg instead
            import signal
            os.killpg(os.getpgid(current_process.pid), signal.SIGTERM)
            current_process = None
            await update.message.reply_text(
                "Command timed out after 30 seconds and was killed. "
                "Use /bg <command> for long-running processes."
            )
    except Exception as e:
        current_process = None
        await update.message.reply_text(f"Error executing command: {str(e)}")


def main():
    """Start the bot."""
    if not BOT_TOKEN:
        print("Error: BOT_TOKEN must be set in .env file.")
        return

    # Setup bot commands menu
    async def post_init(app: Application):
        from telegram import BotCommand
        commands = [
            BotCommand("start", "Start the bot"),
            BotCommand("cd", "Change directory (e.g., /cd <path>)"),
            BotCommand("home", "Go to home directory"),
            BotCommand("run", "Run a shell command (e.g., /run ls)"),
            BotCommand("bg", "Run a command in background (e.g., /bg top)"),
            BotCommand("kill", "Kill the currently running process"),
            BotCommand("stats", "Show system CPU, RAM, and Disk usage"),
            BotCommand("logs", "Show last 50 lines of bot logs"),
            BotCommand("restart", "Restart the bot script"),
        ]
        await app.bot.set_my_commands(commands)

    # Create the Application
    application = Application.builder().token(
        BOT_TOKEN).post_init(post_init).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cd", cd_command))
    application.add_handler(CommandHandler("home", home_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("logs", logs_command))
    application.add_handler(CommandHandler("run", run_command))
    application.add_handler(CommandHandler("bg", bg_command))
    application.add_handler(CommandHandler("kill", kill_command))
    application.add_handler(CommandHandler("restart", restart_command))
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
