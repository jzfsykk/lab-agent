# 智能实验室预约系统 · Lab Agent

> 面向高校实验室的一站式预约管理平台：实验室与设备台账、在线预约与审核、AI 知识库问答、智能预约 Agent。

<p>
  <img alt="Python" src="https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white">
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white">
  <img alt="Vue" src="https://img.shields.io/badge/Vue-3.5-4FC08D?logo=vuedotjs&logoColor=white">
  <img alt="Vite" src="https://img.shields.io/badge/Vite-8-646CFF?logo=vite&logoColor=white">
  <img alt="MySQL" src="https://img.shields.io/badge/MySQL-8.0%2B-4479A1?logo=mysql&logoColor=white">
  <img alt="LangGraph" src="https://img.shields.io/badge/LangGraph-Agent-1C3C3C">
  <img alt="License" src="https://img.shields.io/badge/License-MIT-yellow.svg">
</p>

---

## 简介

实验室资源分散、预约靠纸质登记、设备状态没人维护——这是大多数高校实验室的日常。本项目把这些环节收进一套前后端分离的系统里：

- **管理端**负责实验室、设备、用户、预约审核的全生命周期维护；
- **学生端**可以查空闲实验室、看设备清单、提交预约、查看自己的预约进度；
- **AI 助手**接入了实验室的知识库（开放时间、安全规范、设备使用说明、预约规则），支持流式问答，并且能通过 Tool Calling 直接查询真实数据、代为完成预约。

后端使用 FastAPI + SQLAlchemy 2.0，前端使用 Vue 3 + Element Plus，AI 部分基于 RAG（Chroma 向量库 + BGE 中文向量模型）与 LangGraph Agent。

## 功能特性

### 基础业务

| 模块 | 能力 |
| --- | --- |
| 认证授权 | JWT 登录/注册、Token 路由守卫、密码 bcrypt 加盐哈希、登录态过期自动跳转 |
| 用户管理 | 个人信息查看与修改、头像上传、修改密码、管理员对用户的增删改查与启用/禁用 |
| 实验室管理 | 实验室 CRUD、容纳人数、开放时段、位置维护、状态开关 |
| 设备管理 | 设备 CRUD、按实验室归属、型号规格、库存数量、可用状态 |
| 预约流程 | 提交预约（实验室 + 设备 + 日期 + 时段）、我的预约、取消预约、管理员审核（通过/拒绝）、过期预约自动扫描取消 |
| 文件服务 | 头像与附件上传、扩展名白名单、大小限制、静态资源挂载 |

### AI 能力

| 能力 | 实现 |
| --- | --- |
| 知识库问答（RAG） | Markdown 知识库分块 → BGE 中文向量化 → Chroma 检索 → 拼装上下文回答 |
| 流式输出 | SSE 推送 `status → tool_start → tool_end → token → done` 全过程事件，前端逐步渲染 |
| Tool Calling | Agent 可调用后端工具查询实验室空闲情况、设备清单、用户预约记录 |
| 智能预约 Agent | 基于 LangGraph 的状态机：理解意图 → 收集槽位 → 校验冲突 → 落库 → 反馈结果 |
| 优雅降级 | 未配置大模型密钥时，AI 接口返回明确业务提示，其余功能完全不受影响 |

## 技术栈

**后端**

- FastAPI 0.115 + Uvicorn
- SQLAlchemy 2.0（`Mapped` / `mapped_column` 声明式模型）
- MySQL 8.0+ / PyMySQL
- PyJWT（HS256）+ bcrypt
- Pydantic Settings（`.env` 集中配置）
- 统一响应体 + 全局异常处理（业务异常 / 校验异常 / HTTP 异常 / 兜底异常）
- ChromaDB + sentence-transformers（`bge-small-zh-v1.5`）
- LangGraph + langchain-openai

**前端**

- Vue 3.5（Composition API + `<script setup>`）
- Vue Router 5
- Element Plus 2.14
- Axios（统一拦截器：Token 注入、错误提示、401 跳转）
- Vite 8（`/api`、`/uploads` 代理，SSE 关闭缓冲）
- marked + DOMPurify（AI 回复的 Markdown 渲染与 XSS 过滤）

