from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, or_
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Song
from app.schemas.search import SongSearchResult, SongSearchResults


router = APIRouter()


@router.get("/search", response_model=SongSearchResults)
def search_songs(
    query: str,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """Search songs by title or artist using a case-insensitive partial match."""

    if not query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query parameter cannot be empty",
        )

    search_filter = or_(
        Song.title.ilike(f"%{query}%"),
        Song.artist.ilike(f"%{query}%"),
    )

    base_query = db.query(Song).filter(search_filter)
    total = base_query.count()

    songs = (
        base_query.order_by(desc(Song.created_at)).offset(offset).limit(limit).all()
    )

    song_results = [SongSearchResult(song=song) for song in songs]

    return SongSearchResults(query=query, songs=song_results, total=total)