from __future__ import annotations
from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()

# Now, we define the Settings class.
# We use @dataclass(frozen=True) to make this immutable.
# Once settings are loaded, they should not change during runtime.
@dataclass(frozen=True)
class Settings:
    # Now, we fetch the Database URL.
    # We provide a sensible default for local development (PostgreSQL).
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://marketmaker:marketmakerpass@db:5432/marketmaker"
    )

    # Now, we parse the Stock Watchlist.
    # The env var is a comma-separated string ("AAPL,TSLA").
    # We split it, strip whitespace, and uppercase it to ensure consistency.
    stock_watchlist: list[str] = tuple(
        s.strip().upper()
        for s in os.getenv("STOCK_WATCHLIST", "AAPL,GOOGL,AMD,AMZN,TSLA").split(",")
        if s.strip()
    )

    polymarket_query: str = os.getenv("POLYMARKET_QUERY","election")
    poll_interval_seconds: int = int(os.getenv("POLL_INTERVAL_SECONDS", "120"))
    sec_user_agent: str | None = os.getenv("SEC_USER_AGENT", "MarketMaker alessionaji1@gmail.com")
    anomaly_threshold: float = float(os.getenv("ANOMALY_THRESHOLD", "0.75"))

    # FMP config
    fmp_api_key: str | None = os.getenv("FMP_API_KEY", None)
    fmp_rate_limit_per_minute: int = int(os.getenv("FMP_RATE_LIMIT_PER_MINUTE", "5"))
    fmp_rate_limit_per_day: int = int(os.getenv("FMP_RATE_LIMIT_PER_DAY", "250"))

settings = Settings()