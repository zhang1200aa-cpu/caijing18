"""
Web 页面路由
"""
import logging
from flask import Blueprint, render_template

logger = logging.getLogger(__name__)

web_bp = Blueprint('web', __name__)


@web_bp.route('/')
def index():
    """首页：管理面板"""
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"❌ [Web] 加载首页失败: {str(e)}")
        return f"<h1>caijing18</h1><p>财经新闻聚合平台</p><p>错误: {str(e)}</p>"


@web_bp.route('/admin')
def admin_panel():
    """管理后台"""
    try:
        return render_template('admin.html')
    except Exception as e:
        logger.error(f"❌ [Web] 加载管理后台失败: {str(e)}")
        return f"<h1>管理后台</h1><p>错误: {str(e)}</p>"


@web_bp.route('/summary')
@web_bp.route('/summary/<range_key>')
def summary_page(range_key='1d'):
    """AI 总结页面"""
    try:
        return render_template('summary.html')
    except Exception as e:
        logger.error(f"❌ [Web] 获取默认总结失败: {str(e)}")
        return render_template('summary.html', error=str(e)), 500
