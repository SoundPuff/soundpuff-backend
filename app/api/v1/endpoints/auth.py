from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from supabase import Client
from pydantic import BaseModel, EmailStr
from uuid import UUID

from app.core.deps import get_supabase_client
from app.db.session import get_db
from app.models import User  # Import from models package to ensure all models are loaded
from app.schemas.token import Token
from app.schemas.user import UserCreate, User as UserSchema

router = APIRouter()


class SignupRequest(BaseModel):
    """Request schema for Supabase Auth signup"""
    email: EmailStr
    password: str
    username: str

    class Config:
        json_schema_extra = {
            "example": {
                "email": "john.doe@example.com",
                "password": "SecurePassword123!",
                "username": "johndoe"
            }
        }


class LoginRequest(BaseModel):
    """Request schema for Supabase Auth login"""
    email: EmailStr
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "email": "john.doe@example.com",
                "password": "SecurePassword123!"
            }
        }


@router.post(
    "/signup",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Sign up a new user",
    description="""
    Create a new user account with Supabase Auth.

    This endpoint will:
    1. Create a user in Supabase Auth (handles email/password securely)
    2. Create a user profile in the database
    3. Return an access token for immediate use when Supabase issues a session

    If Supabase does not return a session (common when email confirmation is required),
    the endpoint returns a 201 with an explanatory message instructing the user to confirm their email.
    """,
    responses={
        201: {
            "description": "User created successfully (may require email confirmation)",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer"
                    }
                }
            }
        },
        400: {"description": "Username already taken or invalid email/password"}
    }
)
def signup(
    signup_data: SignupRequest,
    db: Session = Depends(get_db),
    supabase: Client = Depends(get_supabase_client)
):
    """
    Sign up with Supabase Auth and create a user profile.

    Steps:
    1. Create user in Supabase Auth (handles email/password)
    2. Create user profile in our database
    3. Return access token
    """
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == signup_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )

    try:
        # Sign up with Supabase Auth
        auth_response = supabase.auth.sign_up({
            "email": signup_data.email,
            "password": signup_data.password
        })

        # If Supabase returned an explicit error, surface it
        if getattr(auth_response, "error", None):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Signup error: {auth_response.error}"
            )

        if not auth_response.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create user account"
            )

        # Determine whether Supabase created a session and provided an access token
        has_token = bool(
            getattr(auth_response, "session", None)
            and getattr(auth_response.session, "access_token", None)
        )

        # Create user profile in our database
        user_id = UUID(auth_response.user.id)
        db_user = User(
            id=user_id,
            username=signup_data.username
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        # If Supabase returned a session/token, return it for immediate use
        if has_token:
            return {
                "access_token": auth_response.session.access_token,
                "token_type": "bearer"
            }

        # No session/token -> likely email confirmation required (common behavior)
        return {
            "detail": "User created. Please confirm your email before logging in."
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Signup failed: {str(e)}"
        )


@router.post(
    "/login",
    response_model=Token,
    summary="Login with email and password",
    description="""
    Authenticate with Supabase Auth and get an access token.

    Use the returned token to access protected endpoints by:
    1. Click the "Authorize" button at the top of this page
    2. Enter the token in the format: `Bearer <your-token>`
    3. Or include it in your request headers: `Authorization: Bearer <your-token>`
    """,
    responses={
        200: {
            "description": "Login successful",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer"
                    }
                }
            }
        },
        401: {"description": "Invalid email or password"}
    }
)
def login(
    login_data: LoginRequest,
    supabase: Client = Depends(get_supabase_client)
):
    """
    Login with Supabase Auth.

    Returns an access token that can be used for authenticated requests.
    """
    try:
        # Login with Supabase Auth
        auth_response = supabase.auth.sign_in_with_password({
            "email": login_data.email,
            "password": login_data.password
        })

        if not auth_response.session or not auth_response.session.access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )

        return {
            "access_token": auth_response.session.access_token,
            "token_type": "bearer"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Login failed: {str(e)}"
        )
