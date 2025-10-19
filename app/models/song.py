from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base
from app.models.playlist import playlist_songs


class Song(Base):
    __tablename__ = "songs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)
    artist = Column(String(100), nullable=False)
    album = Column(String(100), nullable=True)
    duration = Column(Integer, nullable=True)  # duration in seconds
    spotify_id = Column(String(100), unique=True, index=True, nullable=True)
    preview_url = Column(String(255), nullable=True)
    cover_image_url = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    playlists = relationship("Playlist", secondary=playlist_songs, back_populates="songs")
