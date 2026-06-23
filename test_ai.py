import requests
import json

url = 'https://api.baipiao.eu.org/v1/chat/completions'
payload = {
    'model': 'deepseek-v4-flash-free',
    'messages': [{'role': 'user', 'content': '回复"OK"表示连接正常'}],
    'max_tokens': 100
}
headers = {
    'Authorization': 'Bearer sk-123',
    'Content-Type': 'application/json'
}

print(f'正在测试: {url}')
print(f'模型: {payload["model"]}')
print()

try:
    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    print(f'HTTP状态码: {resp.status_code}')
    if resp.status_code == 200:
        result = resp.json()
        content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
        print(f'✅ AI连接成功!')
        print(f'回复: {content}')
    else:
        print(f'❌ 请求失败')
        print(f'响应内容: {resp.text[:500]}')
except requests.exceptions.ConnectTimeout:
    print('❌ 连接超时 - 服务器无响应')
except requests.exceptions.ConnectionError as e:
    print(f'❌ 连接失败: {e}')
except Exception as e:
    print(f'❌ 错误: {type(e).__name__}: {e}')