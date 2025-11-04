"""JWT Authentication module for Interview Copilot API."""

from datetime import datetime, timedelta
from typing import Optional, Dict
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from config import config

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer token security
security = HTTPBearer()


class TokenData(BaseModel):
    """JWT Token data model."""
    user_id: str
    email: str
    exp: Optional[datetime] = None


class UserCredentials(BaseModel):
    """User credentials for login."""
    email: str
    password: str


class UserCreate(BaseModel):
    """User creation model."""
    email: str
    password: str
    full_name: Optional[str] = None


class User(BaseModel):
    """User model."""
    id: str
    email: str
    full_name: Optional[str] = None
    is_active: bool = True
    created_at: datetime


class TokenResponse(BaseModel):
    """JWT Token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


# In-memory user storage (replace with database in production)
users_db: Dict[str, Dict] = {}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=config.jwt_access_token_expire_minutes)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, config.jwt_secret_key, algorithm=config.jwt_algorithm)

    return encoded_jwt


def decode_token(token: str) -> TokenData:
    """Decode and validate JWT token."""
    try:
        payload = jwt.decode(token, config.jwt_secret_key, algorithms=[config.jwt_algorithm])
        user_id: str = payload.get("sub")
        email: str = payload.get("email")

        if user_id is None or email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return TokenData(user_id=user_id, email=email)

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenData:
    """Get current authenticated user from JWT token."""
    token = credentials.credentials
    return decode_token(token)


async def get_optional_user(authorization: Optional[str] = Header(None)) -> Optional[TokenData]:
    """Get user if token provided, otherwise None (for optional auth)."""
    if not authorization:
        return None

    if not authorization.startswith("Bearer "):
        return None

    token = authorization.replace("Bearer ", "")

    try:
        return decode_token(token)
    except HTTPException:
        return None


def create_user(email: str, password: str, full_name: Optional[str] = None) -> User:
    """Create new user."""
    if email in users_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    user_id = f"user_{len(users_db) + 1}"
    hashed_password = get_password_hash(password)

    user_data = {
        "id": user_id,
        "email": email,
        "hashed_password": hashed_password,
        "full_name": full_name,
        "is_active": True,
        "created_at": datetime.utcnow()
    }

    users_db[email] = user_data

    return User(
        id=user_id,
        email=email,
        full_name=full_name,
        is_active=True,
        created_at=user_data["created_at"]
    )


def authenticate_user(email: str, password: str) -> Optional[User]:
    """Authenticate user with email and password."""
    user_data = users_db.get(email)

    if not user_data:
        return None

    if not verify_password(password, user_data["hashed_password"]):
        return None

    return User(
        id=user_data["id"],
        email=user_data["email"],
        full_name=user_data.get("full_name"),
        is_active=user_data["is_active"],
        created_at=user_data["created_at"]
    )


def get_user_by_id(user_id: str) -> Optional[User]:
    """Get user by ID."""
    for user_data in users_db.values():
        if user_data["id"] == user_id:
            return User(
                id=user_data["id"],
                email=user_data["email"],
                full_name=user_data.get("full_name"),
                is_active=user_data["is_active"],
                created_at=user_data["created_at"]
            )
    return None


def require_auth_dependency():
    """Dependency that requires authentication if REQUIRE_AUTH is True."""
    if config.require_auth:
        return Depends(get_current_user)
    return Depends(get_optional_user)
