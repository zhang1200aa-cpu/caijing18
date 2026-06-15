import os
from dotenv import load_dotenv

load_dotenv()

# Telegram 配置
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'your_bot_token_here')
TARGET_CHANNEL = '@Financial_Express'  # 目标频道

# 数据库配置
DATABASE_URL = 'sqlite:///./finance_data.db'
DATA_RETENTION_DAYS = 7

# Web 服务配置
FLASK_HOST = '0.0.0.0'
FLASK_PORT = 5000
FLASK_DEBUG = False

# 去重配置
SIMILARITY_THRESHOLD = 0.75  # 相似度阈值
MIN_CONTENT_LENGTH = 20  # 最小内容长度

# 标签配置
FINANCE_KEYWORDS = {
    '股票': ['股票', '涨停', '跌停', '破位', '上市', '融资'],
    '基金': ['基金', '净值', '涨幅', '基民'],
    '债券': ['债券', '收益率', '利息', '到期'],
    '期货': ['期货', '大宗商品', '原油', '金价'],
    '外汇': ['美元', '欧元', '人民币', '汇率'],
    '房产': ['房产', '楼市', '房价', '降息'],
    '加密': ['比特币', '以太坊', '币圈', '区块链'],
    '宏观': ['GDP', '通胀', '央行', '政策', '降准', '降息'],
}
