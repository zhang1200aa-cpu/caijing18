import os
import json
from datetime import datetime
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# ============ 多频道配置 ============
# 支持多个频道，用逗号分隔
CHANNEL_IDS_STR = os.getenv("TELEGRAM_CHANNEL_ID", "-1001234567890,-1009876543210")
CHANNEL_IDS = [int(ch.strip()) for ch in CHANNEL_IDS_STR.split(",") if ch.strip()]

# 频道名称映射（可选）
CHANNEL_NAMES = {
    -1001234567890: "Financial_Express",
    -1009876543210: "其他频道",
}

DB_DIR = "/app/data"
LINKS_FILE = os.path.join(DB_DIR, "telegram_links.json")

os.makedirs(DB_DIR, exist_ok=True)

def save_link(url, text="", channel_id=None, channel_name="Unknown"):
    """保存链接到 JSON 文件"""
    links = []
    if os.path.exists(LINKS_FILE):
        try:
            with open(LINKS_FILE, 'r', encoding='utf-8') as f:
                links = json.load(f)
        except json.JSONDecodeError:
            links = []
    
    # 避免重复
    if not any(link.get('url') == url for link in links):
        links.append({
            'url': url,
            'text': text[:100],
            'channel_id': channel_id,
            'channel_name': channel_name,
            'date': datetime.now().isoformat(),
        })
        
        # 按日期倒序排列（新消息在前）
        links = sorted(links, key=lambda x: x['date'], reverse=True)
        
        with open(LINKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(links, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ [Bot] [{channel_name}] 保存链接: {url}")
        return True
    else:
        logger.debug(f"⏭️ [Bot] 链接已存在，跳过: {url}")
        return False

def get_channel_name(channel_id):
    """获取频道名称"""
    return CHANNEL_NAMES.get(channel_id, f"Channel_{channel_id}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """接收频道消息"""
    message = update.channel_post
    
    if not message:
        return
    
    # 检查是否来自监听的频道
    if message.chat_id not in CHANNEL_IDS:
        return
    
    # 只处理有文本的消息
    if not message.text:
        return
    
    text = message.text
    channel_name = get_channel_name(message.chat_id)
    
    # 提取所有链接
    words = text.split()
    links_found = 0
    
    for word in words:
        # 匹配常见的链接格式
        if word.startswith(('http://', 'https://', 't.me')):
            # 标准化 URL
            if word.startswith('t.me'):
                url = 'https://' + word
            elif word.startswith('http'):
                url = word
            else:
                url = 'https://' + word
            
            # 移除末尾的标点符号（如果有）
            url = url.rstrip('.,;:!?）)】')
            
            if save_link(url, text, message.chat_id, channel_name):
                links_found += 1
    
    if links_found > 0:
        logger.info(f"📨 [Bot] [{channel_name}] 消息处理完成，发现 {links_found} 个链接")

async def run_bot():
    """异步运行 Bot"""
    if not BOT_TOKEN:
        logger.error("❌ [Bot] 缺少 TELEGRAM_BOT_TOKEN")
        return
    
    if not CHANNEL_IDS:
        logger.error("❌ [Bot] 缺少 TELEGRAM_CHANNEL_ID，请在 .env 中配置")
        return
    
    # 启动信息
    logger.info("=" * 60)
    logger.info("🤖 [Bot] Telegram 机器人启动")
    logger.info("=" * 60)
    logger.info(f"📡 监听的频道数: {len(CHANNEL_IDS)}")
    for ch_id in CHANNEL_IDS:
        logger.info(f"   - {get_channel_name(ch_id)} (ID: {ch_id})")
    logger.info(f"💾 链接保存位置: {LINKS_FILE}")
    logger.info("=" * 60)
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # 添加消息处理器
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("✅ [Bot] 等待新消息...\n")
    
    try:
        await app.run_polling()
    except Exception as e:
        logger.error(f"❌ [Bot] 运行错误: {e}", exc_info=True)
        raise

def main():
    """主函数（供 main.py 调用）"""
    import asyncio
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logger.info("\n⏹️ [Bot] 机器人已停止")
    except Exception as e:
        logger.error(f"❌ [Bot] 致命错误: {e}", exc_info=True)

if __name__ == '__main__':
    main()
