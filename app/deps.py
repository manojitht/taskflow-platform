from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .db import get_db
from .models import User
from .security import decode_token


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Reads the JWT from an HttpOnly cookie; redirects to /login if missing/invalid."""
    user_id = decode_token(request.cookies.get("access_token", ""))
    user = db.get(User, user_id) if user_id else None
    if not user:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return user