## 系统架构

```mermaid
flowchart LR
    subgraph Client["浏览器"]
        V["Vue 3 + Element Plus<br/>管理端 / 学生端"]
    end

    subgraph Server["FastAPI 服务"]
        direction TB
        R["Router 层<br/>auth / user / lab / equipment<br/>reservation / files / ai"]
        S["Service 层<br/>业务编排"]
        D["Model 层<br/>SQLAlchemy ORM"]
        AI["AI 服务<br/>RAG + Agent"]
    end

    subgraph Storage["存储"]
        DB[("MySQL<br/>lab_agent")]
        FS[["uploads/<br/>头像与附件"]]
        VEC[("Chroma<br/>向量库")]
        KB[/"data/kb/*.md<br/>知识库文档"/]
    end

    LLM["大模型 API<br/>OpenAI 兼容接口"]

    V -- "/api/*" --> R
    V -- "/uploads/*" --> FS
    R --> S --> D --> DB
    S --> AI
    AI --> VEC
    AI --> LLM
    KB -. 首次加载时分块向量化 .-> VEC
    S --> FS
    AI -- "Tool Calling" --> S
```

## 目录结构

```
lab-agent/
├── backend/
│   ├── app/
│   │   ├── api/                # 路由层：auth / user / lab / equipment / reservation / files / ai
│   │   ├── services/           # 业务逻辑：认证、用户、实验室、设备、预约、知识库、Agent
│   │   ├── models/             # SQLAlchemy 模型：User / Lab / Equipment / Reservation
│   │   ├── schemas/            # Pydantic 请求与响应模型
│   │   ├── common/             # 统一响应体、业务异常、全局异常处理
│   │   ├── dependencies/       # 依赖注入：当前用户、角色校验
│   │   ├── utils/              # JWT 编解码、密码哈希
│   │   ├── config.py           # 配置中心（读取 .env）
│   │   ├── database.py         # 引擎、会话、Base
│   │   └── main.py             # 应用入口：路由挂载、CORS、静态资源、生命周期任务
│   ├── data/
│   │   ├── kb/                 # 知识库原文（Markdown）
│   │   ├── chroma/             # 向量库持久化目录（运行时生成）
│   │   └── models/             # 本地向量模型（运行时下载）
│   ├── scripts/
│   │   ├── seed_data.py        # 演示数据：8 间实验室 + 32 台设备
│   │   └── create_admin.py     # 创建管理员账号
│   ├── uploads/                # 上传文件目录（运行时生成）
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── api/                # 接口封装，按模块拆分
│   │   ├── views/              # 页面：登录、注册、首页、实验室、设备、预约、审核、AI 助手
│   │   ├── layouts/            # 主框架布局（侧边栏 + 顶栏）
│   │   ├── components/         # 通用组件
│   │   ├── router/             # 路由表与登录守卫
│   │   └── utils/              # axios 封装、Token 存取
│   ├── vite.config.js
│   └── package.json
├── docs/
│   └── architecture.md         # 架构与数据模型说明
└── README.md
```

## 快速开始

### 环境要求

| 组件 | 版本 |
| --- | --- |
| Python | 3.12+（开发环境 3.14） |
| Node.js | 18+（建议 20 LTS） |
| MySQL | 8.0+（开发环境 9.7） |

### 1. 获取代码

```bash
git clone https://github.com/jzfsykk/lab-agent.git
cd lab-agent
```

### 2. 初始化数据库

```sql
CREATE DATABASE lab_agent DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 建议使用专用账号，不要用 root
CREATE USER 'lab_app'@'127.0.0.1' IDENTIFIED BY '你的强密码';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, DROP, REFERENCES
  ON lab_agent.* TO 'lab_app'@'127.0.0.1';
FLUSH PRIVILEGES;
```

> 数据表由 `Base.metadata.create_all()` 在服务启动时自动创建，无需手动建表。

### 3. 启动后端

