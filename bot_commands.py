import json
import os
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from utils import calc_kda
from dota_api import fetch_matches, fetch_match_details, fetch_matches_for_yesterday_msk

TOP_DAY_CACHE_FILE = "data/top_day_cache.json"

def load_top_day_cache():
    try:
        with open(TOP_DAY_CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_top_day_cache(data):
    with open(TOP_DAY_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

with open('data/players.json', 'r', encoding='utf-8') as f:
    players = json.load(f)
with open('data/heroes.json', 'r', encoding='utf-8') as f:
    heroes = json.load(f)
HERO_ID_TO_LOCALIZED = {h['id']: h['localized_name'] for h in heroes if 'id' in h and 'localized_name' in h}

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("БОГ ПОМОЖЕТ!")

async def top_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    cache = load_top_day_cache()
    if today_str in cache:
        await update.message.reply_text("⏳ Loading cached top stats for the day...")
        msg = cache[today_str]
        await update.message.reply_text(msg)
        return

    await update.message.reply_text("⏳ Calculating top stats for the day...")

    results = []
    all_matches = []  # For additional ratings

    for player in players:
        steam_id = player.get('steam_id')
        if not steam_id:
            continue

        matches = await fetch_matches_for_yesterday_msk(steam_id)
        if not matches:
            continue

        best_match = None
        worst_match = None
        best_kda = -1
        worst_kda = float('inf')

        for m in matches:
            kills = m.get("kills", 0)
            deaths = m.get("deaths", 0)
            assists = m.get("assists", 0)
            kda = calc_kda(kills, deaths, assists)
            match_info = {
                "player": player,
                "match": m,
                "kda": kda
            }
            if kda > best_kda:
                best_kda = kda
                best_match = match_info
            if kda < worst_kda:
                worst_kda = kda
                worst_match = match_info

        # Fetch detailed stats for all matches for additional ratings
        for m in matches:
            match_id = m.get("match_id")
            details = await fetch_match_details(match_id)
            if details:
                for p in details.get("players", []):
                    if str(p.get("account_id")) == str(player.get("steam_id")):
                        m["gold_per_min"] = p.get("gold_per_min", 0)
                        m["hero_damage"] = p.get("hero_damage", 0)
                        m["assists"] = p.get("assists", 0)
                        m["kills"] = p.get("kills", 0)
                        m["deaths"] = p.get("deaths", 0)
                        m["hero_id"] = p.get("hero_id", m.get("hero_id"))
                        all_matches.append({
                            "player": player,
                            "match": m
                        })
                        break

        if best_match:
            # Fetch detailed stats for best match
            match_id = best_match["match"].get("match_id")
            details = await fetch_match_details(match_id)
            if details:
                for p in details.get("players", []):
                    if str(p.get("account_id")) == str(player.get("steam_id")):
                        best_match["match"]["gold_per_min"] = p.get("gold_per_min", 0)
                        best_match["match"]["hero_damage"] = p.get("hero_damage", 0)
                        break
            results.append({"type": "best", "data": best_match})

        if worst_match:
            # Fetch detailed stats for worst match
            match_id = worst_match["match"].get("match_id")
            details = await fetch_match_details(match_id)
            if details:
                for p in details.get("players", []):
                    if str(p.get("account_id")) == str(player.get("steam_id")):
                        worst_match["match"]["gold_per_min"] = p.get("gold_per_min", 0)
                        worst_match["match"]["hero_damage"] = p.get("hero_damage", 0)
                        break
            results.append({"type": "worst", "data": worst_match})

    mvp = max((r for r in results if r["type"] == "best"), key=lambda x: x["data"]["kda"], default=None)
    loh = min((r for r in results if r["type"] == "worst"), key=lambda x: x["data"]["kda"], default=None)

    def perf_str(info):
        player = info["player"]
        m = info["match"]
        login = player.get("login", "")
        # Use login if it starts with '@', otherwise use name
        if login.startswith("@"):
            display_name = login
        else:
            display_name = player.get("name", "Unknown")
        hero_id = m.get("hero_id", "Unknown")
        hero_name = HERO_ID_TO_LOCALIZED.get(hero_id, f"HeroID:{hero_id}")
        win = (
            (m.get("player_slot", 0) < 128 and m.get("radiant_win")) or
            (m.get("player_slot", 0) >= 128 and not m.get("radiant_win"))
        )
        kills = m.get("kills", 0)
        deaths = m.get("deaths", 0)
        assists = m.get("assists", 0)
        gpm = m.get("gold_per_min", 0)
        hero_damage = m.get("hero_damage", 0)
        return (
            f"{display_name}, Hero: {hero_name}, {'WIN' if win else 'LOSE'}, "
            f"Kills: {kills}, Deaths: {deaths}, Assists: {assists}, "
            f"GPM: {gpm}, HeroDMG: {hero_damage}"
        )

    # Additional ratings
    killer = max(all_matches, key=lambda x: x["match"].get("kills", 0), default=None)
    miposhka = max(all_matches, key=lambda x: x["match"].get("assists", 0), default=None)
    suicider = max(all_matches, key=lambda x: x["match"].get("deaths", 0), default=None)
    greedy = max(all_matches, key=lambda x: x["match"].get("gold_per_min", 0), default=None)
    damager = max(all_matches, key=lambda x: x["match"].get("hero_damage", 0), default=None)

    # Nightfall award: all matches with 0 deaths and at least 1 kill
    nightfall_matches = [
        {"player": m["player"], "match": m["match"]}
        for m in all_matches
        if m["match"].get("deaths", 0) == 0 and m["match"].get("kills", 0) > 0
    ]

    # TimTim award: all matches with 0 kills
    timtim_matches = [
        {"player": m["player"], "match": m["match"]}
        for m in all_matches
        if m["match"].get("kills", 0) == 0
    ]

    def short_perf_str(info, field):
        player = info["player"]
        m = info["match"]
        login = player.get("login", "")
        if login.startswith("@"):
            display_name = login
        else:
            display_name = player.get("name", "Unknown")
        hero_id = m.get("hero_id", "Unknown")
        hero_name = HERO_ID_TO_LOCALIZED.get(hero_id, f"HeroID:{hero_id}")
        value = m.get(field, 0)
        if field == "kills":
            return f"{display_name}, Hero: {hero_name}, Kills: {value}"
        if field == "assists":
            return f"{display_name}, Hero: {hero_name}, Assists: {value}"
        if field == "deaths":
            return f"{display_name}, Hero: {hero_name}, Deaths: {value}"
        if field == "gold_per_min":
            return f"{display_name}, Hero: {hero_name}, GPM: {value}"
        if field == "hero_damage":
            return f"{display_name}, Hero: {hero_name}, HeroDMG: {value}"
        return ""

    msg = "🏆 Top Day Results:\n"
    if mvp:
        msg += f"\nMVP (Best KDA):\n{perf_str(mvp['data'])}"
    else:
        msg += "\nMVP (Best KDA): Not found"

    if loh:
        msg += f"\n\nLOH (Worst KDA):\n{perf_str(loh['data'])}"
    else:
        msg += "\n\nLOH (Worst KDA): Not found"

    msg += "\n\nKiller (Most Kills):\n"
    msg += short_perf_str(killer, "kills") if killer else "Not found"

    msg += "\n\nMiposhka (Most Assists):\n"
    msg += short_perf_str(miposhka, "assists") if miposhka else "Not found"

    msg += "\n\nSuicider (Most Deaths):\n"
    msg += short_perf_str(suicider, "deaths") if suicider else "Not found"

    msg += "\n\nGreedy (Highest GPM):\n"
    msg += short_perf_str(greedy, "gold_per_min") if greedy else "Not found"

    msg += "\n\nDamager (Highest HeroDMG):\n"
    msg += short_perf_str(damager, "hero_damage") if damager else "Not found"

    msg += "\n\nNightfall award (Идеалыч 0 смертей):\n"
    if nightfall_matches:
        msg += "\n".join([short_perf_str(m, "kills") for m in nightfall_matches])
    else:
        msg += "Not found"

    if timtim_matches:
        msg += "\n\nTimTim award (0 kills):\n"
        msg += "\n".join([short_perf_str(m, "deaths") for m in timtim_matches])    

    cache[today_str] = msg
    save_top_day_cache(cache)

    await update.message.reply_text(msg)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.from_user:
        await update.effective_chat.send_message("⚠️ Can't identify your Telegram user.")
        return

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
        kda = calc_kda(kills, deaths, assists)
        kda_list.append(kda)
    avg_kda = sum(kda_list) / total if total > 0 else 0

    msg = (
        f"📊 Your ranked matches stats for the last {period}:\n"
        f"Matches played: {total}\n"
        f"Win rate: {win_rate:.2f}%\n"
        f"Average KDA: {avg_kda:.2f}\n"
    )
    await update.message.reply_text(msg)