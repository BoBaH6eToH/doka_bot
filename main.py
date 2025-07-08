from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv

import json
import requests
import os

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
OPENDOTA_API_KEY = os.getenv("OPENDOTA_API_KEY")

with open('data/players.json', 'r', encoding='utf-8') as f:
    players = json.load(f)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("БОГ ПОМОЖЕТ!")

async def top_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📊 Here's the top for today!")

async def match_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Please provide a match ID.\nExample: /match 271145478")
        return

    match_id = context.args[0]

    url = f"https://api.opendota.com/api/matches/{match_id}?api_key={OPENDOTA_API_KEY}"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        duration = data.get("duration", 0)
        radiant_win = data.get("radiant_win", False)
        players = [p.get("personaname", "Unknown") for p in data.get("players", [])]

        msg = f"🏆 Match ID: {match_id}\n"
        msg += f"Duration: {duration // 60}m {duration % 60}s\n"
        msg += f"Radiant Victory: {'Yes' if radiant_win else 'No'}\n"
        msg += f"Players:\n" + "\n".join(players)

        await update.message.reply_text(msg)
    else:
        await update.message.reply_text("⚠️ Failed to fetch match info. Make sure the ID is correct.")


if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("top_day", top_day))
    app.add_handler(CommandHandler("match", match_info))
    app.run_polling()
