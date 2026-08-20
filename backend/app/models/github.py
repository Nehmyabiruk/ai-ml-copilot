from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.project import Project


class AppUser(Base):
    __tablename__ = "app_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_token: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    github_login: Mapped[str | None] = mapped_column(String(255), nullable=True)
    github_account_id: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True)
    github_oauth_state: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    projects: Mapped[list["Project"]] = relationship(back_populates="owner")
    installations: Mapped[list["GitHubInstallation"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class GitHubInstallation(Base):
    __tablename__ = "github_installations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Made nullable because pure OAuth does not have a real installation_id
    installation_id: Mapped[int | None] = mapped_column(Integer, unique=True, index=True, nullable=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("app_users.id", ondelete="CASCADE"), index=True)
    account_login: Mapped[str] = mapped_column(String(255))

    # NEW – store the OAuth access token here
    access_token: Mapped[str | None] = mapped_column(String(512), nullable=True)
    refresh_token: Mapped[str | None] = mapped_column(String(512), nullable=True)   # ← NEW
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["AppUser"] = relationship(back_populates="installations")
    repositories: Mapped[list["GitHubRepository"]] = relationship(
        back_populates="installation", cascade="all, delete-orphan"
    )


class GitHubRepository(Base):
    __tablename__ = "github_repositories"
    __table_args__ = (
        UniqueConstraint("installation_id", "github_repository_id", name="uq_installation_repository"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    installation_id: Mapped[int] = mapped_column(
        ForeignKey("github_installations.id", ondelete="CASCADE"), index=True
    )
    github_repository_id: Mapped[int] = mapped_column(Integer, index=True)
    full_name: Mapped[str] = mapped_column(String(500))
    default_branch: Mapped[str] = mapped_column(String(255), default="main")

    installation: Mapped["GitHubInstallation"] = relationship(back_populates="repositories")
    projects: Mapped[list["Project"]] = relationship(back_populates="github_repository")