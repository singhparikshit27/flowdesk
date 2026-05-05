from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
import httpx
import os

from app.database import get_db
from app.models import Task, ProjectMember, Project, User
from app.auth_utils import get_current_user

router = APIRouter()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

class AIRequest(BaseModel):
    project_id: int
    question: str

@router.post("/ask")
async def ask_ai(data: AIRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Verify membership
    member = db.query(ProjectMember).filter(
        ProjectMember.project_id == data.project_id,
        ProjectMember.user_id == current_user.id
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a member of this project")

    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="AI assistant not configured")

    # Gather project context
    project = db.query(Project).filter(Project.id == data.project_id).first()
    tasks = db.query(Task).filter(Task.project_id == data.project_id).all()
    members = db.query(ProjectMember).filter(ProjectMember.project_id == data.project_id).all()
    now = datetime.utcnow()

    task_lines = []
    for t in tasks:
        overdue = t.due_date and t.due_date < now and t.status != "done"
        assignee_name = t.assignee.name if t.assignee else "Unassigned"
        due_str = t.due_date.strftime("%Y-%m-%d") if t.due_date else "No due date"
        task_lines.append(
            f"- [{t.status.upper()}] {t.title} | Priority: {t.priority} | Assigned: {assignee_name} | Due: {due_str}{'  ⚠ OVERDUE' if overdue else ''}"
        )

    member_lines = [f"- {m.user.name} ({m.role})" for m in members]
    tasks_text = "\n".join(task_lines) if task_lines else "No tasks yet."
    members_text = "\n".join(member_lines)

    system_prompt = f"""You are FlowDesk AI, an intelligent project health assistant. You analyze project data and give sharp, actionable insights.

Current Project: {project.name}
Description: {project.description or 'No description'}

Team Members ({len(members)}):
{members_text}

Tasks ({len(tasks)} total):
{tasks_text}

Stats:
- Todo: {sum(1 for t in tasks if t.status == 'todo')}
- In Progress: {sum(1 for t in tasks if t.status == 'in_progress')}
- Done: {sum(1 for t in tasks if t.status == 'done')}
- Overdue: {sum(1 for t in tasks if t.due_date and t.due_date < now and t.status != 'done')}

Be concise, direct, and helpful. Answer in 3-5 sentences max unless a breakdown is needed."""

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 500,
                "system": system_prompt,
                "messages": [{"role": "user", "content": data.question}]
            }
        )

    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="AI service error")

    result = response.json()
    answer = result["content"][0]["text"]
    return {"answer": answer, "project": project.name}
