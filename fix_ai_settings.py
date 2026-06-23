"""
修复 AI 设置脚本
- 清除数据库中错误的 AI 配置（让代码回退到使用 .env 的配置）
"""
import sys
import os

# 确保在项目根目录运行
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from database import get_all_settings, set_setting, get_session

def main():
    print("=" * 50)
    print("🔧 AI 设置修复工具")
    print("=" * 50)
    
    # 检查当前数据库中的 AI 设置
    settings = get_all_settings()
    print("\n📋 当前数据库中的 AI 设置：")
    ai_keys = ['ai_api_key', 'ai_base_url', 'ai_model']
    for k in ai_keys:
        val = ''
        if isinstance(settings, dict):
            val = settings.get(k, '')
        elif isinstance(settings, list):
            for s in settings:
                if s.get('key') == k:
                    val = s.get('value', '')
        display = val[:10] + '...' if val and len(val) > 10 else val
        print(f"   {k} = {display or '(空)'}")
    
    # 检查是否包含脱敏值
    needs_fix = False
    if isinstance(settings, dict):
        api_key = settings.get('ai_api_key', '')
    else:
        api_key = ''
        for s in (settings or []):
            if s.get('key') == 'ai_api_key':
                api_key = s.get('value', '')
    
    if api_key and api_key.startswith('****'):
        needs_fix = True
        print(f"\n⚠️  检测到脱敏后的 API Key: '{api_key}'")
    
    # 检查 .env 文件
    env_api_key = ''
    env_base_url = ''
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('AI_API_KEY='):
                    env_api_key = line.split('=', 1)[1].strip().strip('"').strip("'")
                elif line.startswith('AI_BASE_URL='):
                    env_base_url = line.split('=', 1)[1].strip().strip('"').strip("'")
    
    print(f"\n📄 .env 文件中的配置：")
    print(f"   AI_API_KEY = {env_api_key[:10] + '...' if len(env_api_key) > 10 else env_api_key or '(空)'}")
    print(f"   AI_BASE_URL = {env_base_url or '(空)'}")
    
    if needs_fix:
        print("\n🛠️  正在修复...")
        # 清空数据库中错误的 AI 设置，让代码回退到 .env
        set_setting('ai_api_key', '')
        set_setting('ai_base_url', '')
        set_setting('ai_model', '')
        print("✅ 已清除数据库中错误的 AI 设置，现在会使用 .env 中的配置")
    
    if not env_api_key:
        print("\n⚠️  .env 中未配置 AI_API_KEY，请添加")
    
    if not env_base_url:
        print("\n⚠️  .env 中未配置 AI_BASE_URL，请添加")
    
    # 验证修复结果
    print("\n📋 修复后数据库中的 AI 设置：")
    settings2 = get_all_settings()
    for k in ai_keys:
        val = ''
        if isinstance(settings2, dict):
            val = settings2.get(k, '')
        elif isinstance(settings2, list):
            for s in settings2:
                if s.get('key') == k:
                    val = s.get('value', '')
        print(f"   {k} = {val or '(已清除，将使用 .env)'}")
    
    print("\n" + "=" * 50)
    print("✅ 修复完成！")
    print("💡 提示：请确保 .env 中的 AI_BASE_URL 和 AI_API_KEY 配置正确")
    print("=" * 50)

if __name__ == '__main__':
    main()