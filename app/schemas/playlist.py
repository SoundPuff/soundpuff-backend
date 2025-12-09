from pydantic import BaseModel
from typing import Optional, List, Literal
from datetime import datetime
from uuid import UUID
from app.schemas.user import User
from app.schemas.song import Song


class PlaylistBase(BaseModel):
    title: str
    description: Optional[str] = None
    privacy: Literal["public", "private"] = "public"


class PlaylistCreate(PlaylistBase):
    pass


class PlaylistUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    privacy: Optional[Literal["public", "private"]] = None
    


class PlaylistInDB(PlaylistBase):
    id: int
    user_id: UUID
    privacy: Literal["public", "private"]
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Playlist(PlaylistInDB):
    owner: User
    songs: List[Song] = []
    likes_count: int = 0
    comments_count: int = 0
