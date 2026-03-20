#!/usr/bin/env python3
import time
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

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7660990923"))

# Global variable to store the currently running process (for /kill)
current_process = None
# Global variable for interactive mode
interactive_mode = False
# Dictionary to store custom aliases
aliases = {}

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
    """Handle /bg command to execute long-running shell commands with live updates."""
    if not is_admin(update):
        return
    global current_process

    # Prevent running multiple bg commands at once to avoid confusion
    if current_process is not None and current_process.poll() is None:
        await update.message.reply_text("A process is already running. Please /kill it first or wait for it to finish.")
        return

    command = " ".join(context.args).strip()
    if not command:
        await update.message.reply_text("Please provide a command. Usage: /bg <command>")
        return

    try:
        current_process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Merge stderr into stdout for live reading
            text=True,
            cwd=current_dir,
            preexec_fn=os.setsid  # Allow killing process group
        )

        message = await update.message.reply_text(f"🚀 Started background process (PID: {current_process.pid})\nLoading...")

        async def read_output():
            global current_process
            output_buffer = ""
            last_update_time = time.time()
            loop = asyncio.get_running_loop()

            # Read stdout line by line without blocking the event loop
            def readline():
                return current_process.stdout.readline()

            while True:
                line = await loop.run_in_executor(None, readline)
                if not line and current_process.poll() is not None:
                    break
                if line:
                    output_buffer += line
                    current_time = time.time()

                    # Update message every 3 seconds to avoid rate limit
                    if current_time - last_update_time >= 3.0:
                        last_update_time = current_time
                        display_text = output_buffer
                        if len(display_text) > 4000:
                            display_text = display_text[-4000:]
                        try:
                            await message.edit_text(f"⏳ Process Running (PID: {current_process.pid})\n\n```\n{display_text}\n```", parse_mode='Markdown')
                        except Exception as e:
                            logger.error(f"Failed to edit live message: {e}")

            # Final update once the process completes
            display_text = output_buffer
            if len(display_text) > 4000:
                display_text = display_text[-4000:]
            if not display_text.strip():
                display_text = "Process finished with no output."

            status = "✅ Process Finished" if current_process.returncode == 0 else "❌ Process Failed/Killed"
            try:
                await message.edit_text(f"{status} (PID: {current_process.pid})\n\n```\n{display_text}\n```", parse_mode='Markdown')
            except Exception as e:
                logger.error(f"Failed to edit final message: {e}")

            current_process = None

        # Start reading the output in the background so the bot remains responsive
        asyncio.create_task(read_output())

    except Exception as e:
        current_process = None
        await update.message.reply_text(f"Error executing background command: {str(e)}")


async def kill_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /kill command to terminate the running process."""
    if not is_admin(update):
        return
    global current_process
    if current_process is None or current_process.poll() is not None:
        await update.message.reply_text("No active process to kill.")
        current_process = None
        return
    try:
        import signal
        os.killpg(os.getpgid(current_process.pid), signal.SIGTERM)
        # Give it a tiny bit to actually die, the read loop will handle nullifying current_process
        await update.message.reply_text(f"The running process (PID: {current_process.pid}) has been sent the kill signal.")
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


async def alias_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a new shortcut alias."""
    if not is_admin(update):
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usage: `/alias <name> <command>`\nExample: `/alias up apt-get update`", parse_mode='Markdown')
        return
    alias_name = args[0]
    alias_cmd = " ".join(args[1:])
    aliases[alias_name] = alias_cmd
    await update.message.reply_text(f"✅ Alias saved: `{alias_name}` -> `{alias_cmd}`", parse_mode='Markdown')


async def aliases_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all aliases."""
    if not is_admin(update):
        return
    if not aliases:
        await update.message.reply_text("No aliases saved.")
        return
    msg = "📝 **Saved Aliases:**\n\n"
    for name, cmd in aliases.items():
        msg += f"`{name}` -> `{cmd}`\n"
    await update.message.reply_text(msg, parse_mode='Markdown')


async def interactive_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle interactive shell mode on."""
    if not is_admin(update):
        return
    global interactive_mode
    interactive_mode = True
    await update.message.reply_text("🟢 **Interactive Mode Enabled**\nYou no longer need to use `/run`. Every message you send will be executed as a shell command.\nType `/exit` to turn this off.", parse_mode='Markdown')


async def exit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle interactive shell mode off."""
    if not is_admin(update):
        return
    global interactive_mode
    interactive_mode = False
    await update.message.reply_text("🔴 **Interactive Mode Disabled**\nYou must now use `/run <cmd>` to execute commands.", parse_mode='Markdown')


async def execute_shell_command(update: Update, command: str):
    """Helper function to execute a shell command and reply with output."""
    global current_process

    # Check for alias
    first_word = command.split()[0] if command else ""
    if first_word in aliases:
        command = command.replace(first_word, aliases[first_word], 1)
        await update.message.reply_text(f"*(Alias expanded: `{command}`)*", parse_mode='Markdown')

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
                "Use `/bg <command>` for long-running processes.",
                parse_mode='Markdown'
            )
    except Exception as e:
        current_process = None
        await update.message.reply_text(f"Error executing command: {str(e)}")


async def run_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /run command to execute shell commands."""
    if not is_admin(update):
        return
    # Extract the command after /run
    command = " ".join(context.args).strip()
    if not command:
        await update.message.reply_text("Please provide a command to run. Usage: /run <command>")
        return
    await execute_shell_command(update, command)


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
            BotCommand("interactive", "Toggle interactive shell mode"),
            BotCommand("exit", "Disable interactive mode"),
            BotCommand("alias", "Add a shortcut (e.g., /alias up apt update)"),
            BotCommand("aliases", "List all shortcuts"),
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
    application.add_handler(CommandHandler("interactive", interactive_command))
    application.add_handler(CommandHandler("exit", exit_command))
    application.add_handler(CommandHandler("alias", alias_command))
    application.add_handler(CommandHandler("aliases", aliases_command))

    # Message handler for interactive mode or fallback warning
    async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if is_admin(update):
            if interactive_mode:
                command = update.message.text.strip()
                await execute_shell_command(update, command)
            else:
                await update.message.reply_text("Please use `/run <command>` to execute shell commands, or type `/interactive` to enable interactive mode.", parse_mode='Markdown')

    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, unknown_command))

    # Start the bot
    print("Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
