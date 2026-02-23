import logging

def setup_logging() -> None:
    # Now, we configure the global logging system.
    # We use a predictable format including Timestamp, Log Level, Logger Name, and Message.
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
