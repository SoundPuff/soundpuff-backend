from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime
from uuid import UUID
from app.schemas.user import User
from app.schemas.song import Song


class PlaylistBase(BaseModel):
    title: str
    description: Optional[str] = None
    privacy: Literal["public", "private"] = "public"
    cover_image_url: Optional[str] = None


class PlaylistCreate(PlaylistBase):
    song_ids: Optional[List[int]] = None  # Songs to add during playlist creation


class PlaylistUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    privacy: Optional[Literal["public", "private"]] = None
    cover_image_url: Optional[str] = None
    song_ids: Optional[List[int]] = None
    


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
    songs: List[Song] = Field(default_factory=list)
    likes_count: int = 0
    comments_count: int = 0
    is_liked: Optional[bool] = None


class PlaylistAddSong(BaseModel):
    song_id: int
    # Pydantic v2 configuration for additional JSON schema info
    model_config = {
        "json_schema_extra": {"example": {"song_id": 123}}
    }
