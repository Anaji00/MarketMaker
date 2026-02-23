"""
Financial Modeling Prep (FMP) API Adapter.

Handles alternative data fetching with:
- Async-first design (non-blocking I/O)
- Built-in rate limiting (respect API quotas)
- Exponential backoff retry logic
- Circuit breaker pattern for failure isolation
"""

from __future__ import annotations

import logging
import asyncio
from datetime import datetime, timedelta
import httpx
from typing import Any
from collections import deque

log = logging.getLogger("services.fmp_adapter")

class RateLimiter:
    """
    Token bucket rate limiter.
    Prevents exceeding FMP's 5 req/min and 250 req/day limits.
    
    Concept: Sliding Window Log
    We store the timestamp of every request in a queue (deque).
    To check if we can make a request, we look at how many timestamps 
    fall within the last minute/day.
    """
    def __init__(self, per_minute: int, per_day: int):
        self.per_minute = per_minute
        self.per_day = per_day

        # Deques are optimized for adding/removing from ends (O(1)).
        self.minute_calls: deque[datetime] = deque()
        self.day_calls: deque[datetime] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Block until a request slot is available."""
        async with self._lock:
            now = datetime.now()

            # 1. Clean up old timestamps (Slide the window)
            minute_ago = now - timedelta(minutes=1)
            while self.minute_calls and self.minute_calls[0] < minute_ago:
                self.minute_calls.popleft()
            day_ago = now - timedelta(days=1)
            while self.day_calls and self.day_calls[0] < day_ago:
                self.day_calls.popleft()
            # 2. Check Limits
            if len(self.minute_calls) >= self.per_minute:
                wait_time = 60 -(now - self.minute_calls[0]).total_seconds()
                log.warning("Rate limit hit: waiting %.2f seconds for minute window", wait_time)
                await asyncio.sleep(wait_time)
                return await self.acquire()  # Re-check after waiting

            if len(self.day_calls) >= self.per_day:
                wait_time = 86400 - (now - self.day_calls[0]).total_seconds()
                log.warning("Daily rate limit hit: waiting %.2f seconds for day window", wait_time)
                await asyncio.sleep(wait_time)
                return await self.acquire()  # Re-check after waiting
            
            # 3. Consume Token
            # Record the current timestamp for both windows
            self.minute_calls.append(now)
            self.day_calls.append(now)

class CircuitBreaker:
    """
    Prevents cascading failures by stopping requests to a failing endpoint.
    
    Pattern: Circuit Breaker
    - CLOSED: Normal operation. Requests flow through.
    - OPEN: Too many failures. Requests are blocked immediately (fail fast).
    - HALF_OPEN: After a timeout, we let ONE request through to test if the service recovered.
    """
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time: datetime | None = None
        self.state = "CLOSED"

    def call_succeeded(self) -> None:
        """Reset on success."""
        self.failures = 0
        self.last_failure_time = None
        self.state = "CLOSED"
    
    def call_failed(self) -> None:
        """Record a failure and potentially open the circuit."""
        self.failures += 1
        self.last_failure_time = datetime.utcnow()
        if self.failures >= self.failure_threshold:
            self.state = "OPEN"
            log.error("Circuit breaker OPEN: %d failures", self.failures)

    def can_attempt(self) -> bool:
        """Check if we can attempt a call."""
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            if self.last_failure_time:
                elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
                if elapsed >= self.timeout:
                    self.state = "HALF_OPEN"
                    log.info("Circuit breaker HALF_OPEN: timeout elapsed")
                    return True
            return False
        
        return True  # HALF_OPEN allows one attempt
    
class FMPAdapter:
    """
    Async adapter for Financial Modeling Prep API.
    
    Key improvements over Quiver:
    - Fully async (no blocking I/O)
    - Rate limiting built-in
    - Automatic retries with exponential backoff
    - Circuit breaker for resilience
    """
    BASE_URL = "https://financialmodelingprep.com/api/v3"

    def __init__(self, api_key: str | None, rate_limit_per_minute: int, rate_limit_per_day: int):
        self.api_key = api_key
        self.rate_limiter = RateLimiter(rate_limit_per_minute, rate_limit_per_day)
        self.circuit_breaker = CircuitBreaker()

        if not api_key:
            log.warning("FMP API key not set, FMP adapter disabled")

    def enabled(self) -> bool:
        return self.api_key is not None
    
    async def _request(
        self, 
        endpoint: str,
        params: dict[str, Any] | None = None,
        max_retries: int = 3
    ) -> list[dict[str, Any]]:
        """
        Core HTTP request with retry logic and circuit breaking.
        """
        if not self.enabled():
            return []
        if not self.circuit_breaker.can_attempt():
            log.warning("Circuit breaker OPEN, skipping FMP request to %s", endpoint)
            return []
        
        # Build Request URL and Parameters
        params = params or {}
        params["apikey"] = self.api_key
        url = f"{self.BASE_URL}/{endpoint}"
        
        # Retry loop with Exponential Backoff
        # Attempt 1: wait 0s (if fail)
        # Attempt 2: wait 2s (if fail)
        # Attempt 3: wait 4s ...

        for attempt in range(max_retries):
            try:
                await self.rate_limiter.acquire()  # Ensure we respect rate limits
                async with httpx.AsyncClient(timeout=15) as client:
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    data = response.json()
                    self.circuit_breaker.call_succeeded()  # Reset circuit on success

                    if isinstance(data, list):
                        return data
                    elif isinstance(data, dict) and "Error Message" in data:
                        log.error(f"FMP API error: {data['Error Message']}")
                        return []
                    else:
                        log.warning("Unexpected FMP response format: %s", data)
                        return []
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    wait_time = 2 ** attempt  # Exponential backoff: 1, 2, 4, 8...
                    log.warning(f"Rate limit 429, retry in {wait_time}s")
                    await asyncio.sleep(wait_time)
                    continue
                elif e.response.status_code >= 500:
                    wait_time = 2 ** attempt
                    log.error(f"Server error {e.response.status_code}, retry in {wait_time}s")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    log.error(f"HTTP error {e.response.status_code}: {e}")
                    self.circuit_breaker.call_failed()
                    return []            
            except Exception as e:
                log.exception(f"Error during FMP request: {e}")
                self.circuit_breaker.call_failed()
                return []
            
        return []
    
    async def fetch_insider_trades(self, symbol: str) -> list[dict[str, Any]]:
        """
        Fetch recent insider trading (Form 4 filings).
        
        API: https://financialmodelingprep.com/api/v4/insider-trading
        """
        params = {"page": "0"}
        if symbol:
            params["symbol"] = symbol.upper()
        
        trades = await self._request("v4/insider-trading", params)

        normalized = []
        for trade in trades:
            normalized.append({
                "Ticker": trade.get("symbol", "").upper(),
                "Transaction": trade.get("transactionType", ""),
                "Value": float(trade.get("securitiesTransacted", 0.0)) * float(trade.get("price", 0.0)),
                "Date": trade.get("filingDate", ""),
                "Insider": trade.get("reportingName", ""),
                "raw": trade
            })
        return normalized
    
    def _parse_amount(self, amount_str: str) -> float:
        """
        Parse FMP's amount ranges into midpoint estimates.
        
        FMP returns ranges like "$1,001 - $15,000" or "$50,001 - $100,000"
        We extract the midpoint for numerical analysis.
        """
        if not amount_str or amount_str == "N/A":
            return 0.0
        
        try:
            #Remove dollar signs and commas
            cleaned = amount_str.replace("$", "").replace(",", "")
            if "-" in cleaned:
                parts = cleaned.split("-")
                low = float(parts[0].strip())
                high = float(parts[1].strip())
                return (low + high) / 2.0
            
            return float(cleaned.strip())
        
        except Exception as e:
            log.warning(f"Failed to parse amount '{amount_str}': {e}")
            return 0.0