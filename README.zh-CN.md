# 🚀 caijing18 — Telegram 财经新闻智能聚合平台

<p align="center">
  <img src="https://img.shields.io/badge/python-3.8+-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/flask-3.0+-black?style=for-the-badge&logo=flask&logoColor=white" alt="Flask">
  <img src="https://img.shields.io/badge/sqlite3-✅-brightgreen?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite">
  <img src="https://img.shields.io/badge/docker-✅-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/license-MIT-yellow?style=for-the-badge" alt="License">
  <img src="https://img.shields.io/badge/PRs-welcome-orange?style=for-the-badge" alt="PRs Welcome">
</p>

<p align="center">
  <b>基于 Telegram 公开频道网页抓取的自动化财经新闻聚合与管理平台</b><br>
  支持 <b>AI 智能总结</b>、<b>当日财经分析互动问答</b>、多维度搜索筛选、定时任务维护，开箱即用的 Docker 部署。
</p>

<p align="center">
  <a href="README.md"><img src="https://img.shields.io/badge/🌍-多语言-darkblue?style=for-the-badge" alt="多语言"></a>
  <a href="README.en.md"><img src="https://img.shields.io/badge/🇬🇧-English-blue?style=for-the-badge" alt="English"></a>
  <a href="README.ja.md"><img src="https://img.shields.io/badge/🇯🇵-日本語-blue?style=for-the-badge" alt="日本語"></a>
</p>

---

## 📋 目录

