# SoundPuff Backend

A social music platform API built with FastAPI and PostgreSQL.

## Features

- User authentication (signup/login with JWT)
- User profiles with bio and avatar
- Playlist creation, viewing, and editing
- Follow/unfollow users
- Feed showing playlists from followed users
- Like and comment on playlists
- Search functionality

## Tech Stack

- **FastAPI** - Modern Python web framework
- **PostgreSQL** - Database
- **SQLAlchemy** - ORM
- **Alembic** - Database migrations
- **Pydantic** - Data validation
- **JWT** - Authentication

## Project Structure

```
soundpuff-backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   ├── auth.py
│   │       │   ├── users.py
│   │       │   └── playlists.py
│   │       └── api.py
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   └── deps.py
│   ├── db/
│   │   ├── base.py
│   │   ├── base_class.py
│   │   └── session.py
│   ├── models/
│   │   ├── user.py
│   │   ├── playlist.py
│   │   ├── song.py
│   │   ├── comment.py
│   │   ├── like.py
│   │   └── follow.py
│   ├── schemas/
│   │   ├── user.py
│   │   ├── token.py
│   │   ├── playlist.py
│   │   ├── song.py
│   │   ├── comment.py
│   │   ├── like.py
│   │   └── follow.py
│   └── main.py
├── alembic/
├── requirements.txt
├── .env.example
└── README.md
```

## Setup

### Prerequisites

- Python 3.8-3.12
- PostgreSQL 12+
- [uv](https://docs.astral.sh/uv/) - Fast Python package installer

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd soundpuff-backend
```

2. Install uv (if not already installed):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

3. Install dependencies and create virtual environment:
```bash
uv sync
```

4. Create a PostgreSQL database:
```bash
createdb soundpuff
```

5. Copy `.env.example` to `.env` and update the values:
```bash
cp .env.example .env
```

6. Initialize Alembic and create the database tables:
```bash
uv run alembic init alembic
uv run alembic revision --autogenerate -m "Initial migration"
uv run alembic upgrade head
```

### Running the Application

Start the development server:
```bash
uv run uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

API documentation (Swagger UI): `http://localhost:8000/api/v1/docs`

## API Endpoints

### Authentication
- `POST /api/v1/auth/signup` - Register a new user
- `POST /api/v1/auth/login` - Login user

### Users
- `GET /api/v1/users/me` - Get current user
- `PUT /api/v1/users/me` - Update current user
- `GET /api/v1/users/{username}` - Get user by username
- `POST /api/v1/users/{username}/follow` - Follow user
- `DELETE /api/v1/users/{username}/follow` - Unfollow user
- `GET /api/v1/users/{username}/followers` - Get user followers
- `GET /api/v1/users/{username}/following` - Get users being followed

### Playlists
- `GET /api/v1/playlists/` - Get all playlists
- `GET /api/v1/playlists/feed` - Get feed (playlists from followed users)
- `POST /api/v1/playlists/` - Create playlist
- `GET /api/v1/playlists/{playlist_id}` - Get playlist by ID
- `PUT /api/v1/playlists/{playlist_id}` - Update playlist
- `DELETE /api/v1/playlists/{playlist_id}` - Delete playlist
- `POST /api/v1/playlists/{playlist_id}/like` - Like playlist
- `DELETE /api/v1/playlists/{playlist_id}/like` - Unlike playlist
- `GET /api/v1/playlists/{playlist_id}/comments` - Get playlist comments
- `POST /api/v1/playlists/{playlist_id}/comments` - Create comment
- `PUT /api/v1/playlists/comments/{comment_id}` - Update comment
- `DELETE /api/v1/playlists/comments/{comment_id}` - Delete comment

## Database Schema

- **users** - User accounts
- **playlists** - Music playlists
- **songs** - Song metadata
- **playlist_songs** - Many-to-many relationship between playlists and songs
- **comments** - Comments on playlists
- **likes** - Likes on playlists
- **follows** - User follow relationships

## Development

### Database Migrations

Create a new migration:
```bash
uv run alembic revision --autogenerate -m "Description"
```

Apply migrations:
```bash
uv run alembic upgrade head
```

Rollback migration:
```bash
uv run alembic downgrade -1
```

### Adding Dependencies

Add a new dependency:
```bash
uv add <package-name>
```

Add a development dependency:
```bash
uv add --dev <package-name>
```

### Managing the Environment

Sync dependencies (install/update based on lock file):
```bash
uv sync
```

Update dependencies:
```bash
uv lock --upgrade
```

## License

MIT2
