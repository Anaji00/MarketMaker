"""
Model Persistence Module.

Training a machine learning model (like the IsolationForest) can be computationally
expensive. We don't want to retrain the model every time the application restarts.

"Persistence" is the process of saving the trained model's state to disk.
This module provides simple functions to save (serialize) and load (deserialize)
any Python object, typically a trained model, using the `pickle` library.
"""
from __future__ import annotations
import os 
import pickle
from typing import Any
import logging

log = logging.getLogger("ml.model_store")

# Now, we establish Robust Path Management.
# Instead of relying on relative paths (which break depending on where you run the script from),
# we calculate the absolute path relative to this file's location.
# 1. Get the directory of this script: .../backend/app/ml/
# 2. Go up two levels to the project root: .../backend/
# 3. Point to the 'models' folder.
# This ensures the application is portable across different environments.
MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "models")
# Now, we ensure the directory exists. If it's missing, we create it (mkdir -p).
os.makedirs(MODEL_DIR, exist_ok=True)

def save_pickle(name: str, obj: Any) -> None:
    """
    Serialize and save a Python object to a file in the model directory.

    Args:
        name (str): The base name for the model file (e.g., "iso_forest").
        obj (Any): The Python object to save (e.g., a trained sklearn model).
    """
    # Now, we construct the full file path.
    path = os.path.join(MODEL_DIR, f"{name}.pkl")
    # Now, we open the file in binary write mode ('wb').
    # We use the 'pickle' protocol to serialize the Python object structure into bytes.
    with open(path, "wb") as f:
        pickle.dump(obj, f)
    log.info("Saved model '%s' to %s", name, path)
    return path

def load_pickle(name: str) -> Any | None:
    """
    Load and deserialize a Python object from a file in the model directory.

    SECURITY WARNING: `pickle` is not secure. Only unpickle data you trust.
    Loading a malicious pickle file can result in arbitrary code execution.
    """
    # Now, we resolve the path again.
    path = os.path.join(MODEL_DIR, f"{name}.pkl")
    # Now, we check for existence to avoid crashing with a FileNotFoundError.
    # This allows the calling code to handle the "cold start" (no model yet) gracefully.
    if not os.path.exists(path):
        return None
    # Now, we deserialize the bytes back into a Python object.
    with open(path, "rb") as f:
        obj = pickle.load(f)
        log.info("Loaded model '%s' from %s", name, path)
        return obj