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
  Supports <b>AI-powered summaries</b>, <b>interactive financial Q&A analysis</b>, multi-dimensional search and filtering, scheduled task maintenance, and out-of-the-box Docker deployment.
</p>

<p align="center">
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
- Supports multi-channel concurrent scraping, configurable scrape interval (default 30 minutes)
- **Three-layer intelligent deduplication**: based on message ID, content hash, and similarity calculation to effectively filter duplicate content
- **Historical message backfill**: automatically fetches configurable number of historical messages when binding new channels (async background execution with real-time progress tracking)
- **Channel re-scraping**: already bound channels can re-trigger historical message backfill

### 🏷️ Automatic Tag Classification
- Built-in financial dictionary that automatically extracts tags for each news item (stocks, funds, macroeconomics, A-shares, Hong Kong stocks, US stocks, etc.)
- Supports tag filtering and combined queries
- **Customizable tag dictionary**: modify the `FINANCE_KEYWORDS` dictionary in `config.py` to add, remove, or edit categories and keywords

### 🤖 AI-Powered Summaries & Interactive Analysis
- Integrates OpenAI-compatible APIs (supports DeepSeek, GPT, Tongyi Qianwen, and other models)
- **Today's Summary** & **Yesterday's Summary**: generated from all news of the current/previous day
- **3-Day Summary** & **Weekly Summary**: synthesized from daily summaries to extract trends
- **Search Summary**: retrieves and summarizes relevant news by keyword
- **Today's Financial Analysis (QA Interactive)**: answers user's financial questions based on configurable time range (default 24 hours, supports 1 hour ~ 30 days) of news
- **Share link**: copy share link button after QA completion, supports URL parameter auto-asking for easy sharing
- **Configurable scheduling**: each summary type's generation time and enabled status can be configured online via admin panel
- **Custom AI prompts**: daily summary, composite summary (3-day/weekly), and today's financial analysis prompts can be edited online, with reset-to-default support
- **Custom context**: configurable long-term context for AI summaries to help AI understand specific background information
- **Online configuration**: directly configure API Key, Base URL, and model name through the web admin panel
- **Configuration priority**: Database settings > `.env` file > Code defaults
- **Auto-refresh cache**: today's summary auto-refreshes with configurable interval (default 10 minutes, adjustable from 1 minute to 24 hours via admin panel)

### 💾 Data Backup & Restore
- **Database backup**: one-click backup of SQLite database, generates `.db` format backup
- **JSON export**: export all table data as readable JSON format for easy migration and viewing
- **Database restore**: one-click restore database from `.db` backup file
- **JSON import**: import data from JSON file into database (supports selective import by type: news, summaries, channels, settings, etc.)
- **Backup management**: view, download, delete backup files in admin panel
- **Auto backup scheduling**: supports configuring periodic automatic backups, retaining the latest N backup files, auto-cleaning old backups

### 💻 Web Admin Panel
- Modern responsive UI, perfectly adapted for PC and mobile
- **Summary Center** (`/summary`): dedicated page displaying all AI summaries, supports viewing historical summaries
- Full-text search, multi-tag filtering, date range viewing
- Statistics dashboard: total news count, time distribution, tag popularity
- **Channel management**: add/delete/enable/disable channels online, with historical message backfill async progress tracking
- **Backup management**: manage backup files online, supports create/restore/download/delete, auto-backup scheduling configuration
- **AI settings**: configure and test AI API connections online, customize prompts and context
- **System settings**: scrape interval, auto-refresh interval, password modification, site name, announcement
- **First-run setup guide**: automatically detects first-time startup and prompts user to add Telegram channels

### 📨 Telegram Push Notifications
- Supports sending scrape completion notifications via Telegram Bot
- Enable by configuring `TELEGRAM_BOT_TOKEN` and `TG_NOTIFY_CHAT_ID` in `.env`

### ⏰ Scheduled Tasks

| Task | Default Time | Description |
|------|-------------|-------------|
| 🔄 Telegram Scraping | Every 30 min | Automatically check and fetch new messages (configurable interval) |
| 🧠 Daily AI Summary | Daily 20:00 | Generate AI summary for the day's news |
| 📊 3-Day Summary | Daily 20:30 | Synthesized from daily summaries |
| 📈 Weekly Summary | Friday 21:00 | Synthesized from daily summaries |
| 💾 Data Backup | Daily 02:00 | Auto backup database (keep latest N backups) |
| 🧹 Data Cleanup | Daily 03:00 | Automatically delete expired data (7 days) |
| 📋 Statistics Update | Every hour | Update news statistics |

> All summary task execution times and enabled status can be modified online via the admin panel.

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

> 📌 **Tip**: On first use, the system automatically detects first-run status and guides you to add channels. Default admin credentials are `admin` / `admin`. Please change your password immediately.

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
| `/summary/search?q=keyword` | 🔍 Search summary |
| `/summary/date/2026-01-01` | 📚 Historical summary viewer |
| `/admin` | ⚙️ **Admin Panel** — Channel management, AI settings, backup management, system configuration |

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
| `/api/summary/date/<date>` | `GET` | Get historical summary by date (YYYY-MM-DD or YYYYMMDD) |
| `/api/summary/list?start=2026-01-01&end=2026-01-31` | `GET` | Get historical summary list within date range |
| `/api/ai/status` | `GET` | AI system status (configuration, connection, etc.) |
| `/api/ai/today-qa` | `POST` | Submit a question for AI financial analysis based on configurable time range news |

