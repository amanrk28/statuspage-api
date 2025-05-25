from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from app.config import settings
from contextlib import contextmanager

engine = create_engine(settings.DATABASE_URL, pool_size=50, max_overflow=0)
Base = declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@contextmanager
def get_db():
    db: Session = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        print("Rolling back operation", e)
        db.rollback()
    finally:
        db.close()

def get_db_session():
    return SessionLocal()
