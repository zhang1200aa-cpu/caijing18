#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Bot - 监听频道消息并保存链接
"""

import os
import json
import logging
import asyncio
import nest_asyncio
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters
import config

# 允许嵌套的事件循环
nest_asyncio.apply()

# 加载环境变量
load_dotenv()

# ============ 日志配置 ============
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============ 配置 ============
BOT_TOKEN = config.TELEGRAM_BOT_TOKEN
CHANNEL_IDS_STR = os.getenv("TELEGRAM_CHANNEL_ID", "-1001234567890")
CHANNEL_IDS = [int(ch.strip()) for ch in CHANNEL_IDS_STR.split(",") if ch.strip()]

CHANNEL_NAMES = {
    -1001375475051: "Financial_Express",
}

DB_DIR = config.APP_DATA_DIR
LINKS_FILE = os.path.join(DB_DIR, "telegram_links.json")

os.makedirs(DB_DIR, exist_ok=True)

# ============ 工具函数 ============

def save_link(url, text="", channel_id=None, channel_name="Unknown"):
    """保存链接到 JSON 文件"""
    links = []
    if os.path.exists(LINKS_FILE):
        try:
            with open(LINKS_FILE, 'r', encoding='utf-8') as f:
                links = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"⚠️ [Bot] 读取链接文件失败: {e}")
            links = []
    
    # 检查链接是否已存在
    if not any(link.get('url') == url for link in links):
        links.append({
            'url': url,
            'text': text[:100] if text else "",
            'channel_id': channel_id,
            'channel_name': channel_name,
            'date': datetime.now().isoformat(),
        })
        
        # 按日期排序（最新的在前）
        links = sorted(links, key=lambda x: x['date'], reverse=True)
        
        # 保存到文件
        try:
            with open(LINKS_FILE, 'w', encoding='utf-8') as f:
                json.dump(links, f, ensure_ascii=False, indent=2)
            logger.info(f"✅ [Bot] [{channel_name}] 保存链接: {url}")
            return True
        except IOError as e:
            logger.error(f"❌ [Bot] 保存链接失败: {e}")
            return False
    else:
        logger.debug(f"⏭️ [Bot] 链接已存在，跳过: {url}")
        return False

def get_channel_name(channel_id):
    """获取频道名称"""
    return CHANNEL_NAMES.get(channel_id, f"Channel_{channel_id}")

# ============ Bot 消息处理器 ============

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理频道消息"""
    message = update.channel_post
    
    # 安全检查
    if not message or not message.text:
        return
    
    if message.chat_id not in CHANNEL_IDS:
        return
    
    text = message.text
    channel_name = get_channel_name(message.chat_id)
    
    # 提取链接
    words = text.split()
    links_found = 0
    
    for word in words:
        # 识别链接
        if word.startswith(('http://', 'https://', 't.me')):
            # 清理链接（去除末尾的标点符号）
            url = word.rstrip('.,;:!?）)】]')
            
            # 处理 t.me 链接
            if url.startswith('t.me'):
                url = 'https://' + url
            elif not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            # 保存链接
            if save_link(url, text, message.chat_id, channel_name):
                links_found += 1
    
    if links_found > 0:
        logger.info(f"📨 [Bot] [{channel_name}] 消息处理完成，发现 {links_found} 个链接")

# ============ Bot 启动函数 ============

async def run_bot():
    """启动 Bot 异步主函数"""
    
    # 验证配置
    if not BOT_TOKEN:
        logger.error("❌ [Bot] 缺少 TELEGRAM_BOT_TOKEN 环境变量")
        return False
    
    if not CHANNEL_IDS:
        logger.error("❌ [Bot] 缺少 TELEGRAM_CHANNEL_ID 环境变量")
        return False
    
    # 输出启动信息
    logger.info("=" * 70)
    logger.info("🤖 [Bot] Telegram 机器人启动")
    logger.info("=" * 70)
    logger.info(f"📡 监听频道数: {len(CHANNEL_IDS)}")
    for ch_id in CHANNEL_IDS:
        logger.info(f"   - {get_channel_name(ch_id)} (ID: {ch_id})")
    logger.info(f"💾 链接保存位置: {LINKS_FILE}")
    logger.info("=" * 70)
    
    try:
        # 创建应用
        app = Application.builder().token(BOT_TOKEN).build()
        
        # 添加消息处理器
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        logger.info("✅ [Bot] 等待新消息...\n")
        
        # 运行 polling（nest_asyncio 允许嵌套事件循环）
        await app.run_polling(allowed_updates=Update.ALL_TYPES)
        
        return True
    
    except Exception as e:
        logger.error(f"❌ [Bot] 运行失败: {e}", exc_info=True)
        return False

# ============ 主函数 ============

def main():
    """程序入口"""
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logger.info("⚠️ [Bot] 收到中断信号，正在关闭...")
    except Exception as e:
        logger.error(f"❌ [Bot] 致命错误: {e}", exc_info=True)
    finally:
        logger.info("🛑 [Bot] Bot 已停止")

if __name__ == '__main__':
    main()
