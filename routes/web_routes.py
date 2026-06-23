"""
Web 页面路由
"""
import logging
from flask import Blueprint, render_template, request

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
def summary_index():
    """AI 总结中心首页"""
    try:
        return render_template('summary.html', range_key='')
    except Exception as e:
        logger.error(f"❌ [Web] 加载总结页面失败: {str(e)}")
        return render_template('summary.html', range_key='', error=str(e)), 500


@web_bp.route('/summary/today')
def summary_today():
    """今日总结页面"""
    try:
        return render_template('summary.html', range_key='today')
    except Exception as e:
        logger.error(f"❌ [Web] 加载今日总结失败: {str(e)}")
        return render_template('summary.html', range_key='today', error=str(e)), 500


@web_bp.route('/summary/yesterday')
def summary_yesterday():
    """昨日总结页面"""
    try:
        return render_template('summary.html', range_key='yesterday')
    except Exception as e:
        logger.error(f"❌ [Web] 加载昨日总结失败: {str(e)}")
        return render_template('summary.html', range_key='yesterday', error=str(e)), 500


@web_bp.route('/summary/3d')
def summary_3d():
    """三天总结页面"""
    try:
        return render_template('summary.html', range_key='3d')
    except Exception as e:
        logger.error(f"❌ [Web] 加载三天总结失败: {str(e)}")
        return render_template('summary.html', range_key='3d', error=str(e)), 500


@web_bp.route('/summary/1w')
def summary_1w():
    """一周总结页面"""
    try:
        return render_template('summary.html', range_key='1w')
    except Exception as e:
        logger.error(f"❌ [Web] 加载一周总结失败: {str(e)}")
        return render_template('summary.html', range_key='1w', error=str(e)), 500


@web_bp.route('/summary/search')
def summary_search():
    """搜索总结页面"""
    try:
        q = request.args.get('q', '')
        return render_template('summary.html', range_key='', search_query=q)
    except Exception as e:
        logger.error(f"❌ [Web] 加载搜索总结失败: {str(e)}")
        return render_template('summary.html', range_key='', error=str(e)), 500


@web_bp.route('/summary/date/<date_str>')
def summary_date(date_str):
    """按日期查看历史总结页面"""
    try:
        return render_template('summary.html', range_key='history', date_param=date_str)
    except Exception as e:
        logger.error(f"❌ [Web] 加载历史总结失败: {str(e)}")
        return render_template('summary.html', range_key='history', error=str(e)), 500