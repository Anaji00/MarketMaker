from __future__ import annotations
import logging
from fastapi import FastAPI
from app.db import init_db
from app.logging import setup_logging
from app.core.scheduler import start_scheduler, scheduler
from app.config import settings

from app.router.health import router as health_router
from app.router.alerts import router as alerts_router
from app.router.admin import router as admin_router
from app.router.signals import router as signals_router

from app.db import SessionLocal 
from app.core.ingest import ingest_stocks_and_options,ingest_quiver_altdata, ingest_polymarket, refit_models_from_db

setup_logging()
log = logging.getLogger("app.main")

app = FastAPI(title="MarketMaker", version="0.1.0")

app.include_router(health_router)
app.include_router(signals_router)
app.include_router(alerts_router)
app.include_router(admin_router)

@app.on_event("startup")
async def startup():
    # Now, we initialize the database schema (create tables if missing).
    init_db()
    log.info("DB initialized.")
    # Now, we start the background scheduler.
    start_scheduler()

    # Now, we perform Model Bootstrapping.
    # We create a temporary DB session to fetch historical data and train the Isolation Forest.
    # This ensures the model is ready to score new signals immediately upon startup.
    db = SessionLocal()
    try:
        refit_models_from_db(db)
        log.info("Bootstrapped anomaly models from DB.")
    finally:
        db.close()
    
    # Now, we schedule the "Tick" job.
    scheduler.add_job(_job_tick, "interval", seconds=settings.poll_interval_seconds, id="tick", replace_existing=True)
    log.info("Scheduler started with tick interval of %d seconds.", settings.poll_interval_seconds)

async def _job_tick():
    """
    The "Heartbeat" of the application.
    This function runs every X seconds to fetch new data.
    """
    # Now, we create a fresh DB session for this tick.
    # This ensures thread safety and proper transaction isolation.
    db = SessionLocal()
    try:
        # Now, we run the ingestion pipelines sequentially.
        # We use 'await' for async IO operations (Polymarket).
        await ingest_stocks_and_options(db)
        await ingest_polymarket(db)
        # Quiver is synchronous, so we call it directly.
        ingest_quiver_altdata(db)
    finally:
        # Now, we explicitly close the session to return the connection to the pool.
        db.close()