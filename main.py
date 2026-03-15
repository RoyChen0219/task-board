"""
Task Board Backend - FastAPI + SQLite
工作看板后端服务
"""
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from contextlib import contextmanager

# 数据库配置
DATABASE_PATH = "task_board.db"

app = FastAPI(title="Task Board API", version="1.0.0")

# ==================== Database Setup ====================

@contextmanager
def get_db():
    """数据库连接上下文管理器"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """初始化数据库表"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 成员表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                role TEXT DEFAULT 'member',
                status TEXT DEFAULT 'offline',
                current_task_id INTEGER,
                last_active_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 任务表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'pending',
                priority TEXT DEFAULT 'medium',
                assignee_id INTEGER,
                due_date TEXT,
                completed_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (assignee_id) REFERENCES members(id)
            )
        """)
        
        # 产出记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS outputs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                member_id INTEGER NOT NULL,
                task_id INTEGER,
                commit_hash TEXT,
                commit_message TEXT,
                output_type TEXT DEFAULT 'code_commit',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (member_id) REFERENCES members(id),
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            )
        """)
        
        # 每日记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL UNIQUE,
                task_snapshot TEXT NOT NULL,
                member_snapshot TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()

# 启动时初始化数据库
init_db()

# ==================== Pydantic Models ====================

class MemberBase(BaseModel):
    name: str
    email: str
    role: str = "member"

class MemberCreate(MemberBase):
    pass

class MemberUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    current_task_id: Optional[int] = None

class MemberResponse(MemberBase):
    id: int
    status: str
    current_task_id: Optional[int]
    last_active_at: Optional[str]
    
    class Config:
        from_attributes = True

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    priority: str = "medium"
    due_date: Optional[str] = None

class TaskCreate(TaskBase):
    assignee_id: Optional[int] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    assignee_id: Optional[int] = None
    due_date: Optional[str] = None

class TaskResponse(TaskBase):
    id: int
    status: str
    assignee_id: Optional[int]
    completed_at: Optional[str]
    created_at: str
    
    class Config:
        from_attributes = True

class OutputCreate(BaseModel):
    member_id: int
    task_id: Optional[int] = None
    commit_hash: Optional[str] = None
    commit_message: Optional[str] = None
    output_type: str = "code_commit"

class DashboardResponse(BaseModel):
    members: List[MemberResponse]
    tasks: List[TaskResponse]
    task_stats: dict
    output_stats: dict
    alerts: List[dict]

class DailyRecordResponse(BaseModel):
    id: int
    date: str
    task_snapshot: str
    member_snapshot: str
    created_at: str

class DailySummaryResponse(BaseModel):
    date: str
    task_summary: dict
    member_summary: dict
    created_at: str

# ==================== API Routes ====================

# --- Members API ---

@app.post("/members", response_model=MemberResponse)
def create_member(member: MemberCreate):
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO members (name, email, role) VALUES (?, ?, ?)",
                (member.name, member.email, member.role)
            )
            conn.commit()
            member_id = cursor.lastrowid
            
            cursor.execute("SELECT * FROM members WHERE id = ?", (member_id,))
            return dict(cursor.fetchone())
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="Email already exists")

@app.get("/members", response_model=List[MemberResponse])
def get_members(status: Optional[str] = None):
    with get_db() as conn:
        cursor = conn.cursor()
        if status:
            cursor.execute("SELECT * FROM members WHERE status = ?", (status,))
        else:
            cursor.execute("SELECT * FROM members")
        return [dict(row) for row in cursor.fetchall()]

