import os
import json
from datetime import datetime
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DB_DIR = "/app/data"
LINKS_FILE = os.path.join(DB_DIR, "telegram_links.json")

os.makedirs(DB_DIR, exist_ok=True)

def save_link(url, text=""):
    """保存链接到 JSON 文件"""
    links = []
    if os.path.exists(LINKS_FILE):
        with open(LINKS_FILE, 'r', encoding='utf-8') as f:
            links = json.load(f)
    
    # 避免重复
    if not any(link.get('url') == url for link in links):
        links.append({
            'url': url,
            'text': text[:100],  # 保存前 100 字
            'date': datetime.now().isoformat(),
        })
        with open(LINKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(links, f, ensure_ascii=False, indent=2)
        print(f"✅ 保存链接: {url}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """接收频道消息"""
    message = update.channel_post
    
    if message and message.text:
        text = message.text
        # 提取所有链接
        words = text.split()
        for word in words:
            if word.startswith(('http://', 'https://', 't.me/')):
                if not word.startswith('t.me/'):
                    word = 'https://' + word if not word.startswith('http') else word
                save_link(word, text)

async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # 监听频道消息
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🤖 Bot 已启动，监听 Financial_Express 频道...")
    await app.run_polling()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
