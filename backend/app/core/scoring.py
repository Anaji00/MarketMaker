"""
Scoring Engine Module.

Concept: Hybrid Scoring Architecture.
We combine two different types of intelligence:
1. Unsupervised Learning (Anomaly Detection): "Is this weird?"
   - Uses Isolation Forest to find statistical outliers.
2. Heuristic/Supervised Learning (Classification): "What is this?"
   - Uses expert rules (and later ML) to assign a label (e.g., "Bullish Options").
"""
from __future__ import annotations
import math
from app.ml.classifier import heuristic_label
from app.ml.isolation_forest import IsoForestScorer

def enrich_features(features: dict, notional: float) -> dict:
    """
    Add generic cross-source features so the ML sees consistent fields.
    """
    f = dict(features)  # Copy to avoid mutating input
    
    # Now, we apply Log Transformation to the Notional value.
    # Financial data follows a "Power Law" (Pareto distribution).
    # A $1M trade is not just 10x a $100k trade in impact; the scale is exponential.
    # Log(1+x) compresses this huge range into a linear scale that ML models can handle better.
    f["notional_log"] = float(math.log1p(max(notional, 0.0)))
    return f

class ScoringEngine:
    """
    Central coordinator for signal evaluation.
    Holds state for the ML models (like the trained Isolation Forest).
    """
    def __init__(self):
        self.iso = IsoForestScorer()
    
    def fit_anomaly_model(self, feature_dicts: list[dict]) -> None:
        """Train the unsupervised anomaly detector on historical data."""
        self.iso.fit(feature_dicts)

    def score(self, source: str, kind: str, features: dict, raw: dict, notional: float) -> dict:
        """
        Run the full scoring pipeline on a new signal.
        
        Returns:
            dict: Combined result containing enriched features, anomaly score, and label.
        """
        # 1. Preprocessing: Enrich features with cross-cutting data (like notional).
        f = enrich_features(features, notional)
        
        # 2. Unsupervised Scoring: Ask the Isolation Forest "How weird is this vector?".
        a = self.iso.score(f)
        
        # 3. Heuristic Scoring: Ask the Expert Rules "What category is this?".
        label, confidence = heuristic_label(source, kind, f, raw)
        
        return {
            "features": f,
            "anomaly_score": a,
            "class_label": label,
            "class_confidence": confidence,
        }