from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime
from jose import JWTError, jwt
from pydantic import ValidationError
from typing import Optional, Dict, Any

from ..config import settings
from ..db.database import get_database
from ..models.user import UserModel
from ..db.repositories.users import UserRepository

security = HTTPBearer(
    scheme_name="JWT Authentication",
    description="Enter JWT token",
    auto_error=False
)

async def get_current_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Dependency for endpoints that require admin authentication
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not credentials:
        raise credentials_exception
        
    token = credentials.credentials
    
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        
        # Check if user is an admin
        if payload.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized for admin access"
            )
            
        return payload
        
    except (JWTError, ValidationError):
        raise credentials_exception

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db = Depends(get_database)
) -> Dict[str, Any]:
    """
    Dependency for endpoints that require user authentication (regular user or admin)
    Returns user data with token payload
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not credentials:
        raise credentials_exception
        
    token = credentials.credentials
    
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        
        # Get role to determine if admin or regular user
        role = payload.get("role", "user")
        
        # For admins (they don't have user records in the database)
        if role == "admin":
            return {
                "id": user_id,
                "role": "admin",
                "is_admin": True
            }
        
        # For regular users, get their info from the database
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(user_id)
        
        if not user:
            raise credentials_exception
        
        # Update last active timestamp
        await user_repo.update(
            user_id, 
            {"lastActive": datetime.now()}
        )
        
        # Return user model with additional auth info
        user_dict = user.model_dump(by_alias=True)
        user_dict["role"] = role
        user_dict["is_admin"] = False
        
        return UserModel.model_validate(user_dict)
        
    except (JWTError, ValidationError, Exception) as e:
        raise credentials_exception

# Optional dependency - doesn't throw exceptions if not authenticated
async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db = Depends(get_database)
) -> Optional[Dict[str, Any]]:
    """
    Dependency for endpoints that can work with or without authentication
    Returns user data if authenticated, None otherwise
    """
    if not credentials:
        return None
        
    token = credentials.credentials
    
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if not user_id:
            return None
            
        role = payload.get("role", "user")
        
        # For admins
        if role == "admin":
            return {
                "id": user_id,
                "role": "admin",
                "is_admin": True
            }
            
        # For regular users
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(user_id)
        
        if not user:
            return None
            
        # Update last active timestamp
        await user_repo.update(
            user_id, 
            {"lastActive": datetime.now()}
        )
        
        # Return user model with additional auth info
        user_dict = user.model_dump(by_alias=True)
        user_dict["role"] = role
        user_dict["is_admin"] = False
        
        return user_dict
        
    except (JWTError, ValidationError):
        return None