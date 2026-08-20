import secrets
import os

from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.github import AppUser

SESSION_COOKIE = "copilot_session"


def get_current_user(request: Request, response: Response, db: Session = Depends(get_db)) -> AppUser:
    token = request.cookies.get(SESSION_COOKIE)
    user = db.query(AppUser).filter(AppUser.session_token == token).first() if token else None
    if user:
        return user
    user = AppUser(session_token=secrets.token_urlsafe(48))
    db.add(user)
    db.commit()
    db.refresh(user)
    response.set_cookie(SESSION_COOKIE, user.session_token, httponly=True, samesite="lax", secure=os.getenv("APP_ENV", "development") == "production", max_age=60 * 60 * 24 * 30)
    return user


def require_project_owner(project_id: int, user: AppUser, db: Session):
    from app.models.project import Project
    project = db.query(Project).filter(Project.id == project_id, Project.owner_user_id == user.id).first()
    if not project:
        raise HTTPException(404, "Project not found for the current user.")
    return project
