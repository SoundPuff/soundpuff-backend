from sqlalchemy import Column, String, DateTime, Text, ForeignKey, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base
from app.models.association_tables import playlist_songs


class Playlist(Base):
    __tablename__ = "playlists"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    cover_image_url = Column(String(255), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships (using lazy='select' to defer loading until needed)
    owner = relationship("User", back_populates="playlists", lazy="select")
    songs = relationship("Song", secondary=playlist_songs, back_populates="playlists", lazy="select")
    comments = relationship("Comment", back_populates="playlist", cascade="all, delete-orphan", lazy="select")
    likes = relationship("Like", back_populates="playlist", cascade="all, delete-orphan", lazy="select")