@app.get("/members/{member_id}", response_model=MemberResponse)
def get_member(member_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM members WHERE id = ?", (member_id,))
        member = cursor.fetchone()
        if not member:
            raise HTTPException(status_code=404, detail="Member not found")
        return dict(member)

@app.put("/members/{member_id}", response_model=MemberResponse)
def update_member(member_id: int, member: MemberUpdate):
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 构建动态更新语句
        updates = []
        values = []
        for field, value in member.model_dump(exclude_unset=True).items():
            updates.append(f"{field} = ?")
            values.append(value)
        
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        values.append(member_id)
        query = f"UPDATE members SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, values)
        conn.commit()
        
        cursor.execute("SELECT * FROM members WHERE id = ?", (member_id,))
        result = cursor.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Member not found")
        return dict(result)

@app.post("/members/{member_id}/status")
def update_member_status(member_id: int, status: str):
    """更新成员在线状态"""
    valid_statuses = ["online", "offline", "away"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE members SET status = ?, last_active_at = ? WHERE id = ?",
            (status, datetime.now().isoformat(), member_id)
        )
        conn.commit()
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Member not found")
        return {"message": "Status updated", "status": status}

# --- Tasks API ---

@app.post("/tasks", response_model=TaskResponse)
def create_task(task: TaskCreate):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO tasks (title, description, priority, assignee_id, due_date) VALUES (?, ?, ?, ?, ?)",
            (task.title, task.description, task.priority, task.assignee_id, task.due_date)
        )
        conn.commit()
        task_id = cursor.lastrowid
        
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        return dict(cursor.fetchone())

@app.get("/tasks", response_model=List[TaskResponse])
def get_tasks(status: Optional[str] = None, assignee_id: Optional[int] = None):
    with get_db() as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM tasks WHERE 1=1"
        params = []
        
        if status:
            query += " AND status = ?"
            params.append(status)
        if assignee_id:
            query += " AND assignee_id = ?"
            params.append(assignee_id)
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

@app.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(task_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        task = cursor.fetchone()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return dict(task)

@app.put("/tasks/{task_id}", response_model=TaskResponse)
def update_task(task_id: int, task: TaskUpdate):
    with get_db() as conn:
        cursor = conn.cursor()
        
        updates = []
        values = []
        for field, value in task.model_dump(exclude_unset=True).items():
            updates.append(f"{field} = ?")
            values.append(value)
        
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        values.append(task_id)
        query = f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, values)
        conn.commit()
        
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        result = cursor.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Task not found")
        return dict(result)

@app.post("/tasks/{task_id}/complete", response_model=TaskResponse)
def complete_task(task_id: int):
    """完成任务"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 检查任务是否存在
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        task = cursor.fetchone()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # 更新任务状态
        cursor.execute(
            "UPDATE tasks SET status = 'completed', completed_at = ? WHERE id = ?",
            (datetime.now().isoformat(), task_id)
        )
        
        # 如果有 assignee，更新成员的当前任务
        if task["assignee_id"]:
            cursor.execute(
                "UPDATE members SET current_task_id = NULL WHERE id = ?",
                (task["assignee_id"],)
            )
        
        conn.commit()
        
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        return dict(cursor.fetchone())

# --- Outputs API ---

@app.post("/outputs")
def create_output(output: OutputCreate):
    """记录产出（代码提交等）"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO outputs (member_id, task_id, commit_hash, commit_message, output_type) VALUES (?, ?, ?, ?, ?)",
            (output.member_id, output.task_id, output.commit_hash, output.commit_message, output.output_type)
        )
        conn.commit()
        
        # 更新成员最后活跃时间
        cursor.execute(
            "UPDATE members SET last_active_at = ?, status = 'online' WHERE id = ?",
            (datetime.now().isoformat(), output.member_id)
        )
        conn.commit()
        
        return {"message": "Output recorded", "id": cursor.lastrowid}

@app.get("/outputs")
def get_outputs(member_id: Optional[int] = None, limit: int = 50):
    """获取产出记录"""
    with get_db() as conn:
        cursor = conn.cursor()
        if member_id:
            cursor.execute(
                "SELECT * FROM outputs WHERE member_id = ? ORDER BY created_at DESC LIMIT ?",
                (member_id, limit)
            )
        else:
            cursor.execute("SELECT * FROM outputs ORDER BY created_at DESC LIMIT ?", (limit,))
        return [dict(row) for row in cursor.fetchall()]