### Backup Management Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/admin/backup/list` | `GET` | Get backup file list |
| `/api/admin/backup/create-db` | `POST` | Create database backup (.db) |
| `/api/admin/backup/export-json` | `POST` | Export data as JSON |
| `/api/admin/backup/restore-db` | `POST` | Restore database from .db backup |
| `/api/admin/backup/import-json` | `POST` | Import data from JSON file |
| `/api/admin/backup/delete` | `POST` | Delete specified backup file |
| `/api/admin/backup/download/<filename>` | `GET` | Download backup file |
| `/api/admin/backup-schedule` | `GET/POST` | Get/update auto backup schedule configuration |

### Admin Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/admin/login` | `POST` | Admin login |
| `/api/admin/logout` | `GET` | Admin logout |
| `/api/admin/check` | `GET` | Check login status |
| `/api/admin/channels` | `GET` | Get channel list |
| `/api/admin/channels/add` | `POST` | Add channel (async historical backfill with progress tracking) |
| `/api/admin/channels/remove` | `POST` | Delete channel (also cleans up associated news) |
| `/api/admin/channels/toggle` | `POST` | Enable/disable channel |
| `/api/admin/channels/re-scrape` | `POST` | Re-trigger channel historical message backfill |
| `/api/admin/check-channels` | `GET` | Check if system has available channels (first-run detection) |
| `/api/admin/settings` | `GET` | Get all settings |
| `/api/admin/settings/update` | `POST` | Update settings |
| `/api/admin/settings/interval` | `POST` | Update scrape interval |
| `/api/admin/auto-refresh-interval` | `GET/POST` | Get/update today's summary auto-refresh interval (minutes, 1~1440) |
| `/api/admin/scrape/trigger` | `POST` | Manually trigger scraping |
| `/api/admin/cleanup` | `POST` | Manually clean up old data |
| `/api/admin/change-password` | `POST` | Change password |
| `/api/admin/ai/settings` | `POST` | Update AI settings |
| `/api/admin/ai/test` | `POST` | Test AI API connection |
| `/api/admin/site-name` | `GET/POST` | Get/update site name |
| `/api/admin/site-notice` | `GET/POST` | Get/update announcement |
| `/api/admin/summary-prompts` | `GET/POST` | Get/update AI summary prompts (daily, composite, today QA) |
| `/api/admin/summary-prompts/todayqa` | `POST` | Update today's financial analysis prompt separately |
| `/api/admin/summary-prompts/reset` | `POST` | Reset specified prompt to default |
| `/api/admin/summary-schedule` | `GET/POST` | Get/update summary schedule configuration (time, enabled) |

---

## 🗂️ Project Structure

```
caijing18/
├── main.py                    # 🚀 Main entry (Flask Web + scheduled tasks + route registration)
├── config.py                  # ⚙️ Common configuration (dedup threshold, data retention days, tag dictionary, etc.)
├── database.py                # 🗄️ Database models and operations (SQLite + SQLAlchemy)
├── tg_scraper.py              # 📡 Telegram public channel web scraper (incremental + historical backfill)
├── tagger.py                  # 🏷️ Automatic financial tag classification (keyword based)
├── deduplicator.py            # 🔍 Three-layer intelligent deduplication (ID, Hash, similarity)
├── logging_setup.py           # 📋 Logging configuration (Windows GBK compatible)
├── telegram_bot.py            # 🤖 Telegram Bot push notification
├── reset_admin.py             # 🔑 Admin password reset script
├── requirements.txt           # 📦 Python dependencies
├── Dockerfile                 # 🐳 Docker image build
├── docker-compose.yml         # 🐳 Docker Compose orchestration
├── .env.example               # 🔑 Environment variable example
│
├── routes/                    # 🛣️ Route layer
│   ├── __init__.py
│   ├── web_routes.py          #   Web page routes (home, admin, summary center)
│   ├── news_api.py            #   News query API routes
│   ├── admin_api.py           #   Admin API routes (includes backup management)
│   └── ai_api.py              #   AI summary & Today QA API routes
│
├── services/                  # 💼 Business service layer
│   ├── __init__.py
│   ├── news_service.py        #   News query service
│   ├── summary_service.py     #   AI summary generation service (all summary types + QA + auto-refresh cache)
│   ├── admin_service.py       #   Admin service (channel sync, schedule management, backup scheduling)
│   └── backup_service.py      #   Data backup & restore service (DB backup/restore, JSON import/export)
│
├── web/                       # 🎨 Frontend resources
│   ├── static/
│   │   ├── css/               #   Stylesheets
│   │   │   ├── style.css
│   │   │   └── admin.css
│   │   └── js/                #   Frontend logic
│   │       ├── app.js
│   │       └── admin.js       #   Admin JS (includes backup management module)
│   └── templates/             #   Page templates
│       ├── index.html
│       ├── summary.html
│       └── admin.html
│
└── data/                      # 📂 Data directory (SQLite database auto-created here)
    ├── finance_data.db        #   SQLite database file
    ├── backups/               #   Backup file storage directory
    └── tg_seen_messages.json  #   Processed message ID cache (pagination dedup)
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
| `FLASK_DEBUG` | ❌ No | `false` | Flask debug mode |
| `TELEGRAM_BOT_TOKEN` | ❌ No | — | Telegram Bot Token (for scrape result push notification) |
| `TG_NOTIFY_CHAT_ID` | ❌ No | — | Telegram chat ID to receive push notifications |
| `TG_NOTIFY_ENABLED` | ❌ No | `false` | Enable TG push notification |
| `BACKUP_DIR` | ❌ No | `data/backups` | Backup file storage directory |
| `BACKUP_MAX_FILES` | ❌ No | `10` | Maximum backup files to retain |

### Core Parameters (config.py)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `SIMILARITY_THRESHOLD` | `0.75` | Deduplication similarity threshold (higher = stricter) |
| `DATA_RETENTION_DAYS` | `7` | Data retention days |
| `MIN_CONTENT_LENGTH` | `20` | Minimum content length (filters out overly short messages) |
| `AI_TIMEOUT` | `120` | AI API request timeout (seconds) |

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
2. System automatically detects first-run status and guides you to admin panel
3. Go to admin panel `/admin`
4. Log in (default username `admin`, password `admin`)
5. Add a Telegram channel (e.g., `https://t.me/s/xxxxx`), set historical backfill count
6. System automatically backfills historical messages in background async; check progress in channel list
7. Wait for automatic scraping or click **"Manual Scrape"** on the dashboard
8. Optional: Configure API Key, Base URL, model in AI settings to enable AI summary features

