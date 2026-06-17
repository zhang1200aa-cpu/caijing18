"""
caijing18 Flask 路由模块
"""
from .web_routes import web_bp
from .news_api import news_api_bp
from .admin_api import admin_api_bp
from .ai_api import ai_api_bp

__all__ = ['web_bp', 'news_api_bp', 'admin_api_bp', 'ai_api_bp']