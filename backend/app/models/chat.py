from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
if TYPE_CHECKING:
    from app.models.project import Project
class ChatMessage(Base):
    __tablename__= "chat_messages"
    id:Mapped[int]=mapped_column(Integer,primary_key=True,index=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str]=mapped_column(
        Text,
        nullable=False,
    )
    content: Mapped[str] =mapped_column(
        Text,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="chat_messages",
    )



    