# Task Board Backend - 工作看板后端服务

基于 FastAPI + SQLite 的团队任务看板后端服务。

## 功能特性

- **成员状态管理** - 记录成员在线/离线、当前任务
- **任务跟踪** - 任务创建、状态流转（待办/进行中/已完成/阻塞）
- **产出记录** - 完成任务数、代码提交记录
- **告警机制** - 任务延期提醒、连续无产出预警

## 技术栈

- Python 3.8+
- FastAPI
- SQLite
- Uvicorn

## 快速开始

### 1. 安装依赖

```bash
cd task_board
pip install -r requirements.txt
```

### 2. 启动服务

```bash
python main.py
```

服务将在 `http://localhost:8000` 启动。

### 3. API 文档

启动后访问:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## API 接口

### 成员管理

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | /members | 创建成员 |
| GET | /members | 获取成员列表 |
| GET | /members/{id} | 获取成员详情 |
| PUT | /members/{id} | 更新成员信息 |
| POST | /members/{id}/status | 更新成员状态 |

### 任务管理

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | /tasks | 创建任务 |
| GET | /tasks | 获取任务列表 |
| GET | /tasks/{id} | 获取任务详情 |
| PUT | /tasks/{id} | 更新任务 |
| POST | /tasks/{id}/complete | 完成任务 |

### 看板数据

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | /dashboard | 获取看板数据 |
| GET | /outputs | 获取产出记录 |
| POST | /outputs | 记录产出 |

## 数据模型

### Member (成员)

```json
{
  "id": 1,
  "name": "张三",
  "email": "zhangsan@example.com",
  "role": "member",
  "status": "online",
  "current_task_id": 5,
  "last_active_at": "2026-03-15T10:30:00"
}
```

### Task (任务)

```json
{
  "id": 1,
  "title": "完成用户登录功能",
  "description": "实现JWT认证",
  "status": "in_progress",
  "priority": "high",
  "assignee_id": 1,
  "due_date": "2026-03-20",
  "completed_at": null,
  "created_at": "2026-03-15T09:00:00"
}
```

### Status 状态流转

- `pending` - 待办
- `in_progress` - 进行中
- `completed` - 已完成
- `blocked` - 阻塞

### Priority 优先级

- `low` - 低
- `medium` - 中
- `high` - 高
- `urgent` - 紧急

## 使用示例

### 创建成员

```bash
curl -X POST "http://localhost:8000/members" \
  -H "Content-Type: application/json" \
  -d '{"name": "张三", "email": "zhangsan@example.com", "role": "backend"}'
```

### 创建任务

```bash
curl -X POST "http://localhost:8000/tasks" \
  -H "Content-Type: application/json" \
  -d '{"title": "开发用户API", "priority": "high", "assignee_id": 1, "due_date": "2026-03-20"}'
```

### 获取看板数据

```bash
curl "http://localhost:8000/dashboard"
```

### 记录代码提交

```bash
curl -X POST "http://localhost:8000/outputs" \
  -H "Content-Type: application/json" \
  -d '{"member_id": 1, "task_id": 1, "commit_hash": "abc123", "commit_message": "feat: add user login"}'
```

## 告警机制

看板会自动检测以下告警：

1. **任务延期** - 当任务到期且状态非已完成/阻塞时触发
2. **无产出预警** - 成员连续3天无产出（无提交记录）时触发

告警信息可在 `/dashboard` 返回的 `alerts` 字段中获取。

## 项目结构

```
task_board/
├── main.py          # 主应用文件
├── requirements.txt # 依赖
└── README.md        # 说明文档
```

## 许可证

MIT
