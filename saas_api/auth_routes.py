"""
Authentication API Routes

Endpoints for user registration, login, and token management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional

from saas_config import get_db, SecurityConfig
from saas_models import User, Tenant, UserRole, SubscriptionTier, AuditLog


router = APIRouter(prefix="/auth", tags=["authentication"])


# Request/Response Models
class UserRegisterRequest(BaseModel):
    """User registration request."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str
    last_name: str
    organization_name: str


class UserLoginRequest(BaseModel):
    """User login request."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    user_id: str
    tenant_id: str
    role: str


class UserResponse(BaseModel):
    """User profile response."""
    id: str
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    role: str
    tenant_id: str
    created_at: datetime
    
    class Config:
        from_attributes = True


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: UserRegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new user and create a tenant (organization).
    
    Creates both tenant and first admin user in a single operation.
    """
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create tenant
    tenant = Tenant(
        name=request.organization_name.lower().replace(" ", "_"),
        display_name=request.organization_name,
        email=request.email,
        subscription_tier=SubscriptionTier.FREE,
        is_active=True
    )
    db.add(tenant)
    db.flush()  # Get tenant ID
    
    # Create admin user
    user = User(
        tenant_id=tenant.id,
        email=request.email,
        password_hash=SecurityConfig.hash_password(request.password),
        first_name=request.first_name,
        last_name=request.last_name,
        role=UserRole.ADMIN,
        is_active=True
    )
    db.add(user)
    
    # Audit log
    audit = AuditLog(
        tenant_id=tenant.id,
        user_id=user.id,
        action="user.registered",
        resource_type="user",
        resource_id=user.id,
        details={"email": user.email, "role": user.role.value}
    )
    db.add(audit)
    
    db.commit()
    db.refresh(user)
    
    # Create access token
    token_data = {
        "user_id": str(user.id),
        "tenant_id": str(user.tenant_id),
        "role": user.role.value
    }
    access_token = SecurityConfig.create_access_token(token_data)
    
    return TokenResponse(
        access_token=access_token,
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        role=user.role.value
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: UserLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return JWT token.
    """
    # Find user
    user = db.query(User).filter(User.email == request.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Verify password
    if not SecurityConfig.verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Check if tenant is active
    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
    if not tenant or not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization account is inactive"
        )
    
    # Update last login
    user.last_login_at = datetime.utcnow()
    
    # Audit log
    audit = AuditLog(
        tenant_id=user.tenant_id,
        user_id=user.id,
        action="user.login",
        resource_type="user",
        resource_id=user.id
    )
    db.add(audit)
    db.commit()
    
    # Create access token
    token_data = {
        "user_id": str(user.id),
        "tenant_id": str(user.tenant_id),
        "role": user.role.value
    }
    access_token = SecurityConfig.create_access_token(token_data)
    
    return TokenResponse(
        access_token=access_token,
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        role=user.role.value
    )


@router.post("/api-key", response_model=dict)
async def generate_api_key(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate a new API key for the current user.
    
    Replaces any existing API key.
    """
    # Generate new API key
    api_key = SecurityConfig.create_api_key()
    
    user.api_key = api_key
    user.api_key_created_at = datetime.utcnow()
    
    # Audit log
    audit = AuditLog(
        tenant_id=user.tenant_id,
        user_id=user.id,
        action="api_key.generated",
        resource_type="user",
        resource_id=user.id
    )
    db.add(audit)
    db.commit()
    
    return {
        "api_key": api_key,
        "created_at": user.api_key_created_at,
        "message": "Store this API key securely. It will not be shown again."
    }


# Import get_current_user for API key generation
from .auth_dependencies import get_current_user
