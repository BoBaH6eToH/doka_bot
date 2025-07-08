from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler
from dotenv import load_dotenv
import os

from bot_commands import help_command, top_day, stats_command

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("top_day", top_day))
