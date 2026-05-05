from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from app.database import get_db
from app.models import Project, ProjectMember, User, UserRole, Task
from app.auth_utils import get_current_user

router = APIRouter()

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None

class AddMemberRequest(BaseModel):
    email: str
    role: str = "member"

def get_member_role(project_id: int, user_id: int, db: Session) -> Optional[str]:
    m = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id
    ).first()
    return m.role if m else None

def require_project_access(project_id: int, user: User, db: Session):
    role = get_member_role(project_id, user.id, db)
    if not role:
        raise HTTPException(status_code=403, detail="Not a member of this project")
    return role

@router.post("/")
def create_project(data: ProjectCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if len(data.name.strip()) < 2:
        raise HTTPException(status_code=400, detail="Project name too short")
    
    project = Project(
        name=data.name.strip(),
        description=data.description,
        created_by=current_user.id
    )
    db.add(project)
    db.flush()

    # Creator is automatically admin
    membership = ProjectMember(
        project_id=project.id,
        user_id=current_user.id,
        role=UserRole.admin
    )
    db.add(membership)
    db.commit()
    db.refresh(project)
    return _project_detail(project, db)

@router.get("/")
def list_my_projects(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    memberships = db.query(ProjectMember).filter(ProjectMember.user_id == current_user.id).all()
    result = []
    for m in memberships:
        p = m.project
        total = db.query(Task).filter(Task.project_id == p.id).count()
        done = db.query(Task).filter(Task.project_id == p.id, Task.status == "done").count()
        result.append({
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "my_role": m.role,
            "member_count": len(p.members),
            "task_count": total,
            "done_count": done,
            "created_at": p.created_at
        })
    return result

@router.get("/{project_id}")
def get_project(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    require_project_access(project_id, current_user, db)
    return _project_detail(project, db)

@router.delete("/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    role = require_project_access(project_id, current_user, db)
    if role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete projects")
    db.delete(project)
    db.commit()
    return {"message": "Project deleted"}

@router.post("/{project_id}/members")
def add_member(project_id: int, data: AddMemberRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    role = require_project_access(project_id, current_user, db)
    if role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can add members")
    
    target_user = db.query(User).filter(User.email == data.email.lower()).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found with that email")
    
    existing = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == target_user.id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="User is already a member")
    
    if data.role not in ["admin", "member"]:
        raise HTTPException(status_code=400, detail="Role must be admin or member")
    
    membership = ProjectMember(
        project_id=project_id,
        user_id=target_user.id,
        role=UserRole(data.role)
    )
    db.add(membership)
    db.commit()
    return {"message": f"{target_user.name} added as {data.role}"}

@router.delete("/{project_id}/members/{user_id}")
def remove_member(project_id: int, user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    role = require_project_access(project_id, current_user, db)
    if role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can remove members")
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot remove yourself")
    
    m = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id
    ).first()
    if not m:
        raise HTTPException(status_code=404, detail="Member not found")
    db.delete(m)
    db.commit()
    return {"message": "Member removed"}

def _project_detail(project: Project, db: Session):
    members = []
    for m in project.members:
        members.append({
            "id": m.user.id,
            "name": m.user.name,
            "email": m.user.email,
            "role": m.role
        })
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "created_at": project.created_at,
        "members": members
    }
