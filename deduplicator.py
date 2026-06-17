import hashlib
import difflib
import logging
from datetime import datetime, timedelta
from database import FinanceNews
import config
from db import session_scope_readonly

logger = logging.getLogger(__name__)


class Deduplicator:
    """智能去重模块"""

    @staticmethod
    def generate_hash(text: str) -> str:
        """生成文本哈希"""
        return hashlib.md5(text.encode()).hexdigest()

    @staticmethod
    def get_similarity(text1: str, text2: str) -> float:
        """计算两个文本的相似度"""
        return difflib.SequenceMatcher(None, text1, text2).ratio()

    @staticmethod
    def is_duplicate(title: str, content: str, message_id: str = None) -> tuple:
        """
        判断是否重复
        1. 优先检查 message_id（精确去重）
        2. 检查内容哈希
        3. 检查相似度

        Returns:
            (is_duplicate: bool, reason: Optional[str])
        """
        content_hash = Deduplicator.generate_hash(content)
        try:
            with session_scope_readonly() as session:
                # 1. 消息ID精确去重
                if message_id:
                    existing = session.query(FinanceNews).filter(
                        FinanceNews.message_id == message_id
                    ).first()
                    if existing:
                        return True, "消息ID重复"

                # 2. 内容哈希去重
                existing = session.query(FinanceNews).filter(
                    FinanceNews.id == content_hash
                ).first()
                if existing:
                    return True, "内容哈希重复"

                # 3. 24小时内相似度检查
                cutoff_time = datetime.utcnow() - timedelta(hours=24)
                recent_news = session.query(FinanceNews).filter(
                    FinanceNews.published_time >= cutoff_time
                ).all()

                for news in recent_news:
                    similarity = Deduplicator.get_similarity(title, news.title)
                    if similarity > config.SIMILARITY_THRESHOLD:
                        return True, f"相似度{similarity:.2%}超过阈值"

            return False, None
        except Exception as e:
            logger.error(f"[去重] 检查失败: {e}")
            return False, None


deduplicator = Deduplicator()
