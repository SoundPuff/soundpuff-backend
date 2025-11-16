from sqlalchemy import Column, BigInteger, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base


class Comment(Base):
    __tablename__ = "comments"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    body = Column(Text, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    playlist_id = Column(BigInteger, ForeignKey("playlists.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="comments")
    playlist = relationship("Playlist", back_populates="comments")
