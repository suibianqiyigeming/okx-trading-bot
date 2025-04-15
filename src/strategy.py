# 策略模块，实现不同的交易策略

import pandas as pd
import numpy as np
from abc import ABC, abstractmethod

class Strategy(ABC):
    """抽象策略类，所有具体策略都应该继承此类"""
    
    @abstractmethod
    def generate_signals(self, data):
        """生成交易信号"""
        pass

class MACDStrategy(Strategy):
    """基于MACD指标的交易策略"""
    
    def __init__(self, fast_period=12, slow_period=26, signal_period=9):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
    
    def calculate_macd(self, data):
        """计算MACD指标"""
        df = data.copy()
        
        # 计算快速和慢速EMA
        df['ema_fast'] = df['close'].ewm(span=self.fast_period, adjust=False).mean()
        df['ema_slow'] = df['close'].ewm(span=self.slow_period, adjust=False).mean()
        
        # 计算MACD线和信号线
        df['macd'] = df['ema_fast'] - df['ema_slow']
        df['signal'] = df['macd'].ewm(span=self.signal_period, adjust=False).mean()
        
        # 计算直方图(MACD - Signal)
        df['histogram'] = df['macd'] - df['signal']
        
        return df
    
    def generate_signals(self, data):
        """根据MACD指标生成买卖信号"""
        df = self.calculate_macd(data)
        
        # 生成信号
        df['signal_action'] = 'hold'  # 默认为持有
        
        # MACD金叉(MACD线上穿信号线)
        df.loc[(df['macd'] > df['signal']) & (df['macd'].shift(1) <= df['signal'].shift(1)), 'signal_action'] = 'buy'
        
        # MACD死叉(MACD线下穿信号线)
        df.loc[(df['macd'] < df['signal']) & (df['macd'].shift(1) >= df['signal'].shift(1)), 'signal_action'] = 'sell'
        
        return df

class RSIStrategy(Strategy):
    """基于RSI指标的交易策略"""
    
    def __init__(self, period=14, oversold=30, overbought=70):
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
    
    def calculate_rsi(self, data):
        """计算RSI指标"""
        df = data.copy()
        
        # 计算价格变化
        df['price_change'] = df['close'].diff()
        
        # 计算上涨和下跌
        df['gain'] = np.where(df['price_change'] > 0, df['price_change'], 0)
        df['loss'] = np.where(df['price_change'] < 0, -df['price_change'], 0)
        
        # 计算平均上涨和下跌
        df['avg_gain'] = df['gain'].rolling(window=self.period).mean()
        df['avg_loss'] = df['loss'].rolling(window=self.period).mean()
        
        # 计算相对强度(RS)
        df['rs'] = df['avg_gain'] / df['avg_loss']
        
        # 计算RSI
        df['rsi'] = 100 - (100 / (1 + df['rs']))
        
        return df
    
    def generate_signals(self, data):
        """根据RSI指标生成买卖信号"""
        df = self.calculate_rsi(data)
        
        # 生成信号
        df['signal_action'] = 'hold'  # 默认为持有
        
        # RSI超卖区间反弹，产生买入信号
        df.loc[(df['rsi'] > self.oversold) & (df['rsi'].shift(1) <= self.oversold), 'signal_action'] = 'buy'
        
        # RSI超买区间回落，产生卖出信号
        df.loc[(df['rsi'] < self.overbought) & (df['rsi'].shift(1) >= self.overbought), 'signal_action'] = 'sell'
        
        return df

class CombinedStrategy(Strategy):
    """组合多个策略的复合策略"""
    
    def __init__(self, strategies=None):
        self.strategies = strategies or []
    
    def add_strategy(self, strategy):
        """添加策略到组合中"""
        self.strategies.append(strategy)
    
    def generate_signals(self, data):
        """根据所有策略产生的信号，生成综合信号"""
        if not self.strategies:
            return data
        
        df = data.copy()
        buy_signals = 0
        sell_signals = 0
        
        # 计算每个策略的信号
        for i, strategy in enumerate(self.strategies):
            strategy_df = strategy.generate_signals(data)
            df[f'strategy_{i}_signal'] = strategy_df['signal_action']
            
            # 统计买卖信号数量
            buy_signals += (strategy_df['signal_action'] == 'buy').sum()
            sell_signals += (strategy_df['signal_action'] == 'sell').sum()
        
        # 生成最终信号(可以基于多数投票或其他规则)
        df['signal_action'] = 'hold'
        
        # 简单的多数投票机制
        for index in df.index:
            votes = {'buy': 0, 'sell': 0, 'hold': 0}
            
            for i in range(len(self.strategies)):
                signal = df.loc[index, f'strategy_{i}_signal']
                votes[signal] += 1
            
            # 找出票数最多的信号
            max_votes = max(votes.values())
            max_signals = [k for k, v in votes.items() if v == max_votes]
            
            # 如果有多个票数相同的信号，优先选择更积极的操作
            if 'buy' in max_signals:
                df.loc[index, 'signal_action'] = 'buy'
            elif 'sell' in max_signals:
                df.loc[index, 'signal_action'] = 'sell'
            else:
                df.loc[index, 'signal_action'] = 'hold'
        
        return df