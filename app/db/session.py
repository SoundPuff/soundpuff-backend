from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Keep the pool tiny to avoid exhausting Supabase Session-mode limits.
engine = create_engine(
    settings.db_url,
    pool_pre_ping=True,
    pool_size=1,
    max_overflow=0,
    pool_timeout=10,
    pool_recycle=1800,
    pool_reset_on_return="commit",
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