### Channel Management
- **Add Channel**: Enter a Telegram public channel URL, set historical backfill count (default 1000, async execution)
- **Re-scrape**: Already bound channels support re-triggering historical backfill
- **Delete Channel**: Also deletes all associated news data for that channel
- **Enable/Disable**: Disabled channels will not be automatically scraped

### AI Summaries
1. Configure API Key, Base URL, and model in Admin Panel → AI Settings
2. Customize daily/composite/today QA prompts as needed
3. Configure AI summary long-term context (helps AI understand specific background)
4. Configure generation time and enabled status for each summary type in schedule settings
5. After configuration, go to Summary Center `/summary` to view summaries by time range
6. Supports manual refresh and automatic scheduled generation

### Today's Financial Analysis (QA Interactive)
1. Configure AI API information in admin panel
2. Set analysis time range (default 24 hours, supports 1 hour ~ 30 days)
3. In Summary Center `/summary`, go to "Today's Financial Analysis" tab and enter your question
4. AI answers based on news within the selected time range
5. After answer is generated, click "Copy share link" button to share analysis results

### Data Backup & Restore
1. Operate in Admin Panel → Backup Management tab
2. **Create backup**: supports database backup (.db) and JSON export
3. **Restore data**: select backup file to restore (.db restores database, JSON import selects by type)
4. **Backup scheduling**: configure auto-backup interval and retention count

---

## 👤 Admin Panel

| Item | Default |
|------|---------|
| **Username** | `admin` |
| **Password** | `admin` |

> ⚠️ **Security Reminder**: Please change your password immediately after first login!

### 🔑 Forgot Your Password?

If you forget the admin password, use the built-in password reset script to reset it with one command:

```bash
# Interactive mode (recommended) — prompts for new password
python reset_admin.py

# Directly specify new password (non-interactive)
python reset_admin.py --password your_new_password

# Reset another admin user
python reset_admin.py --username username --password your_new_password

# List all admin accounts
python reset_admin.py --list
```

This script directly operates on the SQLite database and does not depend on the Flask application running status. It works even if the service is down.
The password is hashed using the same algorithm as the system (bcrypt preferred, SHA256 fallback).

#### 🐳 Reset Password in Docker Environment

If you deployed with Docker and forgot the password, **Method 1 is recommended** (simplest):

```bash
# Method 1 (recommended): Run directly on the host machine
# The database is mounted at ./data/ on the host, so the script can access it directly
python reset_admin.py

# Method 2: Run inside the container
docker compose exec app python reset_admin.py
# Or directly specify a new password
docker compose exec app python reset_admin.py --password your_new_password
```

---

## 🔒 Security Notes

- Sensitive configuration (API Key, passwords, etc.) is stored in `.env` file or database, **none are included in version control**
- Change the admin panel password on first use
- AI API Key can be configured online via the admin panel, no need to edit environment variables
- Flask session key auto-generates on first startup and persists to database

---

## 📜 License

This project is open-sourced under the **MIT License**. Feel free to use and contribute.

---

<p align="center">
  Made with ❤️ for the Open Source Community
</p>

<p align="center">
  <a href="https://paypal.me/zhang1200aa"><img src="https://img.shields.io/badge/Donate-PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white" alt="Donate"></a>
</p>