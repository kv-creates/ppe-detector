"""SQLite store for violation incidents (SQLAlchemy)."""
from __future__ import annotations

import os

from sqlalchemy import Column, Float, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DB_PATH = os.path.abspath("data/violations.db")
ENGINE = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=ENGINE)
Base = declarative_base()


class Violation(Base):
    __tablename__ = "violations"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(String, index=True)
    camera_id = Column(String, index=True)
    class_name = Column(String, index=True)
    conf = Column(Float)
    zone = Column(String)
    snapshot_path = Column(String, nullable=True)


def init_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    Base.metadata.create_all(bind=ENGINE)


def get_session():
    return SessionLocal()
