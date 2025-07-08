from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv
from datetime import datetime, timedelta

import aiohttp
import json
import requests
import os

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
OPENDOTA_API_KEY = os.getenv("OPENDOTA_API_KEY")

with open('data/players.json', 'r', encoding='utf-8') as f:
    players = json.load(f)

async def fetch_matches(steam_id, days):
    """Requests user matches for the last `days` days"""
    url = f"https://api.opendota.com/api/players/{steam_id}/matches?api_key={OPENDOTA_API_KEY}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return None
            all_matches = await resp.json()

    cutoff = datetime.utcnow() - timedelta(days=days)
    filtered = []
    for m in all_matches:
        # match time in unix timestamp (UTC)
        start_time = datetime.utcfromtimestamp(m.get("start_time", 0))
        if start_time >= cutoff and m.get("lobby_type") == 7:  # 7 — ranked matchmaking
            filtered.append(m)
    return filtered

def calc_kda(kills, deaths, assists):
    return (kills + assists) / deaths if deaths != 0 else (kills + assists)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("БОГ ПОМОЖЕТ!")

async def top_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📊 Here's the top for today!")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "⚠️ Please specify period: day, week or month.\n"
            "Example: /stats week"
        )
        return

    period = context.args[0].lower()
    days_map = {"day": 1, "week": 7, "month": 30}
    if period not in days_map:
        await update.message.reply_text("⚠️ Invalid period. Use: day, week or month.")
        return

    user_login = f"@{update.message.from_user.username}" if update.message.from_user.username else None
    if not user_login:
        await update.message.reply_text("⚠️ Can't identify your Telegram login.")
        return

    player = next((p for p in players if p['login'].lower() == user_login.lower()), None)
    if not player or not player.get('steam_id'):
        await update.message.reply_text("⚠️ Steam ID not found for your user.")
        return

    steam_id = player['steam_id']
    days = days_map[period]

    await update.message.reply_text(f"⏳ Fetching your ranked matches for the last {period}...")

    matches = await fetch_matches(steam_id, days)
    if matches is None:
        await update.message.reply_text("⚠️ Failed to fetch matches from OpenDota.")
        return

    if not matches:
        await update.message.reply_text("⚠️ No ranked matches found for the specified period.")
        return

    total = len(matches)
    wins = sum(
        1 for m in matches if
        (m.get("player_slot", 0) < 128 and m.get("radiant_win")) or
        (m.get("player_slot", 0) >= 128 and not m.get("radiant_win"))
    )

    win_rate = wins / total * 100

    # Calculate average KDA per match
    kda_list = []
    for m in matches:
        kills = m.get("kills", 0)
        deaths = m.get("deaths", 0)
        assists = m.get("assists", 0)
        kda = (kills + assists) / deaths if deaths != 0 else (kills + assists)
        kda_list.append(kda)
    avg_kda = sum(kda_list) / total if total > 0 else 0

    msg = (
        f"📊 Your ranked matches stats for the last {period}:\n"
        f"Matches played: {total}\n"
        f"Win rate: {win_rate:.2f}%\n"
        f"Average KDA: {avg_kda:.2f}\n"
    )
    await update.message.reply_text(msg)

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("top_day", top_day))
    app.add_handler(CommandHandler("stats", stats_command))
    app.run_polling()
