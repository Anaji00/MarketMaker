from __future__ import annotations

import logging
import numpy as np
from sklearn.ensemble import IsolationForest

log = logging.getLogger("ml.isolation_forest")

# Now, we define the Feature Vector Schema.
# ML models operate on Matrices (2D arrays of numbers), not Dictionaries.
# We must enforce a strict order of columns.
# Column 0 is always 'ret_1', Column 1 is always 'vol_z', etc.
FEATURE_ORDER = [
    "ret_1",
    "vol_z",
    "ret_vol_20",
    "call_put_oi_ratio",
    "call_put_vol_ratio",  # Must match key in features.py
    "notional_log",
]

def _vectorize(features: dict) -> np.ndarray:
    """
    Convert a feature dictionary into a fixed-order numpy array (Vectorization).
    """
    vec = []
    for feat in FEATURE_ORDER:
        # Now, we perform Imputation.
        # Missing data is common (e.g., a stock might not have options data).
        # We cannot pass 'None' to the math model.
        # We fill missing values with 0.0, which acts as a "neutral" signal in this context.
        val = features.get(feat, 0.0)
        try:
            vec.append(float(val))
        except Exception as e:
            vec.append(0.0)
    # Return as a 1D array of floats
    return np.array(vec, dtype=np.float64)

class IsoForestScorer:
    """
    Wrapper for Scikit-Learn's Isolation Forest. 
    Concept: Unsupervised Anomaly Detection.
    The model builds random decision trees. Anomalies are easy to isolate (shallow depth),
    while normal points are hard to isolate (deep depth).
    """
    def __init__(self) -> None:
        # Type hint for the model (initially None until fit() is called)
        self.model: IsolationForest | None = None

    def fit(self, feature_dicts: list[dict]) -> None:
        """
        Train (Fit) the model on historical data.
        """
        # Now, we convert the list of dictionaries into a Numpy Matrix (X).
        # Rows = Samples, Columns = Features.
        X = np.vstack([_vectorize(f) for f in feature_dicts]) if feature_dicts else None
        
        # Now, we check for sufficiency.
        # Isolation Forest needs a baseline of "normal" behavior.
        # If we have < 50 points, the statistical significance is too low.
        if X is None or len(X) < 50:
            log.warning("not enough data to fit IsoForestScorer")
            self.model = None
            return
        
        # Hyperparameters:
        # n_estimators: Number of trees in the forest (more = more stable, slower).
        # contamination: Our prior belief about how much of the dataset is anomalous (5%).
        self.model = IsolationForest(
            n_estimators=200,
            contamination=0.05,
            random_state=42,
        )
        self.model.fit(X)
        log.info("IsoForestScorer model fitted on %d rows", len(X))

    def score(self, features: dict) -> float:
        """
        Score a new signal.
        Returns:
            float: 0.0 (very normal) to 1.0 (highly anomalous).
        """
        if self.model is None:
            return 0.0
        
        # Now, we prepare the single sample for prediction.
        # Sklearn expects a 2D array even for a single sample, so we reshape to (1, n_features).
        X = _vectorize(features).reshape(1, -1)

        # Now, we get the raw decision function score.
        # Positive = Normal, Negative = Anomalous.
        normality = float(self.model.decision_function(X)[0])
        
        # Now, we normalize the score using a Sigmoid function.
        # The raw score is unbounded and unintuitive.
        # We want a probability-like score: 0.0 (Normal) to 1.0 (Anomaly).
        # The formula 1 / (1 + exp(5 * normality)) inverts and squashes the value.
        score = 1.0 / (1.0 + np.exp(5.0 * normality))
        return float(score)
    