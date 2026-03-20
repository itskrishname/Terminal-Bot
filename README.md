# Terminal Telegram Bot 🚀

A highly secure, feature-rich Telegram Bot that allows you to execute shell commands directly on your server from your Telegram chat. It includes advanced features like background process execution with live output updates, system resource monitoring, and persistent logging.

## 🌟 Key Features

*   **Secure Access Control:** Only the specified `ADMIN_ID` can use the bot. All other users are ignored, preventing unauthorized remote code execution (RCE).
*   **Live Terminal Output:** Run long tasks (like `apt-get install` or downloads) using the `/bg` command, and the bot will stream the terminal output directly to your Telegram message, updating it live every 3 seconds!
*   **Process Management:** Easily `/kill` any runaway or stuck processes directly from the chat.
*   **System Monitoring:** Quickly check your server's RAM, CPU, and Disk Usage with the `/stats` command.
*   **Persistent Logging:** View the bot's internal logs using the `/logs` command to quickly debug issues without SSHing into the server.
*   **Auto-Setup Menu:** The bot automatically registers all its commands with the Telegram API so they appear nicely in your chat menu when you type `/`.

---

## 🛠️ Commands List

| Command | Description | Example |
| :--- | :--- | :--- |
| `/run <cmd>` | Execute a standard shell command (wait for it to finish). | `/run ls -la` |
| `/bg <cmd>` | Execute a long-running shell command in the background with **live output updates**. | `/bg apt-get update` |
| `/kill` | Instantly kill the currently running `/run` or `/bg` process. | `/kill` |
| `/cd <path>` | Change the current working directory. Supports `~` for the home directory. | `/cd /var/www/` |
| `/home` | Instantly jump back to your user's home directory (`~`). | `/home` |
| `/stats` | View real-time system resources (CPU, RAM, Disk). | `/stats` |
| `/logs` | View the last 50 lines of the bot's internal log file (`bot.log`). | `/logs` |
| `/restart` | Restart the bot script immediately without stopping the server. | `/restart` |

---

## ⚙️ Prerequisites & Installation

1. **Python 3.12+**
2. **Telegram Bot Token**: Get this by talking to [@BotFather](https://t.me/BotFather) on Telegram.
3. **Your Telegram User ID**: Talk to a bot like [@userinfobot](https://t.me/userinfobot) to get your numeric user ID.

### Local Setup

1. **Clone the repository** (or download the files to your server).
2. **Install requirements:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Create a `.env` file** in the root directory:
   ```env
   BOT_TOKEN=your_telegram_bot_token_here
   ADMIN_ID=your_numeric_telegram_user_id_here
   ```
4. **Run the bot:**
   ```bash
   python3 main.py
   ```

---

## ☁️ Deployment (Heroku/Render)

This bot is fully prepared to be deployed on platforms like Heroku.

1. Connect your repository to Heroku.
2. In your Heroku **Settings**, go to **Config Vars** and add the following two environment variables:
   * `BOT_TOKEN`: Your token from BotFather.
   * `ADMIN_ID`: Your Telegram numeric ID.
3. The platform will automatically read the included `Procfile`, `runtime.txt`, and `requirements.txt` to install `python-telegram-bot`, `python-dotenv`, and `psutil`, and start the worker process (`python3 main.py`).

---

## ⚠️ Security Warning

Executing arbitrary terminal commands via Telegram is **inherently dangerous**.
* Never share your `ADMIN_ID` or `.env` file.
* Always double-check commands before sending them via `/run` or `/bg`, especially destructive commands like `rm -rf`.
* If you suspect your bot token has been compromised, revoke it immediately via @BotFather.
