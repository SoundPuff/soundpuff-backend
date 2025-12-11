from typing import List, Optional
from pydantic import BaseModel
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

class SongListResponse(BaseModel):
    total: int
    songs: List[Song]

    class Config:
        from_attributes = True