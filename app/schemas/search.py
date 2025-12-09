from pydantic import BaseModel
from typing import List, Optional
from enum import Enum

from app.schemas.user import User
from app.schemas.song import Song
from app.schemas.playlist import Playlist


class SearchType(str, Enum):
    """Type of search to perform"""
    ALL = "all"
    USERS = "users"
    SONGS = "songs"
    PLAYLISTS = "playlists"


class UserSearchResult(BaseModel):
    """User with optional relevance score for search ranking"""
    user: User
    relevance: Optional[float] = None  # 0.0 to 1.0, higher = more relevant

    class Config:
        from_attributes = True


class SongSearchResult(BaseModel):
    """Song with optional relevance score for search ranking"""
    song: Song
    relevance: Optional[float] = None

    class Config:
        from_attributes = True


class PlaylistSearchResult(BaseModel):
    """Playlist with optional relevance score for search ranking"""
    playlist: Playlist
    relevance: Optional[float] = None

    class Config:
        from_attributes = True


class SearchResults(BaseModel):
    """
    Combined search results across all types.
    
    Search should support partial matching:
    - Query "ar" should match "arda", "ariana", "guitar", etc.
    - Results should be ordered by relevance when possible
    """
    query: str
    users: List[UserSearchResult] = []
    songs: List[SongSearchResult] = []
    playlists: List[PlaylistSearchResult] = []
    total_users: int = 0
    total_songs: int = 0
    total_playlists: int = 0

    class Config:
        from_attributes = True


class UserSearchResults(BaseModel):
    """Search results for users only"""
    query: str
    users: List[UserSearchResult] = []
    total: int = 0

    class Config:
        from_attributes = True


class SongSearchResults(BaseModel):
    """Search results for songs only"""
    query: str
    songs: List[SongSearchResult] = []
    total: int = 0

    class Config:
        from_attributes = True


class PlaylistSearchResults(BaseModel):
    """Search results for playlists only"""
    query: str
    playlists: List[PlaylistSearchResult] = []
    total: int = 0

    class Config:
        from_attributes = True
