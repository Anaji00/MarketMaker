"""
Heuristic Classifier Module.

Concept: The "Cold Start" Problem.
We don't have a labeled dataset of "Pumps" vs "Dumps" yet.
So, we cannot train a Supervised Learning model (like a Random Forest).
Instead, we use "Heuristics" (Expert Rules) to label data initially.
This allows the system to provide value immediately while we collect data for future training.
"""
from __future__ import annotations

def heuristic_label(source: str, kind: str, features: dict, raw: dict) -> tuple[str, float]:
    """
    Apply expert rules to assign a label and confidence score to a signal.
    
    Args:
        source: The origin of the signal (e.g., "STOCK", "OPTIONS", "CONGRESS").
        kind: The raw type of event.
        features: Computed numerical features (e.g., z-scores, ratios).
        raw: The original raw data payload.
        
    Returns:
        tuple[str, float]: (Label, Confidence Score 0.0-1.0)
    """
    # Now, we normalize inputs to ensure case-insensitive matching.
    source = source.upper()
    kind = kind.lower()

    # Now, we check for High-Signal Sources.
    # These are "Axiomatic Truths" in our domain.
    # If a Congress member trades, it IS a congress trade. Confidence = 0.9 (High).
    if source == "CONGRESS":
        return ("congress_trade", 0.9)
    if source == "SENATE":
        return ("senate_trade", 0.9)
    if source == "INSIDER":
        return ("insider_trade", 0.9)
    if source == "POLY":
        return ("polymarket_move", 0.7)
    
    # Now, we apply Financial Heuristics for Options.
    # We look at the Call/Put Ratio.
    # > 3.0 means 3x more calls than puts -> Bullish.
    # < 0.33 means 3x more puts than calls -> Bearish.
    if source == "OPTIONS":
        cpr = float(features.get("call_put_vol_ratio", 1.0))
        if cpr >= 3.0:
            return ("bullish_options_skew", 0.75)
        if cpr <= 0.33:
            return ("bearish_options_skew", 0.75)
        return ("options_activity", 0.50)
    
    # Now, we apply Technical Analysis rules for Stocks.
    # We define a "Spike" as:
    # 1. Price moved > 2% in the last period.
    # 2. Volume is > 2 Standard Deviations above the mean (Z-score > 2).
    if source == "STOCK":
        r = float(features.get("ret_1", 0.0))
        vz = float(features.get("vol_z", 0.0))

        # Volume Spike detection
        if abs(r) > 0.02 and abs(vz) > 2.0:
            return ("price_volume_spike", 0.7)
        
        #High bol regime

        vol_20 = float(features.get("ret_vol_20", 0.0))
        if vol_20 > 0.03:
            return ("high_volatility", 0.60)
        return ("stock_move", 0.4)
    
    # Default fallback for unrecognized signals
    return ("unknown", 0.1)