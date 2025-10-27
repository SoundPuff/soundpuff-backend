from sqlalchemy import Column, Integer, ForeignKey, Table
from app.db.base_class import Base

# Association table for many-to-many relationship between Playlist and Song
playlist_songs = Table(
    "playlist_songs",
    Base.metadata,
    Column("playlist_id", Integer, ForeignKey("playlists.id", ondelete="CASCADE"), primary_key=True),
    Column("song_id", Integer, ForeignKey("songs.id", ondelete="CASCADE"), primary_key=True),
    Column("position", Integer, nullable=False, default=0)
)