"""
Service adapter for Quiver Quantitative API.
Handles fetching alternative data like congressional trading and insider trading.
"""
from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger("services.quiver")

class QuiverAdapter:
    """
    Adapter around the Quiver API Python package.
    Design Pattern: Adapter / Wrapper.
    We wrap the third-party `quiverquant` library to:
    1. Isolate dependencies: If we change vendors, we only change this file.
    2. Handle errors centrally: If the API fails, the rest of the app shouldn't crash.
    3. Provide a consistent interface: The rest of the app just calls `fetch_congress_trades`.
    """
    def __init__(self, token: str | None):
        """
        Initialize the QuiverAdapter.

        Args:
            token (str | None): The API token for Quiver Quantitative. 
          If None, the adapter starts in a disabled state.
        """
        self.token = token
        self.client = None

        # Now, we check for the API token.
        # If it's missing, we log a warning but do NOT crash. We just disable this feature.
        if not token:
            log.warning("QUIVER API TOKEN not set, quiver disabled")
            return
        
        try:
            # Now, we attempt a Dynamic Import.
            # This is a "Soft Dependency". The app can run without `quiverquant` installed.
            import quiverquant  # type: ignore
            self.client = quiverquant.quiver(token)
            log.info("Quiver adapter initialized")
        except Exception as e:
            # Catch initialization errors (e.g., library not found, network issues)
            log.exception("Failed to initialize Quiver client: %s", e)
            self.client = None
    
    def enabled(self) -> bool:
        """
        Check if the Quiver client is successfully initialized.

        Returns:
            bool: True if client is ready, False otherwise.
        """
        return self.client is not None
    
    def fetch_congress_trades(self) -> list[dict[str, Any]]:
        """
        Fetch recent congressional trading data.

        Returns:
            list[dict[str, Any]]: A list of dictionaries representing trades.
                                  Returns empty list on failure or if disabled.
        """
        if not self.client:
            return []
        try:
            # Now, we call the external API.
            rows = self.client.congress_trading()
            # Now, we validate the response type.
            # External APIs are unpredictable; we ensure we return a list, never None or an object.
            return rows if isinstance(rows, list) else []
        except Exception as e:
            log.exception("Error fetching congress trades: %s", e)
            return []
        
    def fetch_insider_trades(self) -> list[dict[str, Any]]:
        """
        Fetch recent insider trading data.

        Returns:
            list[dict[str, Any]]: A list of dictionaries representing insider trades.
                                  Returns empty list on failure or if disabled.
        """
        if not self.client:
            return []
        try:
            # Fetch insider trading data from the API
            rows = self.client.insider_trading()
            # Validate return type
            return rows if isinstance(rows, list) else []
        except Exception as e:
            log.exception("Error fetching insider trades: %s", e)
            return []
