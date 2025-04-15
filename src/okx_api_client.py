# API连接模块，处理与OKX交易所的通信

import hmac
import base64
import json
import time
import requests
from urllib.parse import urlencode
from datetime import datetime
from config import Config

class OKXClient:
    def __init__(self, api_key=None, secret_key=None, passphrase=None, base_url=None):
        self.api_key = api_key or Config.API_KEY
        self.secret_key = secret_key or Config.SECRET_KEY
        self.passphrase = passphrase or Config.PASSPHRASE
        self.base_url = base_url or Config.BASE_URL
    
    def _get_timestamp(self):
        """获取ISO格式的时间戳"""
        return datetime.utcnow().isoformat("T", "milliseconds") + "Z"
    
    def _sign(self, timestamp, method, request_path, body=''):
        """生成签名"""
        if str(body) == '{}' or str(body) == 'None':
            body = ''
        message = timestamp + method + request_path + (body if body else '')
        mac = hmac.new(
            bytes(self.secret_key, encoding='utf8'),
            bytes(message, encoding='utf-8'),
            digestmod='sha256'
        )
        d = mac.digest()
        return base64.b64encode(d).decode('utf-8')
    
    def _request(self, method, endpoint, params=None, data=None):
        """发送请求到OKX API"""
        url = self.base_url + endpoint
        timestamp = self._get_timestamp()
        
        if method == 'GET' and params:
            query_string = urlencode(params)
            endpoint = f"{endpoint}?{query_string}"
            url = f"{url}?{query_string}"
        
        body = json.dumps(data) if data else ''
        
        headers = {
            'OK-ACCESS-KEY': self.api_key,
            'OK-ACCESS-SIGN': self._sign(timestamp, method, endpoint, body),
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json'
        }
        
        response = requests.request(method, url, headers=headers, data=body)
        return response.json()
    
    def get_account_balance(self):
        """获取账户余额"""
        return self._request('GET', '/api/v5/account/balance')
    
    def get_market_ticker(self, symbol):
        """获取市场行情数据"""
        params = {'instId': symbol}
        return self._request('GET', '/api/v5/market/ticker', params=params)
    
    def get_kline_data(self, symbol, interval, limit=100):
        """获取K线数据"""
        params = {
            'instId': symbol,
            'bar': interval,
            'limit': limit
        }
        return self._request('GET', '/api/v5/market/candles', params=params)
    
    def place_order(self, symbol, side, order_type, size, price=None):
        """下单"""
        data = {
            'instId': symbol,
            'tdMode': 'cash',  # 现货交易使用cash模式
            'side': side,      # buy or sell
            'ordType': order_type,  # market or limit
            'sz': str(size)
        }
        
        if price and order_type == 'limit':
            data['px'] = str(price)
            
        return self._request('POST', '/api/v5/trade/order', data=data)
    
    def cancel_order(self, symbol, order_id):
        """取消订单"""
        data = {
            'instId': symbol,
            'ordId': order_id
        }
        return self._request('POST', '/api/v5/trade/cancel-order', data=data)
    
    def get_order_details(self, symbol, order_id):
        """获取订单详情"""
        params = {
            'instId': symbol,
            'ordId': order_id
        }
        return self._request('GET', '/api/v5/trade/order', params=params)
    
    def get_open_orders(self, symbol):
        """获取未成交订单"""
        params = {
            'instId': symbol,
            'state': 'live'  # 活跃订单
        }
        return self._request('GET', '/api/v5/trade/orders-pending', params=params)