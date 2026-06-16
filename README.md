# 🚀 caijing18 财经新闻聚合平台

基于 Telegram 频道抓取的自动化财经新闻聚合与管理平台，支持 **AI 智能总结**、多维度搜索筛选、定时任务维护，开箱即用的 Docker 部署。

---

## ✨ 核心功能

### 📡 智能新闻聚合
- 自动从 Telegram 公共财经频道（`t.me/s/Financial_Express` 等）抓取新闻
- 支持多频道并发抓取，每 30 分钟自动更新
- **三层智能去重**：基于消息 ID、内容 Hash 及相似度计算，有效过滤重复资讯

### 🏷️ 自动分类标签
- 内置财经词典，自动为每条新闻提取标签（股票、基金、宏观、A股、港股、美股等）
- 支持标签筛选和组合查询

### 🤖 AI 智能总结
- 集成 OpenAI 兼容 API（支持 DeepSeek、GPT 等模型）
- **每日总结（1d）**：基于当天全部原始新闻生成，不限条数，AI 自动按分类组织
- **近三天综合总结（3d）**：基于三天每日总结 AI 合成，提炼趋势
- **近一周综合总结（7d）**：基于七天每日总结 AI 合成，把握全局
- 支持任意历史日期的总结生成（`/summary/20260616`）

### 💻 Web 管理面板
- 现代化 UI，支持 PC 和移动端
- 全文搜索、多标签筛选、日期范围查看
- AI 总结独立页面，支持日期/范围切换
- 统计看板：新闻总数、时段分布、标签热度

### ⏰ 定时任务
| 任务 | 执行时间 | 说明 |
|------|----------|------|
| Telegram 抓取 | 每 30 分钟 | 自动检查并抓取新消息 |
| 每日 AI 总结 | 每天 08:00 | 生成当日新闻 AI 总结 |
| 近3天总结 | 每天 08:30 | 基于每日总结合成 |
| 近1周总结 | 每天 09:00 | 基于每日总结合成 |
| 数据清理 | 每天 03:00 | 自动删除 7 天前过期数据 |
| 统计更新 | 每小时 | 刷新统计信息 |

---

## � 快速开始

### 方式一：Docker Compose（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/zhang1200aa-cpu/caijing18.git
cd caijing18

# 2. 创建配置文件
echo "TELEGRAM_BOT_TOKEN=your_bot_token_here" > .env

# 3. 启动
docker-compose up -d

# 4. 查看日志
docker-compose logs -f caijing18
```

访问 http://localhost:5000 即可使用。

### 方式二：原生 Python

```bash
# 1. 安装 Python 3.8+
pip install -r requirements.txt

# 2. 创建 .env 配置文件（参考 .env.example）
#    配置 AI API Key、Telegram 频道等

# 3. 启动
python main.py
```

---

## 🌐 Web 页面路由

| 路由 | 说明 |
|------|------|
| `/` | 主页 - 新闻管理面板 |
| `/summary` | 当日 AI 总结（默认 1 天） |
| `/summary/1` | 当日 1 天总结 |
| `/summary/3` | 当日近 3 天总结 |
| `/summary/7` | 当日近 1 周总结 |
| `/summary/20260616` | 指定日期（2026-06-16）1 天总结 |
| `/summary/20260616/1` | 指定日期 1 天总结 |
| `/summary/20260616/3` | 指定日期近 3 天总结 |
| `/summary/20260616/7` | 指定日期近 1 周总结 |

---

## 📡 API 文档

### 新闻接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/news?page=1&per_page=20` | GET | 分页获取新闻列表 |
| `/api/search?keyword=美联储` | GET | 按关键词搜索新闻 |
| `/api/news/by-tag?tag=股票` | GET | 按标签筛选新闻 |
| `/api/filter?tags=股票,基金&start_date=...&end_date=...` | GET | 多条件组合筛选 |
| `/api/tags` | GET | 获取所有可用标签 |

### AI 总结接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/summary?range=1d&date=2026-06-16` | GET | 获取已缓存的 AI 总结 |
| `/api/summary` | POST | 手动触发生成 AI 总结 |
| `POST Body: {"range": "1d", "date": "2026-06-16"}` | | `range`: `1d`/`3d`/`1w` |

