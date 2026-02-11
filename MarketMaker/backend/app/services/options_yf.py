from __future__ import annotations
import logging
import yfinance as yf
import pandas as pd

log = logging.getLogger("services.options_yf")

def fetch_options_snapshot(symbol: str) -> dict:
    """
    Pull a lightweight options snapshot from yfinance:
    We focus on the Nearest Expiry, as that is where the most speculative volume usually is.
    We aggregate (Sum) the volume across all strikes to get a macro sentiment view.
    """
    symbol = symbol.upper().strip()
    try:
        t = yf.Ticker(symbol)
        expiries = t.options
        if not expiries:
            return {"symbol": symbol, "has_options": False}
        
        expiry = expiries[0]
        chain = t.option_chain(expiry)

        calls: pd.DataFrame = chain.calls
        puts: pd.DataFrame = chain.puts

        # Now, we define a helper for safe summation.
        # DataFrames can be messy; this ensures we return a float 0.0 instead of crashing.
        def safe_sum(df: pd.DataFrame, col: str) -> float:
            if df is None or df.empty or col not in df.columns:
                return 0.0
            return float(df[col].fillna(0).sum())
        
        snapshot = {
            "symbol": symbol,
            "has_options": True,
            "expiry": expiry,
            "call_volume": safe_sum(calls, "volume"),
            "put_volume": safe_sum(puts, "volume"),
            "calls_oi": safe_sum(calls, "openInterest"),
            "puts_oi": safe_sum(puts, "openInterest"),
        }
        return snapshot
    except Exception as e:
        log.exception(f"Error fetching options snapshot for %s: %s", symbol, e)
        return {"symbol": symbol, "has_options": False, "error": str(e)}
