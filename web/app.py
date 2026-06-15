# web/app.py
import os
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import sqlite3

# ============================================
# 数据库路径配置（Docker 适配）
# ============================================
DB_DIR = "/app/data"
DB_PATH = os.path.join(DB_DIR, "finance_data.db")

# 确保数据库目录存在
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR, exist_ok=True)

# ============================================
# Flask 应用初始化
# ============================================
app = Flask(__name__)
CORS(app)

# 应用配置
app.config['JSON_AS_ASCII'] = False  # 支持中文
app.config['DATABASE'] = DB_PATH

# ============================================
# 数据库连接函数
# ============================================
def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """初始化数据库"""
    if not os.path.exists(DB_PATH):
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 创建财务数据表（根据你的实际数据结构修改）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS finance_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT,
                amount REAL,
                category TEXT,
                date TEXT,
                source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        print(f"✅ 数据库已初始化: {DB_PATH}")
    else:
        print(f"✅ 数据库已存在: {DB_PATH}")

# ============================================
# API 路由
# ============================================

@app.route('/', methods=['GET'])
def index():
    """主页"""
    return jsonify({
        'status': 'ok',
        'message': '财务数据 API',
        'db_path': DB_PATH,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/data', methods=['GET'])
def get_data():
    """获取所有财务数据"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM finance_data ORDER BY date DESC')
        data = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({
            'status': 'success',
            'data': data,
            'count': len(data)
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/data', methods=['POST'])
def add_data():
    """添加财务数据"""
    try:
        payload = request.get_json()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO finance_data (title, content, amount, category, date, source)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            payload.get('title'),
            payload.get('content'),
            payload.get('amount'),
            payload.get('category'),
            payload.get('date', datetime.now().isoformat()),
            payload.get('source')
        ))
        
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        
        return jsonify({
            'status': 'success',
            'id': new_id,
            'message': '数据已添加'
        }), 201
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/data/<int:data_id>', methods=['GET'])
def get_data_by_id(data_id):
    """获取单条财务数据"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM finance_data WHERE id = ?', (data_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row is None:
            return jsonify({'status': 'error', 'message': '数据不存在'}), 404
        
        return jsonify({
            'status': 'success',
            'data': dict(row)
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/data/<int:data_id>', methods=['PUT'])
def update_data(data_id):
    """更新财务数据"""
    try:
        payload = request.get_json()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE finance_data 
            SET title = ?, content = ?, amount = ?, category = ?, date = ?, source = ?
            WHERE id = ?
        ''', (
            payload.get('title'),
            payload.get('content'),
            payload.get('amount'),
            payload.get('category'),
            payload.get('date'),
            payload.get('source'),
            data_id
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'message': '数据已更新'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/data/<int:data_id>', methods=['DELETE'])
def delete_data(data_id):
    """删除财务数据"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM finance_data WHERE id = ?', (data_id,))
        conn.commit()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'message': '数据已删除'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """获取数据统计"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) as count FROM finance_data')
        total = dict(cursor.fetchone())['count']
        
        cursor.execute('SELECT SUM(amount) as total_amount FROM finance_data')
        total_amount = dict(cursor.fetchone()).get('total_amount', 0) or 0
        
        conn.close()
        
        return jsonify({
            'status': 'success',
            'total_records': total,
            'total_amount': total_amount
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT 1')
        conn.close()
        
        return jsonify({
            'status': 'healthy',
            'db_path': DB_PATH,
            'db_exists': os.path.exists(DB_PATH),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

# ============================================
# 错误处理
# ============================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'status': 'error', 'message': '未找到该资源'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'status': 'error', 'message': '服务器内部错误'}), 500

# ============================================
# 应用启动
# ============================================

if __name__ == '__main__':
    # 初始化数据库
    init_db()
    
    # 启动 Flask 应用
    print(f"\n🚀 启动 Flask 应用...")
    print(f"📂 数据库路径: {DB_PATH}")
    print(f"🌐 访问地址: http://localhost:5000")
    print(f"💚 健康检查: http://localhost:5000/api/health\n")
    
    # 开发环境配置
    app.run(
        host='0.0.0.0',  # Docker 中必须使用 0.0.0.0
        port=5000,
        debug=True,
        use_reloader=False  # Docker 中建议关闭自动重载
    )
