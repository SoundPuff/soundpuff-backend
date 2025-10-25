from sqlalchemy import Column, BigInteger, String, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base
from app.models.association_tables import playlist_songs


class Song(Base):
    __tablename__ = "songs"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    title = Column(Text, nullable=False)
    artist = Column(Text, nullable=False)
    album_art_url = Column(Text, nullable=True)
    song_url = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    playlists = relationship("Playlist", secondary=playlist_songs, back_populates="songs")
