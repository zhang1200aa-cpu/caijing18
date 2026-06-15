#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主程序入口
- 启动 Flask Web 服务器
- 定时任务管理（数据清理、统计）
- Telegram Bot 进程管理
"""

import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, render_template, jsonify, request
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import atexit

# 加载环境变量
load_dotenv()

# ============ 日志配置 ============
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)

# ============ 导入项目模块 ============
from database import init_db, get_db_connection, cleanup_old_data, get_stats
from config import CONFIG

# ============ Flask 应用配置 ============
app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
app.config['JSON_SORT_KEYS'] = False

# ============ 定时任务调度器 ============
scheduler = BackgroundScheduler()
scheduler.start()

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())

# ============ 定时任务函数 ============

def cleanup_task():
    """定时清理任务：删除 7 天前的数据"""
    logger.info("=" * 60)
    logger.info(f"🧹 [Task] 数据清理任务启动 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    try:
        deleted_count = cleanup_old_data()
        logger.info(f"✅ [Task] 清理完成，删除 {deleted_count} 条过期记录")
    except Exception as e:
        logger.error(f"❌ [Task] 清理失败: {str(e)}")
    logger.info("=" * 60)

def stats_task():
    """定时统计任务：生成统计信息"""
    logger.info(f"📊 [Task] 统计任务执行 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    try:
        stats = get_stats()
        logger.info(f"✅ [Task] 统计信息: {stats}")
    except Exception as e:
        logger.error(f"❌ [Task] 统计失败: {str(e)}")

# ============ Flask 路由 ============

@app.route('/')
def index():
    """主页"""
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"❌ [Web] 获取主页失败: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/news', methods=['GET'])
def get_news():
    """获取新闻列表（分页）"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        offset = (page - 1) * per_page
        
        # 获取总数
        cursor.execute("SELECT COUNT(*) FROM articles")
        total = cursor.fetchone()[0]
        
        # 获取分页数据
        cursor.execute(
            """
            SELECT id, title, content, tags, created_at, source
            FROM articles
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (per_page, offset)
        )
        
        articles = []
        for row in cursor.fetchall():
            articles.append({
                'id': row[0],
                'title': row[1],
                'content': row[2],
                'tags': row[3].split(',') if row[3] else [],
                'created_at': row[4],
                'source': row[5],
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': articles,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        })
    except Exception as e:
        logger.error(f"❌ [API] 获取新闻失败: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/search', methods=['GET'])
def search_news():
    """按关键词搜索新闻"""
    try:
        keyword = request.args.get('keyword', '', type=str)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        if not keyword:
            return jsonify({"error": "keyword required"}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        offset = (page - 1) * per_page
        keyword_pattern = f"%{keyword}%"
        
        # 获取总数
        cursor.execute(
            "SELECT COUNT(*) FROM articles WHERE title LIKE ? OR content LIKE ?",
            (keyword_pattern, keyword_pattern)
        )
        total = cursor.fetchone()[0]
        
        # 获取分页数据
        cursor.execute(
            """
            SELECT id, title, content, tags, created_at, source
            FROM articles
            WHERE title LIKE ? OR content LIKE ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (keyword_pattern, keyword_pattern, per_page, offset)
        )
        
        articles = []
        for row in cursor.fetchall():
            articles.append({
                'id': row[0],
                'title': row[1],
                'content': row[2],
                'tags': row[3].split(',') if row[3] else [],
                'created_at': row[4],
                'source': row[5],
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': articles,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        })
    except Exception as e:
        logger.error(f"❌ [API] 搜索失败: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/news/by-tag', methods=['GET'])
def get_news_by_tag():
    """按标签筛选新闻"""
    try:
        tag = request.args.get('tag', '', type=str)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        if not tag:
            return jsonify({"error": "tag required"}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        offset = (page - 1) * per_page
        tag_pattern = f"%{tag}%"
        
        # 获取总数
        cursor.execute("SELECT COUNT(*) FROM articles WHERE tags LIKE ?", (tag_pattern,))
        total = cursor.fetchone()[0]
        
        # 获取分页数据
        cursor.execute(
            """
            SELECT id, title, content, tags, created_at, source
            FROM articles
            WHERE tags LIKE ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (tag_pattern, per_page, offset)
        )
        
        articles = []
        for row in cursor.fetchall():
            articles.append({
                'id': row[0],
                'title': row[1],
                'content': row[2],
                'tags': row[3].split(',') if row[3] else [],
                'created_at': row[4],
                'source': row[5],
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': articles,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        })
    except Exception as e:
        logger.error(f"❌ [API] 按标签筛选失败: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/filter', methods=['GET'])
def filter_news():
    """多条件组合筛选"""
    try:
        tags = request.args.get('tags', '', type=str)
        start_date = request.args.get('start_date', '', type=str)
        end_date = request.args.get('end_date', '', type=str)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        offset = (page - 1) * per_page
        
        # 构建动态查询
        query = "SELECT id, title, content, tags, created_at, source FROM articles WHERE 1=1"
        params = []
        
        if tags:
            tag_list = [t.strip() for t in tags.split(',')]
            tag_conditions = [f"tags LIKE ?" for _ in tag_list]
            query += " AND (" + " OR ".join(tag_conditions) + ")"
            params.extend([f"%{tag}%" for tag in tag_list])
        
        if start_date:
            query += " AND created_at >= ?"
            params.append(f"{start_date} 00:00:00")
        
        if end_date:
            query += " AND created_at <= ?"
            params.append(f"{end_date} 23:59:59")
        
        # 获取总数
        count_query = query.replace(
            "SELECT id, title, content, tags, created_at, source",
            "SELECT COUNT(*)"
        )
        cursor.execute(count_query, params)
        total = cursor.fetchone()[0]
        
        # 获取分页数据
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([per_page, offset])
        cursor.execute(query, params)
        
        articles = []
        for row in cursor.fetchall():
            articles.append({
                'id': row[0],
                'title': row[1],
                'content': row[2],
                'tags': row[3].split(',') if row[3] else [],
                'created_at': row[4],
                'source': row[5],
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': articles,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        })
    except Exception as e:
        logger.error(f"❌ [API] 多条件筛选失败: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/tags', methods=['GET'])
def get_all_tags():
    """获取所有可用标签"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT DISTINCT tags FROM articles WHERE tags IS NOT NULL")
        
        all_tags = set()
        for row in cursor.fetchall():
            if row[0]:
                tags = row[0].split(',')
                all_tags.update([t.strip() for t in tags if t.strip()])
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': sorted(list(all_tags))
        })
    except Exception as e:
        logger.error(f"❌ [API] 获取标签失败: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_api_stats():
    """获取统计信息"""
    try:
        stats = get_stats()
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        logger.error(f"❌ [API] 获取统计信息失败: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/cleanup', methods=['POST'])
def trigger_cleanup():
    """手动触发数据清理"""
    try:
        deleted_count = cleanup_old_data()
        return jsonify({
            'success': True,
            'message': f'Deleted {deleted_count} records'
        })
    except Exception as e:
        logger.error(f"❌ [API] 手动清理失败: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'success': True,
        'message': 'Service is running',
        'timestamp': datetime.now().isoformat()
    })

# ============ 错误处理 ============

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def server_error(error):
    logger.error(f"❌ [Web] 服务器错误: {str(error)}")
    return jsonify({"error": "Internal server error"}), 500

# ============ 主程序 ============

def main():
    """程序入口"""
    logger.info("=" * 60)
    logger.info("🚀 [Main] caijing18 财经新闻聚合平台启动")
    logger.info("=" * 60)
    
    # 初始化数据库
    logger.info("📦 [Main] 初始化数据库...")
    try:
        init_db()
        logger.info("✅ [Main] 数据库初始化完成")
    except Exception as e:
        logger.error(f"❌ [Main] 数据库初始化失败: {str(e)}")
        sys.exit(1)
    
    # 添加定时任务
    logger.info("⏰ [Main] 添加定时任务...")
    try:
        # 每天 03:00 执行数据清理
        scheduler.add_job(
            cleanup_task,
            trigger=CronTrigger(hour=3, minute=0),
            id='cleanup_job',
            name='Daily cleanup task',
            replace_existing=True
        )
        logger.info("✅ [Main] 数据清理任务 - 每天 03:00 执行")
        
        # 每小时执行统计
        scheduler.add_job(
            stats_task,
            trigger=CronTrigger(minute=0),
            id='stats_job',
            name='Hourly stats task',
            replace_existing=True
        )
        logger.info("✅ [Main] 统计任务 - 每小时 00 分执行")
    except Exception as e:
        logger.error(f"❌ [Main] 添加定时任务失败: {str(e)}")
    
    # 启动 Flask 服务器
    logger.info("=" * 60)
    logger.info("🌐 [Main] 启动 Flask Web 服务器...")
    logger.info("=" * 60)
    
    try:
        # 当 Docker 运行时，host 设置为 0.0.0.0，端口为 5000
        app.run(
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=False
        )
    except Exception as e:
        logger.error(f"❌ [Main] Flask 启动失败: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
