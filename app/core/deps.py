from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from supabase import Client
from uuid import UUID

from app.core.config import settings
from app.core.supabase import get_supabase_client as create_supabase_client
from app.db.session import get_db
from app.models import User

# Use HTTPBearer instead of OAuth2PasswordBearer since we're using Supabase Auth
security = HTTPBearer()


def get_supabase_client() -> Client:
    """Dependency to get Supabase client"""
    return create_supabase_client()


def get_current_user(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    supabase: Client = Depends(get_supabase_client)
) -> User:
    """
    Verify Supabase JWT token and return the current user.
    The token is issued by Supabase Auth when users sign up or log in.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials

    try:
        # Verify the token with Supabase
        user_response = supabase.auth.get_user(token)

        if not user_response or not user_response.user:
            raise credentials_exception

        supabase_user = user_response.user
        user_id = UUID(supabase_user.id)

        # Get user from our database
        user = db.query(User).filter(User.id == user_id).first()

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found. Please create a profile first."
            )

        return user

    except ValueError as e:
        # Invalid UUID
        raise credentials_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
