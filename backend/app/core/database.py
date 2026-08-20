from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
)


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# Ensure all models are imported so metadata is complete before
# create_all / migrations run. Without these imports, SQLAlchemy
# may skip tables whose model modules were not yet loaded.
from app.models.project import Project  # noqa: E402
from app.models.document import Document  # noqa: E402
from app.models.document_chunk import DocumentChunk  # noqa: E402
from app.models.github import AppUser, GitHubInstallation, GitHubRepository  # noqa: E402
from app.models.chat import ChatMessage  # noqa: E402