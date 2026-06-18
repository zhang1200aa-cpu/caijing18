# 🚀 caijing18 tg公开频道自动获取,AI总结.

基于 Telegram 公开频道网页抓取的自动化财经新闻聚合与管理平台，支持 **AI 智能总结**、多维度搜索筛选、定时任务维护，开箱即用的 Docker 部署。

---

## ✨ 核心功能

### 📡 智能新闻聚合
- 自动从 Telegram 公共财经频道抓取新闻（通过 `t.me/s/频道名` 公开页面）
- 支持多频道并发抓取，每 30 分钟自动更新
- **三层智能去重**：基于消息 ID、内容 Hash 及相似度计算，有效过滤重复资讯
- **历史消息回填**：绑定新频道时可自动抓取最多 1000 条历史消息

### 🏷️ 自动分类标签
- 内置财经词典，自动为每条新闻提取标签（股票、基金、宏观、A股、港股、美股等）
- 支持标签筛选和组合查询

### 🤖 AI 智能总结
- 集成 OpenAI 兼容 API（支持 DeepSeek、GPT 等模型）
- **今日总结**：基于当天全部新闻生成
- **昨日总结**：基于昨天全部新闻生成
- **三天总结**：基于最近三天的每日总结 AI 合成，提炼趋势
- **一周总结**：基于最近七天的每日总结 AI 合成，把握全局
- **搜索总结**：按关键词检索并汇总相关新闻
- **在线配置**：通过 Web 管理面板直接配置 API Key、Base URL、模型名称、总结上下文
- **配置优先级**：数据库设置 > `.env` 文件 > 代码默认值

### 💻 Web 管理面板
- 现代化 UI，支持 PC 和移动端
- **总结中心**（`/summary`）：独立页面展示今日/昨日/三天/一周/搜索总结
- 全文搜索、多标签筛选、日期范围查看
- 统计看板：新闻总数、时段分布、标签热度
- **频道管理**：在线添加/删除/启禁频道，含历史消息回填
- **AI 设置**：在线配置/测试 AI API 连接
- **系统设置**：抓取间隔、密码修改

### ⏰ 定时任务
| 任务 | 执行时间 | 说明 |
|------|----------|------|
| Telegram 抓取 | 每 30 分钟 | 自动检查并抓取新消息 |
| 每日 AI 总结 | 每天 08:00 | 生成当日新闻 AI 总结 |
| 近3天总结 | 每天 08:30 | 基于每日总结合成 |
| 近1周总结 | 每天 09:00 | 基于每日总结合成 |
| 数据清理 | 每天 03:00 | 自动删除过期数据 |

---

## 🚀 快速开始

### 方式一：Docker Compose（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/zhang1200aa-cpu/caijing18.git
cd caijing18

# 2. 创建配置文件
echo "TG_CHANNEL_URLS=https://t.me/s/Financial_Express" > .env

# 3. 启动
docker compose up -d

# 4. 查看日志
docker compose logs -f caijing18
```

访问 http://localhost:5000 即可使用。

### 方式二：原生 Python

```bash
# 1. 安装 Python 3.8+
pip install -r requirements.txt

# 2. 创建 .env 配置文件（参考 .env.example）

# 3. 启动
python main.py
```

---

## 🌐 页面路由

| 路由 | 说明 |
|------|------|
| `/` | 主页 - 新闻管理面板 |
| `/summary` | 总结中心 - AI 总结独立页面 |
| `/summary/today` | 今日总结 |
| `/summary/yesterday` | 昨日总结 |
| `/summary/3d` | 近三天总结 |
| `/summary/1w` | 近一周总结 |
| `/admin` | 管理后台（频道管理、AI 设置、系统配置） |

---

## 📡 API 文档

### 新闻接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/news?page=1&per_page=20` | GET | 分页获取新闻列表 |
| `/api/news/<id>` | GET | 获取新闻详情 |
| `/api/news/search?keyword=美联储` | GET | 按关键词搜索新闻 |
| `/api/tags` | GET | 获取所有可用标签 |
| `/api/stats` | GET | 获取统计数据 |

### AI 总结接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/summary/today` | GET/POST | 获取/刷新今日总结 |
| `/api/summary/yesterday` | GET/POST | 获取/刷新昨日总结 |
| `/api/summary/3d` | GET/POST | 获取/刷新近三天总结 |
| `/api/summary/1w` | GET/POST | 获取/刷新近一周总结 |
| `/api/summary/search` | POST | 生成搜索总结 |
| `/api/summary/all` | GET | 获取所有已缓存总结 |
| `/api/ai/status` | GET | AI 系统状态（配置、连接等） |

### 管理接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/admin/login` | POST | 管理员登录 |
| `/api/admin/logout` | GET | 管理员登出 |
| `/api/admin/check` | GET | 检查登录状态 |
| `/api/admin/channels` | GET | 获取频道列表 |
| `/api/admin/channels/add` | POST | 添加频道（含历史回填） |
| `/api/admin/channels/remove` | POST | 删除频道（同时清理关联新闻） |
| `/api/admin/channels/toggle` | POST | 启用/禁用频道 |
| `/api/admin/settings` | GET | 获取所有设置 |
| `/api/admin/settings/update` | POST | 更新设置 |
| `/api/admin/scrape/trigger` | POST | 手动触发抓取 |
| `/api/admin/cleanup` | POST | 手动清理旧数据 |
| `/api/admin/change-password` | POST | 修改密码 |
| `/api/admin/ai/settings` | POST | 更新 AI 设置 |
| `/api/admin/ai/test` | POST | 测试 AI API 连接 |

