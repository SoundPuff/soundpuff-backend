from pydantic import BaseModel
from typing import Optional


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: Optional[int] = None  # Token expiry in seconds


class TokenRefresh(BaseModel):
    """Request schema for refreshing tokens"""
    refresh_token: str


class TokenData(BaseModel):
    username: Optional[str] = None