```bash
cd backend

# 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

pip install -r requirements.txt

# 复制配置模板并填写
copy .env.example .env           # Windows
# cp .env.example .env           # macOS / Linux
```

编辑 `backend/.env`：

```ini
DATABASE_URL=mysql+pymysql://lab_app:你的强密码@127.0.0.1:3306/lab_agent
JWT_SECRET_KEY=<用 python -c "import secrets;print(secrets.token_urlsafe(64))" 生成>
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=24

LLM_API_KEY=<你的大模型 API Key，可留空>
LLM_BASE_URL=https://api.agnes-ai.cn/v1
LLM_MODEL=agnes-2.5-flash
```

```bash
# 启动（务必加 --reload-dir app，否则会递归监听 .venv 与 data/chroma）
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --reload-dir app --port 8000
```

接口文档：<http://127.0.0.1:8000/docs>

### 4. 初始化演示数据

```bash
cd backend

# 8 间实验室 + 32 台设备（幂等，可重复执行）
.venv\Scripts\python.exe -m scripts.seed_data

# 创建管理员账号
.venv\Scripts\python.exe -m scripts.create_admin
```

默认管理员：`admin` / `admin123`（**部署到公网前必须修改**）

### 5. 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问 <http://localhost:5173>，使用 `admin / admin123` 登录，或在注册页自行创建学生账号。

## 配置说明

| 变量 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `DATABASE_URL` | 是 | — | MySQL 连接串，格式 `mysql+pymysql://用户:密码@主机:端口/库名` |
| `JWT_SECRET_KEY` | 是 | — | JWT 签名密钥，缺失会导致服务启动失败；建议 64 字节随机串 |
| `JWT_ALGORITHM` | 否 | `HS256` | 签名算法 |
| `JWT_EXPIRE_HOURS` | 否 | `24` | Token 有效期（小时） |
| `LLM_API_KEY` | 否 | 空 | 大模型密钥，留空则 AI 接口返回业务提示，其余功能正常 |
| `LLM_BASE_URL` | 否 | `https://api.agnes-ai.cn/v1` | OpenAI 兼容接口地址 |
| `LLM_MODEL` | 否 | `agnes-2.5-flash` | 模型名称 |

> `backend/.env` 已在 `.gitignore` 中排除，不会进入版本库。请以 `backend/.env.example` 为模板。

## API 概览

所有接口以 `/api` 为前缀，除登录/注册外均需在请求头携带 `Authorization: Bearer <token>`。

统一响应体：

```json
{ "code": 200, "message": "success", "data": {} }
```

| 模块 | 方法 | 路径 | 说明 |
| --- | --- | --- | --- |
| 认证 | POST | `/api/auth/register` | 注册（默认学生角色） |
| 认证 | POST | `/api/auth/login` | 登录，返回 JWT |
| 用户 | GET | `/api/user/me` | 当前用户信息 |
| 用户 | PUT | `/api/user/me` | 修改个人信息 |
| 用户 | PUT | `/api/user/password` | 修改密码 |
| 用户 | GET | `/api/user/list` | 用户列表（管理员） |
| 用户 | POST | `/api/user` | 新增用户（管理员） |
| 用户 | PUT | `/api/user/{user_id}` | 修改用户（管理员） |
| 用户 | DELETE | `/api/user/{user_id}` | 删除用户（管理员） |
| 文件 | POST | `/api/files/upload` | 上传文件，返回访问路径 |
| 实验室 | GET | `/api/lab/list` | 实验室列表 |
| 实验室 | GET | `/api/lab/{lab_id}` | 实验室详情 |
| 实验室 | POST | `/api/lab` | 新增实验室（管理员） |
| 实验室 | PUT | `/api/lab/{lab_id}` | 修改实验室（管理员） |
| 实验室 | DELETE | `/api/lab/{lab_id}` | 删除实验室（管理员） |
| 设备 | GET | `/api/equipment/list` | 设备列表（可按实验室过滤） |
| 设备 | POST | `/api/equipment` | 新增设备（管理员） |
| 设备 | PUT | `/api/equipment/{equipment_id}` | 修改设备（管理员） |
| 设备 | DELETE | `/api/equipment/{equipment_id}` | 删除设备（管理员） |
| 预约 | POST | `/api/reservation` | 提交预约 |
| 预约 | GET | `/api/reservation/my` | 我的预约 |
| 预约 | GET | `/api/reservation/list` | 全部预约（管理员） |
| 预约 | PUT | `/api/reservation/{id}/cancel` | 取消预约 |
| 预约 | PUT | `/api/reservation/{id}/audit` | 审核预约（管理员） |
| AI | POST | `/api/ai/chat` | 一次性问答 |
| AI | POST | `/api/ai/chat/stream` | SSE 流式问答 |

