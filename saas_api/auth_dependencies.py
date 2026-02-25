"""
Authentication Dependencies

FastAPI dependencies for JWT authentication and tenant isolation.
"""

from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional

from saas_config import get_db, SecurityConfig, tenant_context
from saas_models import User, Tenant


# Security scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get current authenticated user from JWT token.
    
    Usage:
        @app.get("/protected")
        def protected_route(user: User = Depends(get_current_user)):
            return {"user_id": str(user.id)}
    """
    token = credentials.credentials
    
    try:
        # Decode JWT token
        payload = SecurityConfig.decode_access_token(token)
        user_id = payload.get("user_id")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        
        # Get user from database
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
        
        # Set tenant context for database queries
        tenant_context.set_tenant_id(str(user.tenant_id))
        
        return user
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}"
        )


async def get_current_active_tenant(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Tenant:
    """
    Dependency to get current user's tenant.
    
    Verifies tenant is active before allowing access.
    """
    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    if not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant account is inactive"
        )
    
    return tenant


async def require_role(required_roles: list[str]):
    """
    Dependency factory for role-based access control.
    
    Usage:
        @app.post("/admin-only")
        def admin_route(user: User = Depends(require_role(["admin"]))):
            return {"message": "Admin access granted"}
    """
    async def role_checker(user: User = Depends(get_current_user)) -> User:
        if user.role.value not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {required_roles}"
            )
        return user
    
    return role_checker


async def get_api_key_user(
    api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Alternative authentication using API key.
    
    Usage:
        @app.get("/api-endpoint")
        def api_route(user: User = Depends(get_api_key_user)):
            return {"user_id": str(user.id)}
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )
    
    user = db.query(User).filter(User.api_key == api_key).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Set tenant context
    tenant_context.set_tenant_id(str(user.tenant_id))
    
    return user


async def get_user_from_token_or_api_key(
    user_jwt: Optional[User] = Depends(get_current_user),
    user_api: Optional[User] = Depends(get_api_key_user)
) -> User:
    """
    Flexible authentication supporting both JWT and API key.
    
    Tries JWT first, falls back to API key.
    """
    return user_jwt or user_api
