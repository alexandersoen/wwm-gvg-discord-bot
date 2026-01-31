from typing import Generator
from sqlmodel import create_engine, Session, SQLModel

DATABASE_URL = "sqlite:///./data/prod.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def init_db():
  from core.models import SignupConfig  # noqa: F401
  SQLModel.metadata.create_all(engine)


def get_session_context() -> Session:
  return Session(engine)


def get_db_yield() -> Generator[Session, None, None]:
  """Will be useful for webapp."""
  with get_session_context() as session:
    yield session
