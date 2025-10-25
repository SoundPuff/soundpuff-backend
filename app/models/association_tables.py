"""Association tables for many-to-many relationships"""
from sqlalchemy import Column, DateTime, Table, BigInteger, ForeignKey
from sqlalchemy.sql import func
from app.db.base_class import Base


# Association table for many-to-many relationship between Playlist and Song
playlist_songs = Table(
    "playlist_songs",
    Base.metadata,
    Column("playlist_id", BigInteger, ForeignKey("playlists.id", ondelete="CASCADE"), primary_key=True),
    Column("song_id", BigInteger, ForeignKey("songs.id", ondelete="CASCADE"), primary_key=True),
    Column("added_at", DateTime(timezone=True), server_default=func.now())
)
