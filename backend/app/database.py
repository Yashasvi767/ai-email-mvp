from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from . import models
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/app.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(bind=engine, autoflush=False)

def init_db():
    models.Base.metadata.create_all(bind=engine)

# context manager for sessions
from contextlib import contextmanager
@contextmanager
def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
