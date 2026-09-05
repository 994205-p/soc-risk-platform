"""
Simple demo authentication: username/password -> JWT carrying the user's
role. This is a PROTOTYPE auth flow (per project scope: "basic secure
practices" for a demo, not production-grade IdP integration).
"""
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.models import User, Role

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def ensure_demo_users(db: Session):
    """Idempotently create the three demo accounts (management/soc/engineer),
    password 'demo1234' for all -- documented clearly in README, not a real
    production credential scheme."""
    role_map = {r.role_name: r.role_id for r in db.query(Role).all()}
    if not role_map:
        return
    demo_users = [
        ("manager", "Alex Chen (Management)", "management"),
        ("analyst", "Priya Nair (SOC Analyst)", "soc_analyst"),
        ("engineer", "Sam Rivera (Security Engineer)", "security_engineer"),
    ]
    for username, display_name, role_name in demo_users:
        if not db.query(User).filter(User.username == username).first():
            db.add(User(username=username, display_name=display_name,
                        role_id=role_map[role_name], password_hash=hash_password("demo1234")))
    db.commit()


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                           detail="Could not validate credentials")
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user


def require_role(*allowed_roles: str):
    def checker(user: User = Depends(get_current_user)):
        if user.role.role_name not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient role permissions for this resource.")
        return user
    return checker
