# FlowDesk — Team Task Intelligence Platform

> A full-stack team task manager with role-based access control and an **AI-powered project health assistant** built on Claude.

🔗 **Live URL:** `[your-railway-url]`  
📁 **GitHub:** `[your-repo-url]`

---

## What Makes FlowDesk Different

While most task managers just track work, FlowDesk **understands** your project. The built-in AI assistant (powered by Claude) reads your entire project context — tasks, statuses, team members, deadlines — and answers questions like:

- *"What's blocking our progress?"*
- *"Who has the most work assigned?"*
- *"Give me a risk assessment of this project"*

This isn't a chatbot bolted on. It's a genuine analytics layer that treats task data as input to an intelligent system.

---

## Features

### Authentication
- JWT-based signup and login
- Tokens stored securely, auto-login on return visit
- Password hashing with bcrypt

### Project Management
- Create projects with name and description
- Multi-project support per user
- Project creator auto-assigned as Admin

### Role-Based Access Control
| Action | Admin | Member |
|---|---|---|
| Create tasks | ✅ | ✅ |
| Add/remove members | ✅ | ❌ |
| Delete project | ✅ | ❌ |
| Delete any task | ✅ | ❌ (own only) |
| View & update tasks | ✅ | ✅ |

### Task Management
- Create, assign, update, and delete tasks
- Status tracking: `Todo → In Progress → Done`
- Priority levels: Low / Medium / High
- Due dates with automatic overdue detection
- Filter tasks by status

### Dashboard
- Cross-project task summary
- Overdue count, completion rate, personal workload

### AI Assistant
- Per-project AI chat powered by Claude API
- Full project context injected automatically
- Quick prompt chips for common questions
- Real-time response streaming

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python) |
| Database | SQLite (dev) / PostgreSQL (prod-ready) |
| Auth | JWT + bcrypt |
| Frontend | Vanilla JS + CSS (single HTML file) |
| AI | Claude API (claude-sonnet-4) |
| Deployment | Railway |

---

## Local Development

```bash
# Clone the repo
git clone [your-repo]
cd flowdesk

# Install backend dependencies
cd backend
pip install -r requirements.txt

# Set environment variables (optional)
export ANTHROPIC_API_KEY="your-key-here"
export SECRET_KEY="your-secret-key"

# Run
python run.py
```

Open `http://localhost:8000` — the frontend is served by FastAPI.

---

## Railway Deployment

1. Push this repo to GitHub
2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Select your repo
4. Set environment variables in Railway dashboard:
   - `ANTHROPIC_API_KEY` — get from [console.anthropic.com](https://console.anthropic.com)
   - `SECRET_KEY` — any random string (e.g. `openssl rand -hex 32`)
5. Deploy. Railway auto-detects `railway.toml` and builds.

The app uses SQLite by default. If you add a Railway Postgres plugin, it auto-switches via `DATABASE_URL`.

---

## API Reference

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/auth/signup` | — | Create account |
| POST | `/api/auth/login` | — | Login |
| GET | `/api/auth/me` | ✅ | Current user |
| GET | `/api/projects/` | ✅ | My projects |
| POST | `/api/projects/` | ✅ | Create project |
| GET | `/api/projects/{id}` | ✅ | Project detail |
| DELETE | `/api/projects/{id}` | Admin | Delete project |
| POST | `/api/projects/{id}/members` | Admin | Add member |
| DELETE | `/api/projects/{id}/members/{uid}` | Admin | Remove member |
| POST | `/api/tasks/` | ✅ | Create task |
| GET | `/api/tasks/project/{id}` | ✅ | Project tasks |
| GET | `/api/tasks/my` | ✅ | My assigned tasks |
| PATCH | `/api/tasks/{id}` | ✅ | Update task |
| DELETE | `/api/tasks/{id}` | ✅/Admin | Delete task |
| GET | `/api/tasks/dashboard/summary` | ✅ | Dashboard stats |
| POST | `/api/ai/ask` | ✅ | AI project insight |

Full interactive docs available at `/docs` (FastAPI Swagger UI).

---

## Database Schema

```
users          → id, name, email, hashed_password, created_at
projects       → id, name, description, created_by, created_at
project_members → id, project_id, user_id, role (admin/member)
tasks          → id, title, description, status, priority, project_id,
                 assignee_id, created_by, due_date, created_at, updated_at
```

---

## Design Decisions

**Why FastAPI?** Python is the natural home for AI-adjacent work. FastAPI gives auto-docs, type safety, and async support — ideal for the AI endpoint.

**Why SQLite first?** Zero config, file-based, Railway-compatible. The codebase transparently upgrades to PostgreSQL via `DATABASE_URL`.

**Why a single HTML file frontend?** No build step, no npm, no deployment complexity. The entire UI ships as one file served directly by FastAPI — which means no CORS headaches and one-command deployment.

**Why Claude for AI?** The AI assistant isn't cosmetic. It receives full structured project context and answers real operational questions about team workload, blockers, and risk.

---

## Author

Built as part of a full-stack engineering assignment.  
Stack: FastAPI + SQLite + Claude API + Railway
