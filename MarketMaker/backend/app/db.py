from __future__ import annotations
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings

class Base(DeclarativeBase):
    pass

# Now, we create the Database Engine.
# This is a Singleton object that manages the connection pool to the database.
# - pool_size=5: Keep 5 connections open and ready.
# - max_overflow=10: Allow spiking up to 15 connections during heavy load.
# - pool_pre_ping=True: Check if connection is alive before using it (prevents "server closed the connection unexpectedly" errors).
engine = create_engine(
    settings.database_url,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    )

# Now, we create a Session Factory.
# This factory will generate new Session objects for each request or task.
# autoflush=False: We want control over when SQL is emitted.
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def init_db():
    from app import models  # Import models to register them with Base
    Base.metadata.create_all(bind=engine)
    