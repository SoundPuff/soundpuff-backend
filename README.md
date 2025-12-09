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
- **PostgreSQL** - Database (local development)
- **Supabase** - Database and Auth (production)
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
- PostgreSQL 12+ (for local development)
- [Supabase](https://supabase.com) account (for production database)
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

4. **Database Setup**

   **Option A: Local PostgreSQL (Development)**

   ```bash
   createdb soundpuff
   ```

   **Option B: Supabase (Production)**

   1. Create a new project at [supabase.com](https://supabase.com)
   2. Go to Settings > API to get your project URL and anon key
   3. Go to Settings > Database > **Connection Pooling**
   4. Copy the **Session pooler** connection string (port 6543)
   5. Your DATABASE_URL format: `postgresql+psycopg2://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres`

   **Note**: Use the Session Pooler (port 6543) instead of direct connection (port 5432) if you don't have IPv6.

5. Copy `.env.example` to `.env` and update the values:

```bash
cp .env.example .env
```

For Supabase, update these variables in `.env`:

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
# Use Session Pooler (IPv4 compatible - port 6543)
DATABASE_URL=postgresql+psycopg2://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
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

### 📚 Interactive API Documentation

**Swagger UI (Recommended)**: http://localhost:8000/api/v1/docs

- Interactive API testing interface
- Try out endpoints directly from your browser
- Built-in authentication support
- See `SWAGGER_UI_GUIDE.md` for detailed usage instructions

**ReDoc**: http://localhost:8000/api/v1/redoc

- Clean, readable API documentation
- Better for reviewing the API structure

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

### Songs

- `GET /api/v1/songs/search` - Search songs by title or artist

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

MIT
