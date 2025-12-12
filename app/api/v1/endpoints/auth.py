from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from supabase import Client
from pydantic import BaseModel, EmailStr
from uuid import UUID

from app.core.deps import get_supabase_client
from app.db.session import get_db
from app.models import User  # Import from models package to ensure all models are loaded
from app.schemas.token import Token, TokenRefresh
from app.schemas.user import UserCreate, User as UserSchema

router = APIRouter()
security = HTTPBearer()


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


class PasswordResetRequest(BaseModel):
    """Request schema for password reset"""
    email: EmailStr

    class Config:
        json_schema_extra = {
            "example": {
                "email": "john.doe@example.com"
            }
        }


class PasswordResetConfirm(BaseModel):
    """Request schema for confirming password reset"""
    token: str
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "token": "6f32a2ab2a044efc7eb84c73d1974672e5db5d42e0336b37476c1b80",
                "password": "NewSecurePassword123!"
            }
        }


@router.post(
    "/signup",
    response_model=Token,
    status_code=status.HTTP_201_CREATED,
    summary="Sign up a new user",
    description="""
    Create a new user account with Supabase Auth.

    This endpoint will:
    1. Create a user in Supabase Auth (handles email/password securely)
    2. Create a user profile in the database
    3. Return access and refresh tokens for immediate use

    **Note**: The username must be unique. Email validation is handled by Supabase.
    
    **Token Usage**:
    - `access_token`: Use for authenticated requests (expires in ~1 hour)
    - `refresh_token`: Use to get new tokens when access token expires
    """,
    responses={
        201: {
            "description": "User created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "refresh_token": "v1.MjQ0ZjJkNGItZjRjMy00...",
                        "token_type": "bearer",
                        "expires_in": 3600
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

        if not auth_response.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create user account"
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

        # Return the access token
        if not auth_response.session or not auth_response.session.access_token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate access token"
            )

        return {
            "access_token": auth_response.session.access_token,
            "refresh_token": auth_response.session.refresh_token,
            "token_type": "bearer",
            "expires_in": auth_response.session.expires_in
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
    Authenticate with Supabase Auth and get access and refresh tokens.

    Use the returned tokens as follows:
    - `access_token`: Include in request headers as `Authorization: Bearer <token>`
    - `refresh_token`: Use with `/auth/refresh` endpoint when access token expires
    
    **Token Lifecycle**:
    - Access tokens expire in ~1 hour
    - Refresh tokens are long-lived but rotated on each use
    - When access token expires, use refresh token to get new tokens
    """,
    responses={
        200: {
            "description": "Login successful",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "refresh_token": "v1.MjQ0ZjJkNGItZjRjMy00...",
                        "token_type": "bearer",
                        "expires_in": 3600
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
            "refresh_token": auth_response.session.refresh_token,
            "token_type": "bearer",
            "expires_in": auth_response.session.expires_in
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Login failed: {str(e)}"
        )


@router.post(
    "/refresh",
    response_model=Token,
    summary="Refresh access token",
    description="""
    Get new access and refresh tokens using a valid refresh token.

    **Token Rotation**: Each time you refresh:
    - A new access token is issued
    - A new refresh token is issued (old one becomes invalid)
    - Store the new refresh token for future use

    **When to use**:
    - When access token expires (401 Unauthorized response)
    - Proactively before expiry using `expires_in` from login response
    """,
    responses={
        200: {
            "description": "Tokens refreshed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "refresh_token": "v1.MjQ0ZjJkNGItZjRjMy00...",
                        "token_type": "bearer",
                        "expires_in": 3600
                    }
                }
            }
        },
        401: {"description": "Invalid or expired refresh token"}
    }
)
def refresh_token(
    token_data: TokenRefresh,
    supabase: Client = Depends(get_supabase_client)
):
    """
    Refresh the access token using a refresh token.

    Supabase handles token rotation automatically - each refresh
    invalidates the old refresh token and issues a new one.
    """
    try:
        # Refresh the session with Supabase
        auth_response = supabase.auth.refresh_session(token_data.refresh_token)

        if not auth_response.session or not auth_response.session.access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )

        return {
            "access_token": auth_response.session.access_token,
            "refresh_token": auth_response.session.refresh_token,
            "token_type": "bearer",
            "expires_in": auth_response.session.expires_in
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token refresh failed: {str(e)}"
        )


@router.post(
    "/password-reset/request",
    status_code=status.HTTP_200_OK,
    summary="Request password reset",
    description="""
    Request a password reset email from Supabase Auth.

    This endpoint will:
    1. Send a password reset email to the provided email address
    2. The email will contain a link to reset the password
    3. The link will redirect to your app's password reset page with a token

    **Note**: For security reasons, this endpoint always returns success even if the email doesn't exist.
    """,
    responses={
        200: {
            "description": "Password reset email sent (or email doesn't exist)",
            "content": {
                "application/json": {
                    "example": {
                        "message": "If the email exists, a password reset link has been sent"
                    }
                }
            }
        }
    }
)
def request_password_reset(
    reset_data: PasswordResetRequest,
    supabase: Client = Depends(get_supabase_client)
):
    """
    Request a password reset email.

    Supabase will send an email with a reset link to the user.
    The link contains a token that can be used to reset the password.
    """
    try:
        # Request password reset from Supabase
        supabase.auth.reset_password_email(reset_data.email)

        # Always return success for security (don't reveal if email exists)
        return {
            "message": "If the email exists, a password reset link has been sent"
        }

    except Exception as e:
        # Still return success to not reveal if email exists
        return {
            "message": "If the email exists, a password reset link has been sent"
        }


@router.post(
    "/password-reset/confirm",
    status_code=status.HTTP_200_OK,
    summary="Confirm password reset",
    description="""
    Reset the password using the token from the reset email.

    This endpoint should be called after the user receives the reset email.
    Extract the token from the URL query parameter and submit it with the new password.

    The reset link format is:
    `https://your-supabase-url/auth/v1/verify?token=<token>&type=recovery&redirect_to=<your-app>`

    **Steps**:
    1. User clicks the reset link in email
    2. Extract the `token` parameter from the URL
    3. Call this endpoint with the token and new password
    4. Use the returned access token for authenticated requests
    """,
    responses={
        200: {
            "description": "Password reset successful",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Password has been reset successfully",
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer"
                    }
                }
            }
        },
        400: {"description": "Invalid or expired reset token"}
    }
)
def confirm_password_reset(
    reset_data: PasswordResetConfirm,
    supabase: Client = Depends(get_supabase_client)
):
    """
    Confirm password reset with token and new password.

    Verifies the recovery token and updates the password.
    """
    try:
        # Verify the token and get a session
        auth_response = supabase.auth.verify_otp({
            "token_hash": reset_data.token,
            "type": "recovery"
        })

        if not auth_response.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )

        # Create a new client with the session token to update password
        supabase.auth.set_session(
            access_token=auth_response.session.access_token,
            refresh_token=auth_response.session.refresh_token
        )

        # Update the password
        update_response = supabase.auth.update_user({
            "password": reset_data.password
        })

        if not update_response.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update password"
            )

        return {
            "message": "Password has been reset successfully",
            "access_token": auth_response.session.access_token,
            "token_type": "bearer"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password reset failed: {str(e)}"
        )


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Logout and invalidate tokens",
    description="""
    Logout the current user and invalidate all their tokens.

    This endpoint will:
    1. Revoke the current session
    2. Invalidate the access token
    3. Invalidate all refresh tokens for this session

    **After logout**:
    - The access token will no longer work
    - The refresh token will no longer work
    - User must login again to get new tokens
    """,
    responses={
        200: {
            "description": "Logout successful",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Successfully logged out"
                    }
                }
            }
        },
        401: {"description": "Invalid or missing token"}
    }
)
def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    supabase: Client = Depends(get_supabase_client)
):
    """
    Logout and invalidate the current session.

    Revokes the session in Supabase, making all tokens for this session invalid.
    """
    try:
        token = credentials.credentials
        
        # First, get the user to verify the token and set the session
        user_response = supabase.auth.get_user(token)
        
        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Sign out from Supabase with scope 'global' to revoke all sessions
        # or 'local' to revoke only the current session
        supabase.auth.sign_out({"scope": "global"})

        return {
            "message": "Successfully logged out"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Logout failed: {str(e)}"
        )
