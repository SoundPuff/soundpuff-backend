import pytest

from app.core.config import Settings


def make_settings(**overrides) -> Settings:
    base_settings = {
        "SECRET_KEY": "test-secret-key",
        "POSTGRES_USER": "postgres",
        "POSTGRES_PASSWORD": "postgres",
        "POSTGRES_SERVER": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_DB": "soundpuff",
    }
    base_settings.update(overrides)
    return Settings(**base_settings)


def test_cors_origins_are_split_into_list():
    settings = make_settings(
        BACKEND_CORS_ORIGINS="http://localhost:3000,http://soundpuff.ozten.app",
    )

    assert [str(origin) for origin in settings.BACKEND_CORS_ORIGINS] == [
        "http://localhost:3000/",
        "http://soundpuff.ozten.app/",
    ]


def test_db_url_defaults_to_local_postgres_connection():
    settings = make_settings()

    assert (
        settings.db_url
        == "postgresql+psycopg2://postgres:postgres@localhost:5432/soundpuff"
    )


def test_supabase_database_url_is_used_when_provided():
    custom_database_url = "postgresql+psycopg2://user:password@host:5432/customdb"
    settings = make_settings(
        SUPABASE_URL="https://example.supabase.co",
        DATABASE_URL=custom_database_url,
    )

    assert settings.db_url == custom_database_url


def test_invalid_database_url_raises_value_error():
    with pytest.raises(ValueError):
        make_settings(DATABASE_URL="not-a-valid-database-url")
