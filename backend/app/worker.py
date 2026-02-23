import asyncio
import logging
from app.log import setup_logging
from app.db import init_db, SessionLocal
from app.core.ingest import ingest_stocks_and_options, ingest_polymarket, ingest_quiver_altdata, refit_models_from_db

setup_logging()
log = logging.getLogger("worker")

async def main():
    init_db()
    db = SessionLocal()
    try:
        refit_models_from_db(db)
        await ingest_stocks_and_options(db)
        await ingest_polymarket(db)
        ingest_quiver_altdata(db)
        log.info("One-shot ingest complete.")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
