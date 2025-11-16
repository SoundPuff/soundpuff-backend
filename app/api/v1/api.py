from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, playlists

api_router = APIRouter()

# Authentication endpoints
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"],
)

# User endpoints
api_router.include_router(
    users.router,
    prefix="/users",
    tags=["Users"],
)

# Playlist endpoints
api_router.include_router(
    playlists.router,
    prefix="/playlists",
    tags=["Playlists"],
)
