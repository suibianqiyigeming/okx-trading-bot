# 数据获取和处理模块

import os
import pandas as pd
import numpy as np
from datetime import datetime
from api import OKXClient
from config import Config

class DataManager:
    def __init__(self, client=None):
        self.client = client or OKXClient()
        self.data_cache = {}  # 用于缓存数据
        
        # 确保数据目录存在
        if not os.path.exists(Config.DATA_DIR):
            os.makedirs(Config.DATA_DIR)
    
    def get_ticker(self, symbol):
        """获取最新市场行情"""
        response = self.client.get_market_ticker(symbol)
        if response.get('code') == '0':
            return response.get('data')[0]
        return None
    
    def get_latest_price(self, symbol):
        """获取最新价格"""
        ticker = self.get_ticker(symbol)
        if ticker:
            return float(ticker.get('last'))
        return None
    
    def get_kline_data(self, symbol, interval=None, limit=100, use_cache=True):
        """获取K线数据并转换为DataFrame"""
        interval = interval or Config.TIME_INTERVAL
        
        # 检查缓存
        cache_key = f"{symbol}_{interval}_{limit}"
        if use_cache and cache_key in self.data_cache:
            return self.data_cache[cache_key]
        
        # 请求新数据
        response = self.client.get_kline_data(symbol, interval, limit)
        
        if response.get('code') == '0':
            data = response.get('data', [])
            
            # 转换为DataFrame
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume', 'currency_volume'
            ])
            
            # 转换数据类型
            for col in ['open', 'high', 'low', 'close', 'volume', 'currency_volume']:
                df[col] = pd.to_numeric(df[col])
            
            # 将时间戳转换为datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # 设置索引
            df.set_index('timestamp', inplace=True)
            
            # 按时间升序排序
            df.sort_index(inplace=True)
            
            # 存入缓存
            self.data_cache[cache_key] = df
            
            return df
        
        return pd.DataFrame()  # 返回空DataFrame作为备选
    
    def get_account_balance(self):
        """获取账户余额"""
        response = self.client.get_account_balance()
        if response.get('code') == '0':
            return response.get('data', [])
        return None
    
    def get_available_balance(self, currency='USDT'):
        """获取可用余额"""
        balance_data = self.get_account_balance()
        if balance_data:
            for account in balance_data:
                for currency_data in account.get('details', []):
                    if currency_data.get('ccy') == currency:
                        return float(currency_data.get('availBal', 0))
        return 0