# --- Dashboard API ---

@app.get("/dashboard", response_model=DashboardResponse)
def get_dashboard():
    """获取看板数据"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 获取所有成员
        cursor.execute("SELECT * FROM members")
        members = [dict(row) for row in cursor.fetchall()]
        
        # 获取所有任务
        cursor.execute("SELECT * FROM tasks")
        tasks = [dict(row) for row in cursor.fetchall()]
        
        # 任务统计
        task_stats = {
            "total": len(tasks),
            "pending": len([t for t in tasks if t["status"] == "pending"]),
            "in_progress": len([t for t in tasks if t["status"] == "in_progress"]),
            "completed": len([t for t in tasks if t["status"] == "completed"]),
            "blocked": len([t for t in tasks if t["status"] == "blocked"]),
        }
        
        # 产出统计
        cursor.execute("SELECT COUNT(*) as count FROM outputs")
        output_stats = {"total_outputs": cursor.fetchone()["count"]}
        
        # 成员产出统计
        cursor.execute("""
            SELECT member_id, COUNT(*) as count 
            FROM outputs 
            WHERE created_at >= date('now', '-7 days')
            GROUP BY member_id
        """)
        output_by_member = {row["member_id"]: row["count"] for row in cursor.fetchall()}
        output_stats["by_member"] = output_by_member
        
        # 告警检测
        alerts = []
        now = datetime.now()
        
        # 1. 任务延期告警
        for task in tasks:
            if task["status"] not in ["completed", "blocked"] and task["due_date"]:
                due_date = datetime.fromisoformat(task["due_date"])
                if due_date < now:
                    alerts.append({
                        "type": "task_overdue",
                        "severity": "high",
                        "message": f"任务 '{task['title']}' 已延期",
                        "task_id": task["id"]
                    })
        
        # 2. 连续无产出预警（3天无产出）
        for member in members:
            if member["last_active_at"]:
                last_active = datetime.fromisoformat(member["last_active_at"])
                days_inactive = (now - last_active).days
                if days_inactive >= 3 and member["status"] == "online":
                    alerts.append({
                        "type": "no_output",
                        "severity": "medium",
                        "message": f"成员 '{member['name']}' 已 {days_inactive} 天无产出",
                        "member_id": member["id"]
                    })
        
        return {
            "members": members,
            "tasks": tasks,
            "task_stats": task_stats,
            "output_stats": output_stats,
            "alerts": alerts
        }

# --- Daily Records API ---

@app.post("/daily-records/snapshot")
def create_daily_snapshot():
    """手动保存当天快照"""
    import json
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 获取当天任务快照
        cursor.execute("SELECT * FROM tasks")
        tasks = [dict(row) for row in cursor.fetchall()]
        task_snapshot = json.dumps(tasks, ensure_ascii=False)
        
        # 获取当天成员快照
        cursor.execute("SELECT * FROM members")
        members = [dict(row) for row in cursor.fetchall()]
        member_snapshot = json.dumps(members, ensure_ascii=False)
        
        # 检查是否已存在当天的记录
        cursor.execute("SELECT id FROM daily_records WHERE date = ?", (today,))
        existing = cursor.fetchone()
        
        if existing:
            # 更新现有记录
            cursor.execute(
                "UPDATE daily_records SET task_snapshot = ?, member_snapshot = ? WHERE date = ?",
                (task_snapshot, member_snapshot, today)
            )
            message = "Daily snapshot updated"
        else:
            # 插入新记录
            cursor.execute(
                "INSERT INTO daily_records (date, task_snapshot, member_snapshot) VALUES (?, ?, ?)",
                (today, task_snapshot, member_snapshot)
            )
            message = "Daily snapshot created"
        
        conn.commit()
        
        return {"message": message, "date": today}

@app.get("/daily-records", response_model=List[DailyRecordResponse])
def get_daily_records(date: Optional[str] = None):
    """按日期查询历史记录"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        if date:
            cursor.execute(
                "SELECT * FROM daily_records WHERE date = ? ORDER BY created_at DESC",
                (date,)
            )
        else:
            cursor.execute("SELECT * FROM daily_records ORDER BY date DESC")
        
        return [dict(row) for row in cursor.fetchall()]

