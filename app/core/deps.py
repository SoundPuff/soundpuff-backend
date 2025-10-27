from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Verify token with Supabase
        if not settings.supabase_client:
            raise credentials_exception
        
        # Get user from Supabase token
        user_response = settings.supabase_client.auth.get_user(token)
        
        if not user_response.user:
            raise credentials_exception
        
        # Get user from database
        user = db.query(User).filter(User.id == user_response.user.id).first()
        if not user:
            raise credentials_exception
            
        return user
        
    except Exception as e:
        raise credentials_exception