---

## 🗂️ 项目结构

```
caijing18/
├── main.py                 # 主程序入口（Flask Web + 定时任务 + 路由注册）
├── config.py               # 公共配置（去重阈值、数据保留天数等）
├── database.py             # 数据库模型和操作（SQLite + SQLAlchemy）
├── ai_summary.py           # AI 总结生成（OpenAI 兼容 API）
├── tg_scraper.py           # Telegram 公共频道网页抓取
├── tagger.py               # 自动财经标签分类
├── deduplicator.py         # 三层智能去重
├── logging_setup.py        # 日志配置
├── requirements.txt        # Python 依赖
├── Dockerfile              # Docker 镜像构建
├── docker-compose.yml      # Docker Compose 编排
├── .env.example            # 环境变量示例
├── routes/
│   ├── __init__.py
│   ├── web_routes.py       # Web 页面路由
│   ├── news_api.py         # 新闻查询 API 路由
│   ├── admin_api.py        # 管理后台 API 路由
│   └── ai_api.py           # AI 总结 API 路由
├── services/
│   ├── __init__.py
│   ├── news_service.py     # 新闻查询服务
│   ├── summary_service.py  # AI 总结生成服务
│   └── admin_service.py    # 管理后台服务
├── web/
│   ├── static/
│   │   ├── css/
│   │   │   ├── style.css   # 主页样式
│   │   │   └── admin.css   # 管理后台样式
│   │   └── js/
│   │       ├── app.js      # 主页前端逻辑
│   │       └── admin.js    # 管理后台前端逻辑
│   └── templates/
│       ├── index.html      # 主页模板
│       ├── summary.html    # 总结中心模板
│       └── admin.html      # 管理后台模板
└── data/                   # 数据目录（SQLite 数据库自动创建）
```

---

## ⚙️ 配置说明

### 环境变量（.env）

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `TG_CHANNEL_URLS` | 是 | `https://t.me/s/XXXXX` | 抓取的公共频道 URL，多个用逗号分隔 |
| `AI_API_KEY` | 否 | 空 | OpenAI 兼容 API Key（建议通过管理面板配置） |
| `AI_BASE_URL` | 否 | `https://api.xxxx.com/v1` | API 基础地址（建议通过管理面板配置） |
| `AI_MODEL` | 否 | `deepseek-v4-flash` | AI 模型名称（建议通过管理面板配置） |
| `DATABASE_PATH` | 否 | `data/finance_data.db` | SQLite 数据库路径 |
| `FLASK_HOST` | 否 | `0.0.0.0` | Web 服务监听地址 |
| `FLASK_PORT` | 否 | `5000` | Web 服务端口 |

### 核心参数（config.py）

| 参数 | 默认值 | 说明 |
|------|--------|--------|
| `SIMILARITY_THRESHOLD` | `0.75` | 去重相似度阈值（越高去重越严格） |
| `DATA_RETENTION_DAYS` | `7` | 数据保留天数 |
| `MIN_CONTENT_LENGTH` | `20` | 最小内容长度（过滤过短消息） |

---

## 🐳 Docker 部署

```bash
# 构建并启动
docker compose up -d

# 查看实时日志
docker compose logs -f caijing18

# 停止服务
docker compose down

# 重启服务
docker compose restart
```

### 原生 Docker

```bash
# 构建镜像
docker build -t caijing18:latest .

# 运行容器
docker run -d \
  -p 5000:5000 \
  -e TG_CHANNEL_URLS=https://t.me/s/xxxxx \
  -v $(pwd)/data:/app/data \
  --name caijing18 \
  caijing18:latest
```

---

## 🔧 使用指南

### 首次启动
1. 访问 `http://localhost:5000`
2. 进入管理后台 `/admin`
3. 登录（默认用户名 `admin`，密码 `admin`）
4. 添加 Telegram 频道（如 `https://t.me/s/xxxxx`）
5. 等待自动抓取或在概览页面点击"手动抓取"
6. 可选：在 AI 设置中配置 API Key 启用 AI 总结功能

### 频道管理
- **添加频道**：输入 Telegram 公开频道 URL，设置历史回填条数（默认 1000 条）
- **删除频道**：会同时删除该频道关联的所有新闻数据
- **启用/禁用**：禁用后该频道不会被自动抓取

### AI 总结
1. 在管理后台 → AI 设置中配置 API Key、Base URL 和模型
2. 配置完成后可进入总结中心 `/summary` 查看各时间范围的总结
3. 支持手动刷新和自动定时生成

---

## 👤 管理后台

默认管理员账号：
- **用户名**: `admin`
- **密  码**: `admin`

> ⚠️ 首次登录后请立即修改密码。

---

## 🔒 安全说明

- 敏感配置（API Key、密码等）存储在 `.env` 文件或数据库中，均不纳入版本控制
- 管理后台密码建议在首次使用时修改
- AI API Key 可通过管理后台在线配置，无需编辑环境变量

---

## 📜 许可证

本项目基于 MIT License 开源。
