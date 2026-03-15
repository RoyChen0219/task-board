# 工作看板前端 (Task Board Frontend)

团队任务管理与进度追踪系统的前端应用。

## 功能特性

- **成员状态卡片** - 显示成员头像、状态灯、当前任务
- **任务看板** - 列式展示（待办/进行中/已完成/阻塞）
- **产出统计** - 当日完成任务数、7天趋势图
- **告警提示** - 延期任务红色高亮

## 技术栈

- HTML5
- Vanilla JavaScript
- Tailwind CSS (CDN)
- Chart.js (可选，用于图表)

## 启动方式

### 1. 直接打开 HTML 文件

```bash
# 直接用浏览器打开
open frontend/index.html

# 或使用 Python 本地服务器
cd frontend
python3 -m http.server 8080
# 访问 http://localhost:8080
```

### 2. 后端 API 配置

前端默认尝试连接 `http://localhost:8003`。

后端 API 需要实现以下端点：

#### GET /members
返回团队成员列表

**响应示例：**
```json
[
  {
    "id": 1,
    "name": "张三",
    "avatar": "https://example.com/avatar.jpg",
    "status": "online",
    "currentTask": "用户登录功能"
  }
]
```

**status 取值：** `online`（在线）、`busy`（忙碌）、`offline`（离线）

#### GET /tasks
返回任务列表

**响应示例：**
```json
[
  {
    "id": 1,
    "title": "完成用户认证模块",
    "assignee": "张三",
    "status": "todo",
    "priority": "high",
    "dueDate": "2026-03-16",
    "overdue": false
  }
]
```

**status 取值：** `todo`（待办）、`inprogress`（进行中）、`done`（已完成）、`blocked`（阻塞）

**priority 取值：** `high`（高）、`medium`（中）、`low`（低）

#### GET /stats
返回统计数据（可选，如不提供则前端从 tasks 计算）

**响应示例：**
```json
{
  "todayCompleted": 5,
  "overdueCount": 2,
  "inProgressCount": 3,
  "trend": [
    { "date": "03-09", "count": 3 },
    { "date": "03-10", "count": 5 }
  ]
}
```

### 3. 使用模拟数据

当前端无法连接到后端 API 时，会自动使用内置的模拟数据进行演示。

## 项目结构

```
task_board/
├── frontend/
│   ├── index.html    # 主页面
│   └── README.md     # 本文件
└── backend/          # 后端目录（需自行创建）
```

## 浏览器兼容性

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## 自定义配置

如需修改 API 地址，编辑 `index.html` 中的：

```javascript
const API_BASE = 'http://localhost:8003';
```

## 截图预览

前端页面包含：
1. 顶部成员状态栏 - 显示6位成员的头像、在线状态和当前任务
2. 统计卡片 - 今日完成、延期告警、进行中数量
3. 7天趋势图 - 柱状图展示完成任务趋势
4. 4列看板 - 待办/进行中/已完成/阻塞

---

如有问题，请检查：
1. 后端服务是否启动并监听 8003 端口
2. API 端点路径是否正确
3. 浏览器控制台是否有错误信息
