from __future__ import annotations

import json
import pandas as pd
import numpy as np

def zscore(series: pd.Series) -> float:
    """
    Calculate the Z-score of the most recent value in a series.
    
    Formula: z = (x - μ) / σ
    Where:
      x = latest value
      μ = mean of the series
      σ = standard deviation
      
    Returns:
        float: The number of standard deviations the latest value is from the mean.
               Returns 0.0 if insufficient data (< 10 points).
    """
    # Now, we clean the data by removing any NaN values that could corrupt the math.
    s = series.dropna()
    
    # Now, we enforce a statistical constraint:
    # We need a minimum sample size (N=10) to calculate a statistically significant Z-score.
    # If we don't have enough history, we return 0.0 (neutral signal).
    if len(s) < 10:
        return 0.0
    
    mu = float(s.mean())
    # Now, we calculate standard deviation. We use ddof=0 (Population Std Dev).
    # Crucially, we add a tiny epsilon (or check for 0) to prevent DivisionByZero errors if the stock price was flat.
    sd = float(s.std(ddof=0)) or 1e-9
    return float((s.iloc[-1] - mu) / sd)

def stock_features(df: pd.DataFrame) -> dict:
    """
    Extract technical indicators from raw stock price history.
    
    Args:
        df: DataFrame containing 'Close' and 'Volume' columns (from yfinance).
        
    Returns:
        dict: A dictionary of calculated features.
    """
    # Now, we validate the input. This is "Defensive Programming".
    # We ensure the DataFrame has the columns we expect before trying to access them.
    if df is None or df.empty or "Close" not in df.columns:
        return {}
    
    # Now, we extract the columns we care about, casting to float to ensure precision.
    close = df["Close"].astype(float)
    vol = df.get("Volume", pd.Series([0]*len(df))).astype(float)

    # Now, we calculate returns. This normalizes the price data.
    # A $10 move on a $100 stock is different than on a $1000 stock. Percentage change captures this.
    returns = close.pct_change().fillna(0.0)
    
    feat = {
        "last_close": float(close.iloc[-1]),
        "ret_1": float(returns.iloc[-1]), # The immediate momentum (1-period return).
        "vol_z": zscore(vol),             # The volume anomaly score (how unusual is the trading activity?).
        
        # Now, we calculate Volatility.
        # We look at the standard deviation of returns over the last 20 periods (approx 1 trading month if daily, or 5 hours if 15m).
        "ret_vol_20": float(returns.tail(20).std(ddof=0) if len(returns) >= 20 else returns.std(ddof=0)),
    }
    return feat

def options_features(snapshot: dict) -> dict:
    """
    Extract features from an options chain snapshot.
    Calculates volume and open interest ratios to gauge sentiment.
    """
    # Now, we check the flag. If there are no options for this ticker, we return early.
    if not snapshot.get("has_options"):
        return {"has_options": False}
    
    # Now, we extract raw metrics safely.
    # We use .get() with a default of 0.0 to handle missing data gracefully.
    calls_vol = float(snapshot.get("call_volume", 0.0))
    puts_vol = float(snapshot.get("put_volume", 0.0))
    calls_oi = float(snapshot.get("calls_oi", 0.0))
    puts_oi = float(snapshot.get("puts_oi", 0.0))

    # Now, we calculate Sentiment Ratios.
    # Call/Put Ratio is a classic indicator. High ratio = Bullish, Low ratio = Bearish.
    # Mathematical Safety: We use max(..., 1.0) in the denominator.
    # This prevents division by zero if there is absolutely no Put volume.
    feat = {
        "has_options": True,
        "calls_volume": calls_vol,
        "puts_volume": puts_vol,
        "calls_oi": calls_oi,
        "puts_oi": puts_oi,
        "call_put_vol_ratio": float(calls_vol / max(puts_vol, 1.0)),
        "call_put_oi_ratio": float(calls_oi / max(puts_oi, 1.0)),
    }
    return feat

def features_json(features: dict) -> str:
    """Serialize features dictionary to a JSON string for database storage."""
    return json.dumps(features, default=str)