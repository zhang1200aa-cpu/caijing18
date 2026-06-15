🚀 Telegram Finance ExpressTelegram Finance Express 是一个自动化财经新闻聚合与管理平台。它能实时从 Telegram 财经频道抓取新闻，通过智能去重、自动打标处理数据，并通过内置的 Web 面板提供搜索、筛选和可视化展示。📋 功能特点智能聚合：自动监听 Telegram 频道，实时获取财经动态。三层智能去重：基于消息 ID、内容 Hash 及相似度计算，有效过滤重复资讯。自动分类标签：内置财经词典，自动为每条新闻提取“股票”、“基金”、“宏观”等标签。可视化管理面板：简洁的前端界面，支持全文搜索、多标签筛选、日期范围查看。自动化维护：内置定时任务，自动清理 7 天前旧数据，支持数据库备份。生产就绪：支持 Supervisor 进程管理与 Nginx 反向代理配置。🛠️ 快速开始1. 环境准备确保已安装 Python 3.8+，并执行以下命令安装依赖：Bashpip install -r requirements.txt
2. 配置环境创建 .env 文件并将你的 Telegram Bot Token 填入：Bashecho "TELEGRAM_BOT_TOKEN=your_bot_token_here" > .env
(获取方法：在 Telegram 搜索 @BotFather，输入 /newbot 即可创建)3. 运行程序Bashpython main.py
程序启动后，Telegram 机器人将开始监听，同时在 http://localhost:5000 启动管理面板。📂 项目结构Plaintexttelegram_finance/
├── main.py              # 主程序入口
├── config.py            # 配置管理（调整去重阈值、数据保留天数等）
├── database.py          # SQLite 数据库操作封装
├── deduplicator.py      # 智能去重算法模块
├── tagger.py            # 中文财经标签提取模块
├── telegram_bot.py      # Telegram 爬虫机器人逻辑
├── requirements.txt     # 依赖清单
├── .env                 # 环境变量配置
├── web/                 # Flask 后端与模板
│   ├── app.py           # API 接口实现
│   └── templates/       # 前端页面文件
└── finance_data.db      # 自动生成的数据库（SQLite）
⚙️ 自定义配置你可以通过修改 config.py 来微调系统行为：SIMILARITY_THRESHOLD: 去重相似度阈值（建议 0.75）。DATA_RETENTION_DAYS: 数据保留天数（默认 7 天）。FINANCE_KEYWORDS: 定义你的分类词典。🌐 API 文档摘要接口方法说明/api/newsGET获取分页新闻列表/api/searchGET按关键词搜索/api/news/by-tagGET按标签筛选新闻/api/filterGET多条件综合筛选（日期+标签）/api/statsGET获取数据统计看板信息🚀 部署建议使用 Supervisor 守护进程在 /etc/supervisor/conf.d/finance-bot.conf 中添加：Ini, TOML[program:finance-bot]
command=/usr/bin/python3 /path/to/telegram_finance/main.py
directory=/path/to/telegram_finance
autostart=true
autorestart=true
stdout_logfile=/var/log/finance-bot.log
使用 Nginx 反向代理Nginxlocation / {
    proxy_pass http://127.0.0.1:5000;
    proxy_set_header Host $host;
}
💡 扩展建议[ ] AI 摘要：接入 OpenAI/DeepSeek API 自动生成长文摘要。[ ] 邮件订阅：定期发送每日财经要闻至邮箱。[ ] 情感分析：通过 NLP 判断市场情绪指标。[ ] Webhook：新闻发布时推送至钉钉或企业微信。⚖️ 许可证本项目基于 MIT License 开源，欢迎自由使用和二次开发。如果您觉得本项目对你有帮助，欢迎点个 Star 支持一下！