- [✨ 核心功能](#-核心功能)
- [🚀 快速开始](#-快速开始)
- [🐳 Docker 部署](#-docker-部署)
- [🌐 页面路由](#-页面路由)
- [📡 API 文档](#-api-文档)
- [🗂️ 项目结构](#️-项目结构)
- [⚙️ 配置说明](#️-配置说明)
- [🔧 使用指南](#-使用指南)
- [👤 管理后台](#-管理后台)
- [🔒 安全说明](#-安全说明)
- [📜 许可证](#-许可证)

---

## ✨ 核心功能

### 📡 智能新闻聚合
- 自动从 Telegram 公共财经频道抓取新闻（通过 `t.me/s/频道名` 公开页面）
- 支持多频道并发抓取，可配置抓取间隔（默认 30 分钟）
- **三层智能去重**：基于消息 ID、内容 Hash 及相似度计算，有效过滤重复资讯
- **历史消息回填**：绑定新频道时可自动抓取指定条数历史消息（异步后台执行，实时进度追踪）
- **频道重新回填**：已绑定的频道可重新触发历史消息回填

### 🏷️ 自动分类标签
- 内置财经词典，自动为每条新闻提取标签（股票、基金、宏观、A 股、港股、美股等）
- 支持标签筛选和组合查询
- **标签词典可自定义**：通过修改 `config.py` 中的 `FINANCE_KEYWORDS` 字典，可增删分类和关键词

### 🤖 AI 智能总结 & 互动分析
- 集成 OpenAI 兼容 API（支持 DeepSeek、GPT、通义千问等模型）
- **今日总结** & **昨日总结**：基于当天/昨日全部新闻生成
- **三天总结** & **一周总结**：基于每日总结合成，提炼持续趋势
- **搜索总结**：按关键词检索并汇总相关新闻
- **当日财经分析（QA 互动问答）**：基于可配置时间范围（默认 24 小时）的新闻，回答用户提出的财经问题，支持灵活的时间范围设置（1 小时 ~ 30 天）
- **定时调度可配置**：每种总结的生成时间和启用状态均可通过管理后台在线配置
- **AI 提示词自定义**：每日总结、复合总结（三日/一周）、当日财经分析的提示词均可在线编辑，支持恢复默认
- **自定义上下文**：可配置 AI 总结的长期上下文，辅助 AI 结合特定背景进行分析
- **在线配置**：通过 Web 管理面板直接配置 API Key、Base URL、模型名称
- **配置优先级**：数据库设置 > `.env` 文件 > 代码默认值

### 💻 Web 管理面板
- 现代化响应式 UI，完美适配 PC 和移动端
- **总结中心**（`/summary`）：独立页面展示各类 AI 总结，支持查看历史总结
- 全文搜索、多标签筛选、日期范围查看
- 统计看板：新闻总数、时段分布、标签热度
- **频道管理**：在线添加/删除/启禁频道，含历史消息回填异步进度追踪
- **AI 设置**：在线配置/测试 AI API 连接，自定义提示词和上下文
- **系统设置**：抓取间隔、密码修改、网站名称、公告
- **首次启动引导**：自动检测首次运行，提示用户添加 Telegram 频道

### 📨 Telegram 订阅通知
- 支持通过 Telegram Bot 推送抓取完成通知
- 通过 `.env` 配置 `TELEGRAM_BOT_TOKEN` 和 `TG_NOTIFY_CHAT_ID` 即可启用

### ⏰ 定时任务

| 任务 | 默认执行时间 | 说明 |
|------|-------------|------|
| 🔄 Telegram 抓取 | 每 30 分钟 | 自动检查并抓取新消息（间隔可配置） |
| 🧠 每日 AI 总结 | 每天 20:00 | 生成当日新闻 AI 总结 |
| 📊 近 3 天总结 | 每天 20:30 | 基于每日总结合成 |
| 📈 近 1 周总结 | 每周五 21:00 | 基于每日总结合成 |
| 🧹 数据清理 | 每天 03:00 | 自动删除 7 天前的过期数据 |
| 📋 数据统计 | 每小时 | 更新新闻统计信息 |

> 所有总结任务的执行时间和启用状态均可通过管理后台在线修改。

---

## 🚀 快速开始

### 方式一：Docker Compose（⭐ 推荐）

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

访问 [http://localhost:5000](http://localhost:5000) 即可使用。

### 方式二：原生 Python

```bash
# 1. 安装 Python 3.8+
pip install -r requirements.txt

# 2. 创建 .env 配置文件（参考 .env.example）

# 3. 启动
python main.py
```

> 📌 **提示**：初次使用时，系统会自动检测首次启动状态并引导添加频道。默认管理员账号为 `admin` / `admin`，请及时修改密码。

---

## 🐳 Docker 部署

### Docker Compose（推荐）

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

## 🌐 页面路由

| 路由 | 说明 |
|------|------|
| `/` | 🏠 **主页** — 新闻管理面板 |
| `/summary` | 📝 **总结中心** — AI 总结独立页面 |
| `/summary/today` | 📅 今日总结 |
| `/summary/yesterday` | 📅 昨日总结 |
| `/summary/3d` | 📆 近三天总结 |
| `/summary/1w` | 📆 近一周总结 |
| `/summary/search?q=关键词` | 🔍 搜索总结 |
| `/summary/date/2026-01-01` | 📚 历史总结查看 |
| `/admin` | ⚙️ **管理后台** — 频道管理、AI 设置、系统配置 |

---

## 📡 API 文档

### 新闻接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/news?page=1&per_page=20` | `GET` | 分页获取新闻列表 |
| `/api/news/<id>` | `GET` | 获取新闻详情 |
| `/api/news/search?keyword=美联储` | `GET` | 按关键词搜索新闻 |
| `/api/tags` | `GET` | 获取所有可用标签 |
| `/api/stats` | `GET` | 获取统计数据 |

### AI 总结接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/summary/today` | `GET/POST` | 获取/刷新今日总结 |
| `/api/summary/yesterday` | `GET/POST` | 获取/刷新昨日总结 |
| `/api/summary/3d` | `GET/POST` | 获取/刷新近三天总结 |
| `/api/summary/1w` | `GET/POST` | 获取/刷新近一周总结 |
| `/api/summary/search` | `POST` | 生成搜索总结 |
| `/api/summary/all` | `GET` | 获取所有已缓存总结 |
| `/api/summary/date/<date>` | `GET` | 按日期获取历史总结（支持 YYYY-MM-DD 或 YYYYMMDD） |
| `/api/summary/list?start=2026-01-01&end=2026-01-31` | `GET` | 获取日期范围内的历史总结列表 |
| `/api/ai/status` | `GET` | AI 系统状态（配置、连接等） |
| _**新增：当日财经分析（QA）**_ | | |
| `/api/ai/today-qa` | `POST` | 提交问题，基于可配置时间范围的新闻进行财经分析回答 |

### 管理接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/admin/login` | `POST` | 管理员登录 |
| `/api/admin/logout` | `GET` | 管理员登出 |
| `/api/admin/check` | `GET` | 检查登录状态 |
| `/api/admin/channels` | `GET` | 获取频道列表 |
| `/api/admin/channels/add` | `POST` | 添加频道（指定条数异步历史回填，支持进度追踪） |
| `/api/admin/channels/remove` | `POST` | 删除频道（同时清理关联新闻） |
| `/api/admin/channels/toggle` | `POST` | 启用/禁用频道 |
| `/api/admin/channels/re-scrape` | `POST` | 重新触发频道历史消息回填 |
| `/api/admin/check-channels` | `GET` | 检查系统是否有可用频道（首次启动检测） |
| `/api/admin/settings` | `GET` | 获取所有设置 |
| `/api/admin/settings/update` | `POST` | 更新设置 |
| `/api/admin/settings/interval` | `POST` | 更新抓取间隔 |
| `/api/admin/scrape/trigger` | `POST` | 手动触发抓取 |
| `/api/admin/cleanup` | `POST` | 手动清理旧数据 |
| `/api/admin/change-password` | `POST` | 修改密码 |
| `/api/admin/ai/settings` | `POST` | 更新 AI 设置 |
| `/api/admin/ai/test` | `POST` | 测试 AI API 连接 |
| `/api/admin/site-name` | `GET/POST` | 获取/更新网站名称 |
| `/api/admin/site-notice` | `GET/POST` | 获取/更新公告内容 |
| `/api/admin/summary-prompts` | `GET/POST` | 获取/更新 AI 总结提示词（含每日、复合、当日分析三类） |
| `/api/admin/summary-prompts/todayqa` | `POST` | 单独更新当日财经分析提示词 |
| `/api/admin/summary-prompts/reset` | `POST` | 重置指定提示词为默认值 |
| `/api/admin/summary-schedule` | `GET/POST` | 获取/更新总结定时配置（时间、启用状态） |

---

## 🗂️ 项目结构

```
caijing18/
├── main.py                    # 🚀 主程序入口（Flask Web + 定时任务 + 路由注册）
├── config.py                  # ⚙️ 公共配置（去重阈值、数据保留天数、标签词典等）
├── database.py                # 🗄️ 数据库模型和操作（SQLite + SQLAlchemy）
├── tg_scraper.py              # 📡 Telegram 公共频道网页抓取（增量 + 历史回填）
├── tagger.py                  # 🏷️ 自动财经标签分类（基于关键词词典）
├── deduplicator.py            # 🔍 三层智能去重（ID、Hash、相似度）
├── logging_setup.py           # 📋 日志配置（兼容 Windows GBK）
├── telegram_bot.py            # 🤖 Telegram Bot 推送通知
├── requirements.txt           # 📦 Python 依赖
├── Dockerfile                 # 🐳 Docker 镜像构建
├── docker-compose.yml         # 🐳 Docker Compose 编排
├── .env.example               # 🔑 环境变量示例
│
├── routes/                    # 🛣️ 路由层
│   ├── __init__.py
│   ├── web_routes.py          #   Web 页面路由（首页、管理后台、总结中心）
│   ├── news_api.py            #   新闻查询 API 路由
│   ├── admin_api.py           #   管理后台 API 路由
│   └── ai_api.py              #   AI 总结 & 当日财经分析 API 路由
│
├── services/                  # 💼 业务服务层
│   ├── __init__.py
│   ├── news_service.py        #   新闻查询服务
│   ├── summary_service.py     #   AI 总结生成服务（含所有总结类型 + QA 互动）
│   └── admin_service.py       #   管理后台服务（频道同步、调度管理）
│
├── web/                       # 🎨 前端资源
│   ├── static/
│   │   ├── css/               #   样式文件
│   │   │   ├── style.css
│   │   │   └── admin.css
│   │   └── js/                #   前端逻辑
│   │       ├── app.js
│   │       └── admin.js
│   └── templates/             #   页面模板
│       ├── index.html
│       ├── summary.html
│       └── admin.html
│
└── data/                      # 📂 数据目录（SQLite 数据库自动创建于此）
    └── tg_seen_messages.json  #   已处理消息 ID 缓存（翻页去重）
```

---

## ⚙️ 配置说明

### 环境变量（.env）

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `TG_CHANNEL_URLS` | ✅ 是 | `https://t.me/s/XXXXX` | 抓取的公共频道 URL，多个用逗号分隔 |
| `AI_API_KEY` | ❌ 否 | — | OpenAI 兼容 API Key（建议通过管理面板配置） |
| `AI_BASE_URL` | ❌ 否 | `https://api.xxxx.com/v1` | API 基础地址（建议通过管理面板配置） |
| `AI_MODEL` | ❌ 否 | `deepseek-v4-flash` | AI 模型名称（建议通过管理面板配置） |
| `DATABASE_PATH` | ❌ 否 | `data/finance_data.db` | SQLite 数据库路径 |
| `FLASK_HOST` | ❌ 否 | `0.0.0.0` | Web 服务监听地址 |
| `FLASK_PORT` | ❌ 否 | `5000` | Web 服务端口 |
| `FLASK_DEBUG` | ❌ 否 | `false` | Flask 调试模式 |
| `TELEGRAM_BOT_TOKEN` | ❌ 否 | — | Telegram Bot Token（用于抓取结果推送通知） |
| `TG_NOTIFY_CHAT_ID` | ❌ 否 | — | 接收推送通知的 Telegram 会话 ID |
| `TG_NOTIFY_ENABLED` | ❌ 否 | `false` | 是否启用 TG 推送通知 |

### 核心参数（config.py）

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `SIMILARITY_THRESHOLD` | `0.75` | 去重相似度阈值（越高去重越严格） |
| `DATA_RETENTION_DAYS` | `7` | 数据保留天数 |
| `MIN_CONTENT_LENGTH` | `20` | 最小内容长度（过滤过短消息） |
| `AI_TIMEOUT` | `120` | AI API 请求超时时间（秒） |

### 标签字典自定义

标签系统通过 `config.py` 文件中的 `FINANCE_KEYWORDS` 字典实现，你可以直接修改该字典来增删标签分类和关键词。

**字典结构：**

```python
FINANCE_KEYWORDS = {
    '分类名1': ['关键词1', '关键词2', ...],
    '分类名2': ['关键词3', '关键词4', ...],
}
```

**示例：增加"新能源"分类**

```python
FINANCE_KEYWORDS = {
    # 原有分类...
    '新能源': ['锂电池', '光伏', '风电', '新能源汽车', '储能', '宁德时代'],
}
```

**修改步骤：**
1. 打开 `config.py` 文件
2. 找到 `FINANCE_KEYWORDS` 字典（约第 56 行）
3. 添加、修改或删除分类和关键词
4. 保存文件并重启服务

> ⚠️ 修改后需重启服务才能生效；关键词匹配**不区分大小写**。

---

## 🔧 使用指南

### 首次启动
1. 访问 [http://localhost:5000](http://localhost:5000)
2. 系统自动检测首次启动状态，引导进入管理后台
3. 进入管理后台 `/admin`
4. 登录（默认用户名 `admin`，密码 `admin`）
5. 添加 Telegram 频道（如 `https://t.me/s/xxxxx`），设置历史回填条数
6. 系统自动在后台异步回填历史消息，频道列表中可查看回填进度
7. 等待自动抓取或在概览页面点击 **"手动抓取"**
8. 可选：在 AI 设置中配置 API Key、Base URL、模型等，启用 AI 总结功能

### 频道管理
- **添加频道**：输入 Telegram 公开频道 URL，设置历史回填条数（默认 1000 条，异步执行）
- **重新回填**：已绑定的频道支持重新触发历史回填
- **删除频道**：会同时删除该频道关联的所有新闻数据
- **启用/禁用**：禁用后该频道不会被自动抓取

### AI 总结
1. 在管理后台 → AI 设置中配置 API Key、Base URL 和模型
2. 可自定义每日总结/复合总结/当日财经分析的提示词
3. 可配置 AI 总结的长期上下文（帮助 AI 理解特定背景）
4. 在调度设置中配置各类总结的生成时间和启用状态
5. 配置完成后进入总结中心 `/summary` 查看各时间范围的总结
6. 支持手动刷新和自动定时生成

### 当日财经分析（QA 互动）
1. 在管理后台配置 AI API 信息
2. 可设置分析时间范围（默认 24 小时，支持 1 小时 ~ 30 天）
3. 在总结中心 `/summary` 的"当日财经分析"标签页输入问题
4. AI 基于所选时间范围内的新闻自动回答

---

## 👤 管理后台

| 项目 | 默认值 |
|------|--------|
| **用户名** | `admin` |
| **密  码** | `admin` |

> ⚠️ **安全提醒**：首次登录后请立即修改密码！

### 🔑 忘记密码怎么办？

如果忘记了管理员密码，无需担心，使用项目自带的密码重置脚本即可一键重置：

```bash
# 交互模式（推荐）— 会提示输入并确认新密码
python reset_admin.py

# 直接指定新密码（非交互）
python reset_admin.py --password 新密码

# 重置其他管理员用户
python reset_admin.py --username 用户名 --password 新密码

# 查看所有管理员
python reset_admin.py --list
```

该脚本直接操作 SQLite 数据库，不依赖 Flask 应用运行状态，即使服务挂了也能正常使用。
密码使用与系统相同的哈希算法存储（优先 bcrypt，备选 SHA256）。

#### 🐳 Docker 环境重置密码

如果使用 Docker 部署忘记密码，**推荐方式一**（最简单）：

```bash
# 方式一（推荐）：在宿主机项目根目录直接运行
# 因为数据库挂载在宿主机 ./data/ 目录，脚本可以直接访问
python reset_admin.py

# 方式二：进入容器内部运行
docker compose exec app python reset_admin.py
# 或者直接指定新密码
docker compose exec app python reset_admin.py --password 你的新密码
```

---

## 🔒 安全说明

- 敏感配置（API Key、密码等）存储在 `.env` 文件或数据库中，**均不纳入版本控制**
- 管理后台密码建议在首次使用时修改
- AI API Key 可通过管理后台在线配置，无需编辑环境变量
- Flask session 密钥在首次启动时自动生成并持久化到数据库

---

## 📜 许可证

本项目基于 **MIT License** 开源，欢迎自由使用和贡献。

---

<p align="center">
  Made with ❤️ for the Open Source Community
</p>

<p align="center">
  <a href="https://paypal.me/zhang1200aa"><img src="https://img.shields.io/badge/赞助-PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white" alt="赞助"></a>
</p>