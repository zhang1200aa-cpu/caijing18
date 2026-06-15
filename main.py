import asyncio
import logging
import threading
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from database import cleanup_old_data, get_session, FinanceNews
from telegram_bot import get_bot
from web.app import app
import config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('finance_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FinanceBot:
    """主应用程序"""
    
    def __init__(self):
        self.bot = get_bot()
        self.scheduler = BackgroundScheduler()
        self.web_thread = None
    
    def setup_scheduler(self):
        """设置定时任务"""
        # 每天凌晨3点清理过期数据
        self.scheduler.add_job(
            cleanup_old_data,
            'cron',
            hour=3,
            minute=0,
            id='cleanup_job'
        )
        
        # 每小时更新一次统计
        self.scheduler.add_job(
            self.log_stats,
            'interval',
            hours=1,
            id='stats_job'
        )
        
        self.scheduler.start()
        logger.info("[调度器] 定时任务已启动")
    
    def log_stats(self):
        """输出统计信息"""
        session = get_session()
        try:
            total = session.query(FinanceNews).count()
            logger.info(f"[统计] 当前数据库包含 {total} 条新闻")
        finally:
            session.close()
    
    def start_web_server(self):
        """启动Web服务"""
        self.web_thread = threading.Thread(
            target=lambda: app.run(
                host=config.FLASK_HOST,
                port=config.FLASK_PORT,
                debug=config.FLASK_DEBUG,
                use_reloader=False
            ),
            daemon=True
        )
        self.web_thread.start()
        logger.info(f"[Web服务] 启动在 http://{config.FLASK_HOST}:{config.FLASK_PORT}")
    
    async def start_telegram_bot(self):
        """启动Telegram机器人"""
        logger.info("[Telegram] 机器人启动中...")
        try:
            await self.bot.run()
        except Exception as e:
            logger.error(f"[Telegram] 错误: {e}")
            # 自动重连
            await asyncio.sleep(5)
            await self.start_telegram_bot()
    
    async def run(self):
        """运行整个应用"""
        logger.info("=" * 50)
        logger.info("🤖 财经机器人启动")
        logger.info("=" * 50)
        
        # 启动定时任务
        self.setup_scheduler()
        
        # 启动Web服务
        self.start_web_server()
        
        # 启动Telegram机器人
        await self.start_telegram_bot()

def main():
    """主入口"""
    finance_bot = FinanceBot()
    
    try:
        asyncio.run(finance_bot.run())
    except KeyboardInterrupt:
        logger.info("\n[关闭] 机器人正在关闭...")
        if finance_bot.scheduler.running:
            finance_bot.scheduler.shutdown()
        logger.info("[关闭] 机器人已关闭")

if __name__ == '__main__':
    main()
