import hmac
import hashlib
import time
import requests
from urllib.parse import urlencode


# 填入你的 API 信息
API_KEY = "f3b61ddd-f9fa-46dd-b473-223b2a5b160d"
SECRET_KEY = "AB0CC20F1A122C6665A191403A62A710"
PASSPHRASE = "Pql7621200208."
BASE_URL = 'https://www.okx.com'
SIMULATED_BASE_URL = 'https://www.okx.com'  # 模拟盘使用相同的基础 URL

# 生成签名
def sign(message, secret_key):
    mac = hmac.new(bytes(secret_key, encoding='utf8'), bytes(message, encoding='utf-8'), digestmod='sha256')
    return mac.hexdigest()

# 生成请求头
def get_headers(method, path, body=''):
    timestamp = str(int(time.time() * 1000))
    if isinstance(body, dict):
        body = urlencode(body) if body else ''
    message = timestamp + method.upper() + path + body
    signature = sign(message, SECRET_KEY)
    headers = {
        'OK-ACCESS-KEY': API_KEY,
        'OK-ACCESS-SIGN': signature,
        'OK-ACCESS-TIMESTAMP': timestamp,
        'OK-ACCESS-PASSPHRASE': PASSPHRASE,
        'Content-Type': 'application/json'
    }
    return headers

# 获取账户信息
def get_account_info():
    path = '/api/v5/asset/balances'
    method = 'GET'
    headers = get_headers(method, path)
    url = SIMULATED_BASE_URL + path
    response = requests.get(url, headers=headers)
    return response.json()

if __name__ == "__main__":
    account_info = get_account_info()
    print(account_info)