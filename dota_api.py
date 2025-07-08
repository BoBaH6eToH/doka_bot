import aiohttp
from datetime import datetime, timedelta

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