### 系统接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/stats` | GET | 获取统计信息 |
| `/api/cleanup` | POST | 手动触发数据清理 |
| `/api/health` | GET | 健康检查 |

---

## 🗂️ 项目结构

```
caijing18/
├── main.py                 # 主程序入口（Flask Web + 定时任务 + 路由）
├── config.py               # 公共配置（去重阈值、数据保留天数等）
├── database.py             # 数据库模型和操作（SQLite + SQLAlchemy）
├── ai_summary.py           # AI 总结生成（OpenAI 兼容 API）
├── tg_scraper.py           # Telegram 公共频道网页抓取
├── telegram_bot.py         # Telegram Bot 模式支持
├── tagger.py               # 自动财经标签分类
├── deduplicator.py         # 三层智能去重
├── requirements.txt        # Python 依赖
├── Dockerfile              # Docker 镜像构建
├── docker-compose.yml      # Docker Compose 编排
├── .env                    # 环境变量（敏感配置）
├── .gitignore
├── README.md
└── web/
    └── templates/
        ├── index.html      # 主页模板
        ├── summary.html    # AI 总结页面模板
        └── admin.html      # 管理页面模板
```

---

## ⚙️ 配置说明

### 环境变量（.env）

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `TELEGRAM_BOT_TOKEN` | 否 | 空 | Telegram Bot Token（Bot 模式） |
| `TG_CHANNEL_URLS` | 是 | `https://t.me/s/Financial_Express` | 抓取的公共频道 URL，多个用逗号分隔 |
| `AI_API_KEY` | 否 | `sk-123` | OpenAI 兼容 API Key，不配置则不生成 AI 总结 |
| `AI_BASE_URL` | 否 | `https://api.baipiao.eu.org/v1` | API 基础地址 |
| `AI_MODEL` | 否 | `deepseek-v4-flash-free` | AI 模型名称 |
| `DATABASE_PATH` | 否 | `data/finance_data.db` | SQLite 数据库路径 |
| `FLASK_HOST` | 否 | `0.0.0.0` | Web 服务监听地址 |
| `FLASK_PORT` | 否 | `5000` | Web 服务端口 |

### 核心参数（config.py）

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `SIMILARITY_THRESHOLD` | `0.75` | 去重相似度阈值（越高去重越严格） |
| `DATA_RETENTION_DAYS` | `7` | 数据保留天数 |
| `MIN_CONTENT_LENGTH` | `20` | 最小内容长度（过滤过短消息） |

---

## 🐳 Docker 部署

### Docker Compose

```bash
# 构建并启动
docker-compose up -d

# 查看实时日志
docker-compose logs -f caijing18

# 停止服务
docker-compose down

# 重启服务
docker-compose restart
```

### 原生 Docker

```bash
# 构建镜像
docker build -t caijing18:latest .

# 运行容器
docker run -d \
  -p 5000:5000 \
  -e TELEGRAM_BOT_TOKEN=your_token \
  -e AI_API_KEY=your_api_key \
  -v $(pwd)/data:/app/data \
  --name caijing18 \
  caijing18:latest
```

---

## � 管理后台

默认管理员账号：
- **用户名**: `admin`
- **密  码**: `admin`

> ⚠️ 首次登录后请立即修改密码。生产环境部署建议通过环境变量设置自定义密码。

---

## �🔧 开发说明

### 添加新频道

编辑 `.env` 文件中的 `TG_CHANNEL_URLS`，多个频道用逗号分隔：
```env
TG_CHANNEL_URLS=https://t.me/s/Financial_Express,https://t.me/s/CaiJing
```

### 更换 AI 模型

支持任意 OpenAI 兼容 API，修改 `.env`：
```env
AI_BASE_URL=https://api.openai.com/v1
AI_MODEL=gpt-3.5-turbo
AI_API_KEY=sk-your_key_here
```

---

## 🔒 安全说明

- 敏感配置（API Key、Token 等）存储在 `.env` 文件中，已加入 `.gitignore`

---

## 📜 许可证

本项目基于 MIT License 开源。