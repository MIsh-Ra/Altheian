from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import User
from app.core.config import settings

security = HTTPBearer()
security_optional = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            options={"leeway": 300}
        )
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    from sqlalchemy import or_
    user = db.query(User).filter(
        or_(User.username == username, User.email == username)
    ).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def get_current_user_flexible(
    token: str | None = None,
    credentials: HTTPAuthorizationCredentials | None = Depends(security_optional),
    db: Session = Depends(get_db),
) -> User:
    raw_token = credentials.credentials if credentials else token
    if not raw_token:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        payload = jwt.decode(
            raw_token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            options={"leeway": 300}
        )
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    from sqlalchemy import or_
    user = db.query(User).filter(
        or_(User.username == username, User.email == username)
    ).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
