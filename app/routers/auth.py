from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..models import User
from ..security import create_token, hash_password, verify_password
from ..templating import templates

router = APIRouter()


def _login_redirect(user_id: int) -> RedirectResponse:
    resp = RedirectResponse("/", status_code=303)
    resp.set_cookie(
        "access_token", create_token(user_id),
        httponly=True, samesite="lax", secure=settings.cookie_secure,
        max_age=settings.access_token_minutes * 60,
    )
    return resp


@router.get("/signup")
def signup_page(request: Request):
    return templates.TemplateResponse(request, "signup.html")


@router.post("/signup")
def signup(request: Request, email: str = Form(...), password: str = Form(...),
           db: Session = Depends(get_db)):
    email = email.strip().lower()
    error = None
    if len(password) < 8:
        error = "Password must be at least 8 characters."
    elif db.scalar(select(User).where(User.email == email)):
        error = "That email is already registered. Log in instead."
    if error:
        return templates.TemplateResponse(request, "signup.html", {"error": error}, status_code=400)
    user = User(email=email, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    return _login_redirect(user.id)


@router.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html")


@router.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...),
          db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            request, "login.html", {"error": "Email or password is incorrect."}, status_code=401)
    return _login_redirect(user.id)


@router.post("/logout")
def logout():
    resp = RedirectResponse("/login", status_code=303)
    resp.delete_cookie("access_token")
    return resp
