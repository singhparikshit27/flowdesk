from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.models import Task, TaskStatus, TaskPriority, ProjectMember, User, Project
from app.auth_utils import get_current_user

router = APIRouter()

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: Optional[str] = "medium"
    assignee_id: Optional[int] = None
    due_date: Optional[datetime] = None
    project_id: int

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    assignee_id: Optional[int] = None
    due_date: Optional[datetime] = None

def require_membership(project_id: int, user_id: int, db: Session):
    m = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id
    ).first()
    if not m:
        raise HTTPException(status_code=403, detail="Not a member of this project")
    return m.role

def task_to_dict(t: Task):
    return {
        "id": t.id,
        "title": t.title,
        "description": t.description,
        "status": t.status,
        "priority": t.priority,
        "project_id": t.project_id,
        "assignee": {"id": t.assignee.id, "name": t.assignee.name} if t.assignee else None,
        "created_by": {"id": t.creator.id, "name": t.creator.name},
        "due_date": t.due_date,
        "created_at": t.created_at,
        "updated_at": t.updated_at,
        "is_overdue": t.due_date and t.due_date < datetime.utcnow() and t.status != "done"
    }

@router.post("/")
def create_task(data: TaskCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if len(data.title.strip()) < 2:
        raise HTTPException(status_code=400, detail="Task title too short")
    
    require_membership(data.project_id, current_user.id, db)
    
    if data.priority not in ["low", "medium", "high"]:
        raise HTTPException(status_code=400, detail="Invalid priority")
    
    if data.assignee_id:
        member = db.query(ProjectMember).filter(
            ProjectMember.project_id == data.project_id,
            ProjectMember.user_id == data.assignee_id
        ).first()
        if not member:
            raise HTTPException(status_code=400, detail="Assignee must be a project member")
    
    task = Task(
        title=data.title.strip(),
        description=data.description,
        priority=TaskPriority(data.priority),
        project_id=data.project_id,
        assignee_id=data.assignee_id,
        created_by=current_user.id,
        due_date=data.due_date
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task_to_dict(task)

@router.get("/project/{project_id}")
def list_tasks(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_membership(project_id, current_user.id, db)
    tasks = db.query(Task).filter(Task.project_id == project_id).all()
    return [task_to_dict(t) for t in tasks]

@router.get("/my")
def my_tasks(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    tasks = db.query(Task).filter(Task.assignee_id == current_user.id).all()
    return [task_to_dict(t) for t in tasks]

@router.patch("/{task_id}")
def update_task(task_id: int, data: TaskUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    role = require_membership(task.project_id, current_user.id, db)
    
    if data.title is not None:
        task.title = data.title.strip()
    if data.description is not None:
        task.description = data.description
    if data.status is not None:
        if data.status not in ["todo", "in_progress", "done"]:
            raise HTTPException(status_code=400, detail="Invalid status")
        task.status = TaskStatus(data.status)
    if data.priority is not None:
        if data.priority not in ["low", "medium", "high"]:
            raise HTTPException(status_code=400, detail="Invalid priority")
        task.priority = TaskPriority(data.priority)
    if data.assignee_id is not None:
        member = db.query(ProjectMember).filter(
            ProjectMember.project_id == task.project_id,
            ProjectMember.user_id == data.assignee_id
        ).first()
        if not member:
            raise HTTPException(status_code=400, detail="Assignee must be a project member")
        task.assignee_id = data.assignee_id
    if data.due_date is not None:
        task.due_date = data.due_date

    task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(task)
    return task_to_dict(task)

@router.delete("/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    role = require_membership(task.project_id, current_user.id, db)
    if role != "admin" and task.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Only admins or task creator can delete")
    
    db.delete(task)
    db.commit()
    return {"message": "Task deleted"}

@router.get("/dashboard/summary")
def dashboard_summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get a summary of all tasks across user's projects for dashboard"""
    memberships = db.query(ProjectMember).filter(ProjectMember.user_id == current_user.id).all()
    project_ids = [m.project_id for m in memberships]
    
    all_tasks = db.query(Task).filter(Task.project_id.in_(project_ids)).all() if project_ids else []
    now = datetime.utcnow()
    
    return {
        "total": len(all_tasks),
        "todo": sum(1 for t in all_tasks if t.status == "todo"),
        "in_progress": sum(1 for t in all_tasks if t.status == "in_progress"),
        "done": sum(1 for t in all_tasks if t.status == "done"),
        "overdue": sum(1 for t in all_tasks if t.due_date and t.due_date < now and t.status != "done"),
        "assigned_to_me": sum(1 for t in all_tasks if t.assignee_id == current_user.id),
        "projects_count": len(project_ids)
    }
