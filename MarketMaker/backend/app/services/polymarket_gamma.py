from __future__ import annotations

import logging
import httpx

log = logging.getLogger("services.polymarket_gamma")

GAMMA_BASE = "https://gamma-api.polymarket.com"  # public metadata API :contentReference[oaicite:5]{index=5}

async def fetch_events(query: str, limit: int = 25) -> list[dict]:
    """
    Fetch active events. We keep it simple:
    1. Pull newest events from the API.
    2. Perform Client-Side Filtering (since the API might not support fuzzy search well).
    """

    params = {
        "order": "id", 
        "ascending": "false",
        "closed": "false",
        "limit": str(limit),
    }

    # Now, we use an Async HTTP Client.
    # This is non-blocking, allowing the server to handle other requests while waiting for Polymarket.
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{GAMMA_BASE}/events", params=params)
        resp.raise_for_status()
        events = resp.json()

    q = (query or "").lower().strip()
    if not q:
        return events
    
    filtered = []
    for e in events:
        blob = f"{e.get('title', '')} {e.get('slug', '')}".lower()
        if q in blob:
            filtered.append(e)

    return filtered

def extract_market_signals_from_event(event: dict) -> list[dict]:
    """
    Normalization Logic.
    The API returns a nested structure (Event -> Markets). We flatten this into a list of Signals.
    """
    signals: list[dict] = []
    markets = event.get("markets", []) or []
    for m in markets:
        # We focus on “probability-ish” movement proxies:
        # Some fields vary; we store raw and let feature layer compute.
        signals.append({
            "market_id": m.get("id"),
            "condition_id": m.get("conditionId"),
            "question": m.get("question"),
            "slug": m.get("slug"),
            "volume": m.get("volume"),
            "liquidity": m.get("liquidity"),
            "clob_token_ids": m.get("clobTokenIds"),
        })
    return signals
