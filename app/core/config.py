from pydantic import AnyHttpUrl, validator
from pydantic_settings import BaseSettings
from typing import List, Optional
from sqlalchemy.engine.url import make_url, URL
from supabase import create_client, Client


class Settings(BaseSettings):
    # App Settings
    PROJECT_NAME: str = "SoundPuff API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # PostgreSQL Database Settings
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: str = "5432"
    POSTGRES_DB: str = "soundpuff"
    DATABASE_URL: Optional[str] = None 

    # Supabase Settings
    SUPABASE_URL: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None

    @property
    def db_url(self) -> str:
        if self.SUPABASE_URL:
            # Supabase provides a direct DATABASE_URL, but we can construct it
            # For now, assume SUPABASE_DATABASE_URL is set, or use DATABASE_URL
            return self.DATABASE_URL or f"postgresql+psycopg2://postgres:[password]@db.[project-ref].supabase.co:5432/postgres"
        return self.DATABASE_URL or (f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}")
    
    @property
    def supabase_client(self) -> Optional[Client]:
        if self.SUPABASE_URL and self.SUPABASE_ANON_KEY:
            return create_client(self.SUPABASE_URL, self.SUPABASE_ANON_KEY)
        return None
    
    # Security Settings
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # CORS Settings
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []


    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v):
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    
    @validator("DATABASE_URL")
    def validate_db_url(cls, v):
        if v is None or v.strip() == "":
            return v
        try:
            make_url(v)
            return v
        except Exception as e:
            raise ValueError(f"Invalid DATABASE_URL. Example format: "
                 f"postgresql+psycopg2://user:password@host:port/db_name. Error: {e}")



    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
