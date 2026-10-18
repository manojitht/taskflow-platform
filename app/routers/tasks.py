from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_user
from ..models import Status, Task, User
from ..templating import templates

router = APIRouter()


def _own_task(db: Session, task_id: int, user: User) -> Task:
    task = db.get(Task, task_id)
    if not task or task.owner_id != user.id:  # authorization: users only touch their own rows
        raise HTTPException(404)
    return task


@router.get("/")
def board(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    tasks = db.scalars(select(Task).where(Task.owner_id == user.id).order_by(Task.created_at)).all()
    columns = {s: [t for t in tasks if t.status == s] for s in Status}
    return templates.TemplateResponse(request, "tasks.html", {"user": user, "columns": columns})


@router.post("/tasks")
def create(title: str = Form(..., max_length=200), description: str = Form(""),
           user: User = Depends(current_user), db: Session = Depends(get_db)):
    db.add(Task(title=title.strip(), description=description.strip(), owner_id=user.id))
    db.commit()
    return RedirectResponse("/", status_code=303)


@router.post("/tasks/{task_id}/status")
def move(task_id: int, status: Status = Form(...),
         user: User = Depends(current_user), db: Session = Depends(get_db)):
    _own_task(db, task_id, user).status = status
    db.commit()
    return RedirectResponse("/", status_code=303)


@router.post("/tasks/{task_id}/delete")
def delete(task_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    db.delete(_own_task(db, task_id, user))
    db.commit()
    return RedirectResponse("/", status_code=303)
