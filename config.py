import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# ============ 数据目录配置 ============
# 支持Docker和本地两种环境
APP_DATA_DIR = os.getenv('APP_DATA_DIR', '/app/data')
if not os.path.exists(APP_DATA_DIR):
    os.makedirs(APP_DATA_DIR, exist_ok=True)

# ============ 数据库配置 ============
DB_PATH = os.path.join(APP_DATA_DIR, 'finance_data.db')
DATABASE_URL = f'sqlite:///{DB_PATH}'
DATA_RETENTION_DAYS = 7

print(f"[数据库] 路径: {DB_PATH}")
print(f"[数据目录] {APP_DATA_DIR}")

# ============ Telegram 配置 ============
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'your_bot_token_here')
TARGET_CHANNEL = '@Financial_Express'
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "-1001234567890")  # Financial_Express 的 ID
TELEGRAM_CHANNEL_USERNAME = "Financial_Express"  # 频道用户名

# ============ Web 服务配置 ============
FLASK_HOST = os.getenv('FLASK_HOST', '0.0.0.0')
FLASK_PORT = int(os.getenv('FLASK_PORT', 5000))
FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'

# ============ 去重配置 ============
SIMILARITY_THRESHOLD = float(os.getenv('SIMILARITY_THRESHOLD', 0.75))
MIN_CONTENT_LENGTH = 20

# ============ 日志配置 ============
LOG_DIR = os.path.join(APP_DATA_DIR, 'logs')
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, 'finance_bot.log')

# ============ 财经关键词配置 ============
FINANCE_KEYWORDS = {
    '股票': ['股票', '涨停', '跌停', '破位', '上市', '融资', '个股', '沪深300'],
    '基金': ['基金', '净值', '涨幅', '基民', '基民', '持仓'],
    '债券': ['债券', '收益率', '利息', '到期', '国债', '企债'],
    '期货': ['期货', '大宗商品', '原油', '金价', '螺纹钢'],
    '外汇': ['美元', '欧元', '人民币', '汇率', '外汇'],
    '房产': ['房产', '楼市', '房价', '降息', '购房', '置业'],
    '加密': ['比特币', '以太坊', '币圈', '区块链', '虚拟货币'],
    '宏观': ['GDP', '通胀', '央行', '政策', '降准', '降息', '经济'],
    '科技': ['科技股', '互联网', '芯片', '新能源', '智能'],
    '其他': ['财经', '投资', '交易', '市场'],
}
