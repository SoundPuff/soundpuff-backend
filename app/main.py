from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

from app.core.config import settings
from app.api.v1.api import api_router

# Import all models at startup to ensure they're registered with SQLAlchemy
from app.models import User, Playlist, Song, Comment, Like, Follow  # noqa: F401

tags_metadata = [
    {
        "name": "Authentication",
        "description": "User authentication with Supabase Auth. Sign up and login to get an access token.",
    },
    {
        "name": "Users",
        "description": "User profile management, follow/unfollow operations, and user discovery.",
    },
    {
        "name": "Playlists",
        "description": "Create, manage, and discover music playlists. Like, comment, and add songs to playlists.",
    },
    {
        "name": "Songs",
        "description": "Search and discover songs available in the catalog.",
    },
]

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="""
## SoundPuff API - Social Music Platform

A social music platform API built with FastAPI, PostgreSQL, and Supabase Auth.

### Features
- 🔐 **Authentication**: Secure user signup/login with Supabase Auth
- 👤 **User Profiles**: Create and manage user profiles with bio and avatar
- 🎵 **Playlists**: Create, edit, and share music playlists
- 👥 **Social**: Follow/unfollow users, like and comment on playlists
- 📱 **Feed**: Personalized feed showing playlists from followed users

### Authentication
All protected endpoints require a Bearer token. Get your token by:
1. Sign up: `POST /api/v1/auth/signup`
2. Login: `POST /api/v1/auth/login`
3. Use the returned `access_token` by clicking the "Authorize" button above
    """,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    openapi_tags=tags_metadata,
    swagger_ui_parameters={
        "persistAuthorization": True,
        "displayRequestDuration": True,
        "filter": True,
        "tryItOutEnabled": True,
    }
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
def read_root():
    return {
        "message": "Welcome to SoundPuff API",
        "version": settings.VERSION,
        "docs": f"{settings.API_V1_STR}/docs"
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}
