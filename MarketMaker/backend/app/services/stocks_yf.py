from __future__ import annotations
import logging
import yfinance as yf
import pandas as pd

log = logging.getLogger("services.stocks_yf")

def fetch_recent_stock_bars(symbol: str, period: str = "5d", interval: str = "15m") -> pd.DataFrame:
    """
    Fetch recent stock bars for a given symbol using yfinance.

    Args:
        symbol (str): The stock symbol to fetch data for.
        period (str): The period over which to fetch data (default is "5d").
        interval (str): The interval between data points (default is "15m").

    Returns:
        pd.DataFrame: A DataFrame containing the stock data.
    """
    symbol = symbol.upper()
    try:
        # Now, we call the yfinance library.
        # auto_adjust=True handles stock splits and dividends automatically.
        df = yf.download(symbol, period=period, interval=interval, progress=False, auto_adjust=True)
        if df is None or df.empty:
            return pd.DataFrame()
        df = df.reset_index()
        return df
    except Exception as e:
        log.exception("failed to fetch stock bars for %s: %s", symbol, e)
        return pd.DataFrame()