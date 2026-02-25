"""
Security Configuration

JWT authentication, password hashing, and security utilities.
"""

from datetime import datetime, timedelta
from typing import Optional
import jwt
from passlib.context import CryptContext
from .settings import settings
import secrets


class SecurityConfig:
    """Security configuration and utilities."""
    
    # Password hashing
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    @classmethod
    def hash_password(cls, password: str) -> str:
        """Hash a password for storing."""
        return cls.pwd_context.hash(password)
    
    @classmethod
    def verify_password(cls, plain_password: str, hashed_password: str) -> bool:
        """Verify a stored password against a plain password."""
        return cls.pwd_context.verify(plain_password, hashed_password)
    
    @classmethod
    def create_access_token(
        cls,
        data: dict,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a JWT access token.
        
        Args:
            data: Dictionary with user data (user_id, tenant_id, role)
            expires_delta: Token expiration time (default from settings)
        
        Returns:
            Encoded JWT token
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=settings.jwt_expiration_minutes
            )
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        })
        
        encoded_jwt = jwt.encode(
            to_encode,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm
        )
        return encoded_jwt
    
    @classmethod
    def decode_access_token(cls, token: str) -> dict:
        """
        Decode and verify a JWT token.
        
        Args:
            token: JWT token string
        
        Returns:
            Decoded token data
        
        Raises:
            jwt.ExpiredSignatureError: Token has expired
            jwt.InvalidTokenError: Token is invalid
        """
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    
    @classmethod
    def create_api_key(cls) -> str:
        """Generate a secure API key."""
        return secrets.token_urlsafe(32)
    
    @classmethod
    def create_refresh_token(cls) -> str:
        """Generate a refresh token."""
        return secrets.token_urlsafe(32)


# CORS configuration
def get_cors_config() -> dict:
    """Get CORS configuration for FastAPI."""
    return {
        "allow_origins": settings.cors_origins,
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    }