@app.get("/daily-records/summary", response_model=DailySummaryResponse)
def get_daily_summary(date: str):
    """获取某天工作汇总"""
    import json
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 查询指定日期的记录
        cursor.execute(
            "SELECT * FROM daily_records WHERE date = ?",
            (date,)
        )
        record = cursor.fetchone()
        
        if not record:
            raise HTTPException(status_code=404, detail=f"No record found for date: {date}")
        
        # 解析快照
        tasks = json.loads(record["task_snapshot"])
        members = json.loads(record["member_snapshot"])
        
        # 任务汇总
        task_summary = {
            "total": len(tasks),
            "pending": len([t for t in tasks if t["status"] == "pending"]),
            "in_progress": len([t for t in tasks if t["status"] == "in_progress"]),
            "completed": len([t for t in tasks if t["status"] == "completed"]),
            "blocked": len([t for t in tasks if t["status"] == "blocked"]),
            "by_priority": {
                "high": len([t for t in tasks if t.get("priority") == "high"]),
                "medium": len([t for t in tasks if t.get("priority") == "medium"]),
                "low": len([t for t in tasks if t.get("priority") == "low"]),
            }
        }
        
        # 成员汇总
        member_summary = {
            "total": len(members),
            "online": len([m for m in members if m.get("status") == "online"]),
            "offline": len([m for m in members if m.get("status") == "offline"]),
            "away": len([m for m in members if m.get("status") == "away"]),
            "members": [
                {
                    "id": m["id"],
                    "name": m["name"],
                    "role": m["role"],
                    "status": m["status"],
                    "current_task_id": m.get("current_task_id")
                }
                for m in members
            ]
        }
        
        return {
            "date": record["date"],
            "task_summary": task_summary,
            "member_summary": member_summary,
            "created_at": record["created_at"]
        }

# --- Health Check ---

@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


# 定时任务：每天18:00自动保存快照
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()

def scheduled_snapshot():
    """定时保存每日快照"""
    try:
        conn = sqlite3.connect('task_board.db')
        c = conn.cursor()
        
        tasks = c.execute('SELECT id, title, status, assignee_id, priority FROM tasks').fetchall()
        members = c.execute('SELECT id, name, role, status, current_task_id FROM members').fetchall()
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        task_snapshot = json.dumps([
            {'id': t[0], 'title': t[1], 'status': t[2], 'assignee_id': t[3], 'priority': t[4]} 
            for t in tasks
        ])
        member_snapshot = json.dumps([
            {'id': m[0], 'name': m[1], 'role': m[2], 'status': m[3], 'current_task_id': m[4]} 
            for m in members
        ])
        
        existing = c.execute('SELECT id FROM daily_records WHERE date = ?', (today,)).fetchone()
        
        if existing:
            c.execute('UPDATE daily_records SET task_snapshot = ?, member_snapshot = ?, created_at = ? WHERE date = ?',
                (task_snapshot, member_snapshot, datetime.now().isoformat(), today))
        else:
            c.execute('INSERT INTO daily_records (date, task_snapshot, member_snapshot, created_at) VALUES (?, ?, ?, ?)',
                (today, task_snapshot, member_snapshot, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        print(f"[Scheduler] 自动保存快照: {today}")
    except Exception as e:
        print(f"[Scheduler] 保存失败: {e}")

# 每天下午6点执行
scheduler.add_job(func=scheduled_snapshot, trigger="cron", hour=18, minute=0)
scheduler.start()
print("[Scheduler] 定时任务已启动: 每天18:00自动保存")