### 预约状态机

```mermaid
stateDiagram-v2
    [*] --> 待审核: 学生提交
    待审核 --> 已通过: 管理员审核通过
    待审核 --> 已拒绝: 管理员拒绝
    待审核 --> 已取消: 学生取消 / 超时自动取消
    已通过 --> 已取消: 学生取消
    已通过 --> [*]
    已拒绝 --> [*]
    已取消 --> [*]
```

`status` 取值：`0` 待审核 · `1` 已通过 · `2` 已拒绝 · `3` 已取消

## 角色与权限

| 角色 | `role` 值 | 可见菜单 |
| --- | --- | --- |
| 管理员 | `admin` | 首页、实验室管理、设备管理、实验室设备、用户管理、预约审核、个人中心、AI 助手 |
| 学生 | `student` | 首页、实验室列表、我的预约、个人中心、AI 助手 |

权限在两层校验：前端路由守卫控制页面可达性，后端依赖注入（`dependencies/auth.py`）校验 Token 与角色，越权请求返回 403。

## 数据模型

```mermaid
erDiagram
    USERS ||--o{ RESERVATIONS : 发起
    LABS ||--o{ EQUIPMENTS : 包含
    LABS ||--o{ RESERVATIONS : 被预约
    EQUIPMENTS ||--o{ RESERVATIONS : 被预约

    USERS {
        int id PK
        string username
        string password "bcrypt 哈希"
        string name
        string role "student / admin"
        string email
        string phone
        string avatar
        int status "0 禁用 1 正常"
    }
    LABS {
        int id PK
        string name
        string location
        int capacity
        string open_time
        string close_time
        int status
    }
    EQUIPMENTS {
        int id PK
        int lab_id FK
        string name
        string description
        string specification
        int quantity
        int status
    }
    RESERVATIONS {
        int id PK
        int user_id FK
        int lab_id FK
        int equipment_id FK
        string date
        string start_time
        string end_time
        string remark
        int status "0 待审核 1 通过 2 拒绝 3 取消"
    }
```

## 部署提示

- **必须修改**：`JWT_SECRET_KEY`、数据库密码、默认管理员密码
- `CORS` 白名单在 `backend/app/main.py` 中，公网部署时改成你的实际前端域名
- `uploads/` 目录需要有写权限；生产环境建议换成对象存储
- 向量模型 `bge-small-zh-v1.5` 首次运行会自动下载（约 91 MB），也可手动放到 `backend/data/models/` 下避免联网
- 建议用 Nginx 反代前端静态产物，并将 `/api`、`/uploads` 转发到 Uvicorn

## 开发说明

```bash
# 后端：格式化与静态检查（可选）
pip install ruff
ruff check backend/app

# 前端：格式化
cd frontend && npm run format
```

- 分支策略：`main` 为主分支，功能开发走 `feat/*`
- 提交信息遵循 Conventional Commits（`feat:` / `fix:` / `docs:` / `refactor:`）

## License

[MIT](LICENSE)

## 致谢

- [FastAPI](https://fastapi.tiangolo.com/) · [SQLAlchemy](https://www.sqlalchemy.org/) · [Vue](https://vuejs.org/) · [Element Plus](https://element-plus.org/)
- [LangGraph](https://github.com/langchain-ai/langgraph) · [ChromaDB](https://www.trychroma.com/) · [BAAI/bge-small-zh-v1.5](https://huggingface.co/BAAI/bge-small-zh-v1.5)
