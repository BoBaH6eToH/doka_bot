import aiohttp
from datetime import datetime, timedelta, time, timezone

MOSCOW_TZ = timezone(timedelta(hours=3))

async def fetch_matches(steam_id, days):
    """Requests user matches for the last `days` days"""
    url = f"https://api.opendota.com/api/players/{steam_id}/matches"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return None
            all_matches = await resp.json()

    cutoff = datetime.utcnow() - timedelta(days=days)
    filtered = []
    for m in all_matches:
        start_time = datetime.utcfromtimestamp(m.get("start_time", 0))
        if start_time >= cutoff and m.get("lobby_type") == 7:
            filtered.append(m)
    return filtered

async def fetch_match_details(match_id):
    """Fetch detailed match info by match_id"""
    url = f"https://api.opendota.com/api/matches/{match_id}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return None
            return await resp.json()

async def fetch_matches_for_yesterday_msk(steam_id):
    """Fetch matches for the previous calendar day in Moscow time."""
    now_msk = datetime.now(MOSCOW_TZ)
    yesterday = now_msk.date() - timedelta(days=1)
    start_dt = datetime.combine(yesterday, time.min, tzinfo=MOSCOW_TZ)
    end_dt = datetime.combine(yesterday, time.max, tzinfo=MOSCOW_TZ)
    start_ts = int(start_dt.timestamp())
    end_ts = int(end_dt.timestamp())

    url = f"https://api.opendota.com/api/players/{steam_id}/matches"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return []
            all_matches = await resp.json()

    filtered = []
    for m in all_matches:
        start_time = m.get("start_time", 0)
        if start_ts <= start_time <= end_ts and m.get("lobby_type") == 7:
            filtered.append(m)
    return filtered

# В функции top_day замените вызов fetch_matches на fetch_matches_for_yesterday_msk:
# matches = await fetch_matches(steam_id, 1)
# на:
# matches = await fetch_matches_for_yesterday_msk(steam_id)