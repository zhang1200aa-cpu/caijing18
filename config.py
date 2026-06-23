"""
caijing18 配置模块（无副作用的纯配置读取）
"""
import os
from dotenv import load_dotenv

# 加载 .env 文件（幂等操作，多次调用无害）
load_dotenv()

# ============ 数据目录配置 ============
# 支持 Docker 和本地两种环境
APP_DATA_DIR = os.getenv('APP_DATA_DIR', '/app/data')

# ============ 数据库配置 ============
DB_PATH = os.path.join(APP_DATA_DIR, 'finance_data.db')
DATABASE_URL = f'sqlite:///{DB_PATH}'
DATA_RETENTION_DAYS = int(os.getenv('DATA_RETENTION_DAYS', '7'))

# ============ Telegram 频道配置（网页爬取模式） ============
TG_CHANNEL_URLS_STR = os.getenv('TG_CHANNEL_URLS', 'https://t.me/s/example_channel')
TG_CHANNEL_URLS = [url.strip() for url in TG_CHANNEL_URLS_STR.split(',') if url.strip()]

# ============ Telegram Bot Token（可选，用于订阅通知） ============
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')

# ============ Telegram 订阅通知设置 ============
# 接收通知的 Telegram 聊天 ID（群组/频道/用户）
TG_NOTIFY_CHAT_ID = os.getenv('TG_NOTIFY_CHAT_ID', '')
# 是否启用 Telegram 通知推送
TG_NOTIFY_ENABLED = os.getenv('TG_NOTIFY_ENABLED', 'false').lower() == 'true'

# ============ Web 服务配置 ============
FLASK_HOST = os.getenv('FLASK_HOST', '0.0.0.0')
FLASK_PORT = int(os.getenv('FLASK_PORT', 5000))
FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'

# ============ 去重配置 ============
SIMILARITY_THRESHOLD = float(os.getenv('SIMILARITY_THRESHOLD', '0.75'))
MIN_CONTENT_LENGTH = 20

# ============ AI 配置（OpenAI 兼容接口） ============
AI_API_KEY = os.getenv('AI_API_KEY', '')
AI_BASE_URL = os.getenv('AI_BASE_URL', '')
AI_MODEL = os.getenv('AI_MODEL', 'gpt-3.5-turbo')
# AI 总结时的系统提示词
AI_SUMMARY_PROMPT = os.getenv('AI_SUMMARY_PROMPT', '你是一个资深财经分析师，请对以下新闻进行总结分析')

# ============ 抓取间隔配置（分钟，管理后台可动态修改） ============
SCRAPE_INTERVAL_MINUTES = int(os.getenv('SCRAPE_INTERVAL_MINUTES', '30'))

# ============ 日志路径配置（仅路径，目录创建移入主程序） ============
LOG_DIR = os.path.join(APP_DATA_DIR, 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'finance_bot.log')

# ============ 财经关键词配置 ============
FINANCE_KEYWORDS = {
    '股票': ['股票', 'A股', '股市', '大盘', '涨停', '跌停', '破位', '上市', '融资', '个股', '沪深300'],
    '基金': ['基金', '净值', '涨幅', '基民', '基民', '持仓'],
    '债券': ['债券', '收益率', '利息', '到期', '国债', '企债'],
    '期货': ['期货', '大宗商品', '原油', '金价', '螺纹钢'],
    '外汇': ['美元', '欧元', '人民币', '汇率', '外汇'],
    '房产': ['房产', '楼市', '房价', '降息', '购房', '置业'],
    '加密': ['比特币', '以太坊', '币圈', '区块链', '虚拟货币'],
    '宏观': ['GDP', '通胀', '央行', '政策', '降准', '降息', '经济'],
    '科技': ['科技股', '互联网', '芯片', '新能源', '智能'],
    'AI': ['AI', '人工智能', '大模型', '机器学习', '深度学习', 'GPT', 'ChatGPT', 'OpenAI', 'AI芯片', '算力'],
    '数据中心': ['数据中心', 'IDC', '云计算', '服务器', '云服务'],
    '其他': ['财经', '投资', '交易', '市场'],
}


def save_ai_config(**kwargs):
    """保存 AI 配置到数据库（运行时持久化，不修改 .env 文件）
    
    支持的参数:
        api_key: AI API Key
        base_url: AI Base URL
        model: AI 模型名
    """
    from database import set_setting
    key_map = {
        'api_key': 'ai_api_key',
        'base_url': 'ai_base_url',
        'model': 'ai_model',
    }
    for param, db_key in key_map.items():
        if param in kwargs and kwargs[param] is not None:
            value = kwargs[param].strip()
            if value:
                set_setting(db_key, value)