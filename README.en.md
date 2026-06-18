# 🚀 caijing18 — Telegram Financial News Intelligent Aggregation Platform

<p align="center">
  <img src="https://img.shields.io/badge/python-3.8+-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/flask-3.0+-black?style=for-the-badge&logo=flask&logoColor=white" alt="Flask">
  <img src="https://img.shields.io/badge/sqlite3-✅-brightgreen?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite">
  <img src="https://img.shields.io/badge/docker-✅-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/license-MIT-yellow?style=for-the-badge" alt="License">
  <img src="https://img.shields.io/badge/PRs-welcome-orange?style=for-the-badge" alt="PRs Welcome">
</p>

<p align="center">
  <b>An automated financial news aggregation and management platform based on Telegram public channel web scraping</b><br>
  Supports <b>AI-powered summaries</b>, multi-dimensional search and filtering, scheduled task maintenance, and out-of-the-box Docker deployment.
</p>

<p align="center">
  <a href="README.md"><img src="https://img.shields.io/badge/🌍-Multi-language-darkblue?style=for-the-badge" alt="Multi-language"></a>
  <a href="README.zh-CN.md"><img src="https://img.shields.io/badge/🇨🇳-中文-blue?style=for-the-badge" alt="中文"></a>
  <a href="README.ja.md"><img src="https://img.shields.io/badge/🇯🇵-日本語-blue?style=for-the-badge" alt="日本語"></a>
</p>

---

## 📋 Table of Contents

