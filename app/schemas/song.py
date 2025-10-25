from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class SongBase(BaseModel):
    title: str
    artist: str
    album_art_url: Optional[str] = None
    song_url: str


class SongCreate(SongBase):
    pass


class SongInDB(SongBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class Song(SongInDB):
    pass