- [✨ Core Features](#-core-features)
- [🚀 Quick Start](#-quick-start)
- [🐳 Docker Deployment](#-docker-deployment)
- [🌐 Page Routes](#-page-routes)
- [📡 API Documentation](#-api-documentation)
- [🗂️ Project Structure](#️-project-structure)
- [⚙️ Configuration](#️-configuration)
- [🔧 Usage Guide](#-usage-guide)
- [👤 Admin Panel](#-admin-panel)
- [🔒 Security Notes](#-security-notes)
- [📜 License](#-license)

---

## ✨ Core Features

### 📡 Intelligent News Aggregation
- Automatically scrapes news from Telegram public financial channels (via `t.me/s/channel_name` public pages)
- Supports multi-channel concurrent scraping, auto-updates every 30 minutes
- **Three-layer intelligent deduplication**: based on message ID, content hash, and similarity calculation to effectively filter duplicate content
- **Historical message backfill**: automatically fetches up to 1000 historical messages when binding new channels

### 🏷️ Automatic Tag Classification
- Built-in financial dictionary that automatically extracts tags for each news item (stocks, funds, macroeconomics, A-shares, Hong Kong stocks, US stocks, etc.)
- Supports tag filtering and combined queries
- **Customizable tag dictionary**: modify the `FINANCE_KEYWORDS` dictionary in `config.py` to add, remove, or edit categories and keywords

### 🤖 AI-Powered Summaries
- Integrates OpenAI-compatible APIs (supports DeepSeek, GPT, and other models)
- **Today's Summary** & **Yesterday's Summary**: generated from all news of the current/previous day
- **3-Day Summary** & **Weekly Summary**: synthesized from daily summaries to extract trends
- **Search Summary**: retrieves and summarizes relevant news by keyword
- **Online configuration**: directly configure API Key, Base URL, model name, and summary context through the web admin panel
- **Configuration priority**: Database settings > `.env` file > Code defaults

### 💻 Web Admin Panel
- Modern responsive UI, perfectly adapted for PC and mobile
- **Summary Center** (`/summary`): dedicated page displaying all AI summaries
- Full-text search, multi-tag filtering, date range viewing
- Statistics dashboard: total news count, time distribution, tag popularity
- **Channel management**: add/delete/enable/disable channels online, with historical message backfill
- **AI settings**: configure and test AI API connections online
- **System settings**: scrape interval, password modification

### ⏰ Scheduled Tasks

| Task | Execution Time | Description |
|------|---------------|-------------|
| 🔄 Telegram Scraping | Every 30 min | Automatically check and fetch new messages |
| 🧠 Daily AI Summary | Daily 08:00 | Generate AI summary for the day's news |
| 📊 3-Day Summary | Daily 08:30 | Synthesized from daily summaries |
| 📈 Weekly Summary | Daily 09:00 | Synthesized from daily summaries |
| 🧹 Data Cleanup | Daily 03:00 | Automatically delete expired data |

---

## 🚀 Quick Start

### Method 1: Docker Compose (⭐ Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/zhang1200aa-cpu/caijing18.git
cd caijing18

# 2. Create configuration file
echo "TG_CHANNEL_URLS=https://t.me/s/Financial_Express" > .env

# 3. Start
docker compose up -d

# 4. View logs
docker compose logs -f caijing18
```

Visit [http://localhost:5000](http://localhost:5000) to start using.

### Method 2: Native Python

```bash
# 1. Install Python 3.8+
pip install -r requirements.txt

# 2. Create .env configuration file (refer to .env.example)

# 3. Start
python main.py
```

> 📌 **Tip**: On first use, the default admin credentials are `admin` / `admin`. Please change your password immediately.

---

## 🐳 Docker Deployment

### Docker Compose (Recommended)

```bash
# Build and start
docker compose up -d

# View real-time logs
docker compose logs -f caijing18

# Stop services
docker compose down

# Restart services
docker compose restart
```

### Native Docker

```bash
# Build image
docker build -t caijing18:latest .

# Run container
docker run -d \
  -p 5000:5000 \
  -e TG_CHANNEL_URLS=https://t.me/s/xxxxx \
  -v $(pwd)/data:/app/data \
  --name caijing18 \
  caijing18:latest
```

---

## 🌐 Page Routes

| Route | Description |
|-------|-------------|
| `/` | 🏠 **Home** — News management panel |
| `/summary` | 📝 **Summary Center** — AI summary dedicated page |
| `/summary/today` | 📅 Today's summary |
| `/summary/yesterday` | 📅 Yesterday's summary |
| `/summary/3d` | 📆 3-day summary |
| `/summary/1w` | 📆 Weekly summary |
| `/admin` | ⚙️ **Admin Panel** — Channel management, AI settings, system configuration |

---

## 📡 API Documentation

### News Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/news?page=1&per_page=20` | `GET` | Paginated news list |
| `/api/news/<id>` | `GET` | News detail |
| `/api/news/search?keyword=Fed` | `GET` | Search news by keyword |
| `/api/tags` | `GET` | Get all available tags |
| `/api/stats` | `GET` | Get statistics |

### AI Summary Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/summary/today` | `GET/POST` | Get/refresh today's summary |
| `/api/summary/yesterday` | `GET/POST` | Get/refresh yesterday's summary |
| `/api/summary/3d` | `GET/POST` | Get/refresh 3-day summary |
| `/api/summary/1w` | `GET/POST` | Get/refresh weekly summary |
| `/api/summary/search` | `POST` | Generate search summary |
| `/api/summary/all` | `GET` | Get all cached summaries |
| `/api/ai/status` | `GET` | AI system status (configuration, connection, etc.) |

### Admin Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/admin/login` | `POST` | Admin login |
| `/api/admin/logout` | `GET` | Admin logout |
| `/api/admin/check` | `GET` | Check login status |
| `/api/admin/channels` | `GET` | Get channel list |
| `/api/admin/channels/add` | `POST` | Add channel (with historical backfill) |
| `/api/admin/channels/remove` | `POST` | Delete channel (also cleans up associated news) |
| `/api/admin/channels/toggle` | `POST` | Enable/disable channel |
| `/api/admin/settings` | `GET` | Get all settings |
| `/api/admin/settings/update` | `POST` | Update settings |
| `/api/admin/scrape/trigger` | `POST` | Manually trigger scraping |
| `/api/admin/cleanup` | `POST` | Manually clean up old data |
| `/api/admin/change-password` | `POST` | Change password |
| `/api/admin/ai/settings` | `POST` | Update AI settings |
| `/api/admin/ai/test` | `POST` | Test AI API connection |

---

## 🗂️ Project Structure

```
caijing18/
├── main.py                    # 🚀 Main entry (Flask Web + scheduled tasks + route registration)
├── config.py                  # ⚙️ Common configuration (dedup threshold, data retention days, etc.)
├── database.py                # 🗄️ Database models and operations (SQLite + SQLAlchemy)
├── ai_summary.py              # 🤖 AI summary generation (OpenAI-compatible API)
├── tg_scraper.py              # 📡 Telegram public channel web scraper
├── tagger.py                  # 🏷️ Automatic financial tag classification
├── deduplicator.py            # 🔍 Three-layer intelligent deduplication
├── logging_setup.py           # 📋 Logging configuration
├── requirements.txt           # 📦 Python dependencies
├── Dockerfile                 # 🐳 Docker image build
├── docker-compose.yml         # 🐳 Docker Compose orchestration
├── .env.example               # 🔑 Environment variable example
│
├── routes/                    # 🛣️ Route layer
│   ├── __init__.py
│   ├── web_routes.py          #   Web page routes
│   ├── news_api.py            #   News query API routes
│   ├── admin_api.py           #   Admin API routes
│   └── ai_api.py              #   AI summary API routes
│
├── services/                  # 💼 Business service layer
│   ├── __init__.py
│   ├── news_service.py        #   News query service
│   ├── summary_service.py     #   AI summary generation service
│   └── admin_service.py       #   Admin service
│
├── web/                       # 🎨 Frontend resources
│   ├── static/
│   │   ├── css/               #   Stylesheets
│   │   │   ├── style.css
│   │   │   └── admin.css
│   │   └── js/                #   Frontend logic
│   │       ├── app.js
│   │       └── admin.js
│   └── templates/             #   Page templates
│       ├── index.html
│       ├── summary.html
│       └── admin.html
│
└── data/                      # 📂 Data directory (SQLite database auto-created here)
```

---

## ⚙️ Configuration

### Environment Variables (.env)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TG_CHANNEL_URLS` | ✅ Yes | `https://t.me/s/XXXXX` | Public channel URLs to scrape, comma-separated |
| `AI_API_KEY` | ❌ No | — | OpenAI-compatible API Key (recommended to configure via admin panel) |
| `AI_BASE_URL` | ❌ No | `https://api.xxxx.com/v1` | API base URL (recommended to configure via admin panel) |
| `AI_MODEL` | ❌ No | `deepseek-v4-flash` | AI model name (recommended to configure via admin panel) |
| `DATABASE_PATH` | ❌ No | `data/finance_data.db` | SQLite database path |
| `FLASK_HOST` | ❌ No | `0.0.0.0` | Web service listen address |
| `FLASK_PORT` | ❌ No | `5000` | Web service port |

### Core Parameters (config.py)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `SIMILARITY_THRESHOLD` | `0.75` | Deduplication similarity threshold (higher = stricter) |
| `DATA_RETENTION_DAYS` | `7` | Data retention days |
| `MIN_CONTENT_LENGTH` | `20` | Minimum content length (filters out overly short messages) |

### Custom Tag Dictionary

The tagging system is implemented through the `FINANCE_KEYWORDS` dictionary in `config.py`. You can directly modify this dictionary to add, remove, or edit tag categories and keywords.

**Dictionary Structure:**

```python
FINANCE_KEYWORDS = {
    'Category Name 1': ['keyword1', 'keyword2', ...],
    'Category Name 2': ['keyword3', 'keyword4', ...],
}
```

**Example: Adding a "Renewable Energy" category**

```python
FINANCE_KEYWORDS = {
    # Existing categories...
    'Renewable Energy': ['lithium battery', 'photovoltaic', 'wind power', 'electric vehicle', 'energy storage', 'CATL'],
}
```

**Modification Steps:**
1. Open the `config.py` file
2. Locate the `FINANCE_KEYWORDS` dictionary (around line 56)
3. Add, modify, or delete categories and keywords
4. Save the file and restart the service

> ⚠️ Changes require a service restart to take effect; keyword matching is **case-insensitive**.

---

## 🔧 Usage Guide

### First-Time Setup
1. Visit [http://localhost:5000](http://localhost:5000)
2. Go to admin panel `/admin`
3. Log in (default username `admin`, password `admin`)
4. Add a Telegram channel (e.g., `https://t.me/s/xxxxx`)
5. Wait for automatic scraping or click **"Manual Scrape"** on the dashboard
6. Optional: Configure API Key in AI settings to enable AI summary features

### Channel Management
- **Add Channel**: Enter a Telegram public channel URL, set historical backfill count (default 1000)
- **Delete Channel**: Also deletes all associated news data for that channel
- **Enable/Disable**: Disabled channels will not be automatically scraped

### AI Summaries
1. Configure API Key, Base URL, and model in Admin Panel → AI Settings
2. After configuration, go to Summary Center `/summary` to view summaries by time range
3. Supports manual refresh and automatic scheduled generation

---

## 👤 Admin Panel

| Item | Default |
|------|---------|
| **Username** | `admin` |
| **Password** | `admin` |

> ⚠️ **Security Reminder**: Please change your password immediately after first login!

---

## 🔒 Security Notes

- Sensitive configuration (API Key, passwords, etc.) is stored in `.env` file or database, **none are included in version control**
- Change the admin panel password on first use
- AI API Key can be configured online via the admin panel, no need to edit environment variables

---

## 📜 License

This project is open-sourced under the **MIT License**. Feel free to use and contribute.

---

<p align="center">
  Made with ❤️ for the Open Source Community
</p>