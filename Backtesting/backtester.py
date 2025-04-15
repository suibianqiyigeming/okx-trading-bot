# 回测模块，用于测试策略在历史数据上的表现

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from data_manager import DataManager
from strategy import MACDStrategy, RSIStrategy, CombinedStrategy
from config import Config
from logger import Logger

class Backtester:
    def __init__(self, symbols=None, timeframe=None, start_date=None, end_date=None):
        self.symbols = symbols or Config.SYMBOLS
        self.timeframe = timeframe or Config.TIME_INTERVAL
        
        # 设置默认回测时间范围
        self.end_date = end_date or datetime.now()
        self.start_date = start_date or (self.end_date - timedelta(days=30))
        
        self.data_manager = DataManager()
        self.logger = Logger()
        
        # 存储回测结果
        self.results = {}
    
    def fetch_historical_data(self, symbol, limit=1000):
        """获取历史数据"""
        try:
            # 尝试从本地文件获取数据
            file_path = f"{Config.DATA_DIR}/{symbol}_{self.timeframe}_historical.csv"
            
            try:
                df = pd.read_csv(file_path, index_col='timestamp', parse_dates=True)
                self.logger.info(f"Loaded historical data for {symbol} from file")
                return df
            except:
                self.logger.info(f"No local data file found for {symbol}, fetching from API")
            
            # 从API获取数据
            df = self.data_manager.get_kline_data(symbol, self.timeframe, limit=limit)
            
            if df.empty:
                self.logger.error(f"Failed to fetch historical data for {symbol}")
                return None
            
            # 过滤时间范围
            df = df[(df.index >= self.start_date) & (df.index <= self.end_date)]
            
            # 保存到本地
            df.to_csv(file_path)
            
            self.logger.info(f"Fetched and saved historical data for {symbol}")
            return df
            
        except Exception as e:
            self.logger.error(f"Error fetching historical data for {symbol}: {str(e)}")
            return None
    
    def run_backtest(self, strategy, symbol, initial_capital=10000):
        """运行单个符号的回测"""
        # 获取历史数据
        data = self.fetch_historical_data(symbol)
        
        if data is None or data.empty:
            self.logger.error(f"No data available for backtest of {symbol}")
            return None
        
        # 生成交易信号
        df = strategy.generate_signals(data)
        
        # 添加价格变化列
        df['price_change'] = df['close'].pct_change()
        
        # 初始化资金和持仓
        capital = initial_capital
        position = 0
        
        # 记录每个交易日的资金
        df['capital'] = capital
        
        # 记录交易
        trades = []
        
        # 模拟交易
        for i in range(1, len(df)):
            current_row = df.iloc[i]
            prev_row = df.iloc[i-1]
            
            # 获取当前信号
            signal = current_row['signal_action']
            price = current_row['close']
            
            # 更新之前持仓的价值
            if position > 0:
                # 多头仓位价值变化
                capital = capital * (1 + current_row['price_change'])
            
            # 执行买入信号
            if signal == 'buy' and position == 0:
                position = 1  # 建立多头仓位
                entry_price = price
                entry_date = current_row.name
                
                trades.append({
                    'type': 'buy',
                    'date': entry_date,
                    'price': entry_price,
                    'capital': capital
                })
                
                self.logger.debug(f"BUY: {symbol} at {price} on {entry_date}")
            
            # 执行卖出信号
            elif signal == 'sell' and position == 1:
                position = 0  # 平仓
                exit_price = price
                exit_date = current_row.name
                
                profit_pct = (exit_price / entry_price - 1) * 100
                
                trades.append({
                    'type': 'sell',
                    'date': exit_date,
                    'price': exit_price,
                    'capital': capital,
                    'profit_pct': profit_pct
                })
                
                self.logger.debug(f"SELL: {symbol} at {price} on {exit_date}, profit: {profit_pct:.2f}%")
            
            # 记录每日资金
            df.at[current_row.name, 'capital'] = capital
        
        # 计算每日收益率
        df['returns'] = df['capital'].pct_change()
        
        # 计算累计收益
        df['cumulative_returns'] = (1 + df['returns']).cumprod()
        
        # 计算回撤
        df['cummax'] = df['cumulative_returns'].cummax()
        df['drawdown'] = df['cummax'] - df['cumulative_returns']
        df['drawdown_pct'] = df['drawdown'] / df['cummax']
        
        # 计算性能指标
        total_return = (df['capital'].iloc[-1] / initial_capital - 1) * 100
        
        # 计算年化收益率
        days = (df.index[-1] - df.index[0]).days
        annual_return = ((1 + total_return / 100) ** (365 / days) - 1) * 100 if days > 0 else 0
        
        # 夏普比率 (假设无风险利率为0)
        sharpe_ratio = df['returns'].mean() / df['returns'].std() * (252 ** 0.5) if df['returns'].std() > 0 else 0
        
        # 最大回撤
        max_drawdown = df['drawdown_pct'].max() * 100
        
        # 计算胜率
        if trades:
            winning_trades = [t for t in trades if t.get('type') == 'sell' and t.get('profit_pct', 0) > 0]
            win_rate = len(winning_trades) / (len(trades) // 2) * 100 if len(trades) > 0 else 0
        else:
            win_rate = 0
        
        # 存储结果
        result = {
            'symbol': symbol,
            'total_return': total_return,
            'annual_return': annual_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'trades_count': len(trades) // 2,  # 买入和卖出算一次交易
            'trades': trades,
            'dataframe': df
        }
        
        self.results[symbol] = result
        return result
    
    def run_all(self, strategy_class=CombinedStrategy, initial_capital=10000):
        """运行所有交易对的回测"""
        for symbol in self.symbols:
            # 创建策略实例
            if strategy_class == CombinedStrategy:
                strategy = CombinedStrategy()
                strategy.add_strategy(MACDStrategy())
                strategy.add_strategy(RSIStrategy())
            else:
                strategy = strategy_class()
            
            self.logger.info(f"Running backtest for {symbol}...")
            result = self.run_backtest(strategy, symbol, initial_capital)
            
            if result:
                self.logger.info(f"Backtest completed for {symbol}")
                self.logger.info(f"Total Return: {result['total_return']:.2f}%")
                self.logger.info(f"Sharpe Ratio: {result['sharpe_ratio']:.2f}")
                self.logger.info(f"Max Drawdown: {result['max_drawdown']:.2f}%")
                self.logger.info(f"Win Rate: {result['win_rate']:.2f}%")
                self.logger.info(f"Number of Trades: {result['trades_count']}")
                self.logger.info("------------------------")
    
    def generate_report(self):
        """生成回测报告"""
        if not self.results:
            self.logger.warning("No backtest results available")
            return "No results available"
        
        report = "===== Backtest Results =====\n\n"
        report += f"Period: {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}\n"
        report += f"Timeframe: {self.timeframe}\n\n"
        
        # 汇总结果
        symbols_summary = []
        for symbol, result in self.results.items():
            symbols_summary.append({
                'Symbol': symbol,
                'Return (%)': f"{result['total_return']:.2f}",
                'Annual (%)': f"{result['annual_return']:.2f}",
                'Sharpe': f"{result['sharpe_ratio']:.2f}",
                'Max DD (%)': f"{result['max_drawdown']:.2f}",
                'Win Rate (%)': f"{result['win_rate']:.2f}",
                'Trades': result['trades_count']
            })
        
        # 打印汇总表格
        if symbols_summary:
            # 计算每列的最大宽度
            col_widths = {}
            for col in symbols_summary[0].keys():
                col_widths[col] = max(len(col), max(len(str(row[col])) for row in symbols_summary))
            
            # 打印表头
            header = " | ".join(f"{col:<{col_widths[col]}}" for col in symbols_summary[0].keys())
            report += header + "\n"
            report += "-" * len(header) + "\n"
            
            # 打印数据行
            for row in symbols_summary:
                row_str = " | ".join(f"{str(row[col]):<{col_widths[col]}}" for col in row.keys())
                report += row_str + "\n"
            
            report += "\n"
        
        # 综合性能
        total_return = sum(res['total_return'] for res in self.results.values()) / len(self.results)
        avg_sharpe = sum(res['sharpe_ratio'] for res in self.results.values()) / len(self.results)
        avg_drawdown = sum(res['max_drawdown'] for res in self.results.values()) / len(self.results)
        avg_win_rate = sum(res['win_rate'] for res in self.results.values()) / len(self.results)
        
        report += "Overall Performance:\n"
        report += f"Average Return: {total_return:.2f}%\n"
        report += f"Average Sharpe Ratio: {avg_sharpe:.2f}\n"
        report += f"Average Max Drawdown: {avg_drawdown:.2f}%\n"
        report += f"Average Win Rate: {avg_win_rate:.2f}%\n"
        
        return report
    
    def plot_results(self, symbol=None):
        """绘制回测结果图表"""
        if not self.results:
            self.logger.warning("No backtest results available for plotting")
            return
        
        if symbol and symbol in self.results:
            # 绘制单个交易对结果
            result = self.results[symbol]
            df = result['dataframe']
            
            plt.figure(figsize=(14, 10))
            
            # 绘制价格和交易点
            plt.subplot(2, 1, 1)
            plt.plot(df.index, df['close'], label='Price')
            
            # 添加买卖点
            for trade in result['trades']:
                if trade['type'] == 'buy':
                    plt.scatter(trade['date'], trade['price'], color='green', marker='^', s=100)
                elif trade['type'] == 'sell':
                    plt.scatter(trade['date'], trade['price'], color='red', marker='v', s=100)
            
            plt.title(f'{symbol} Price and Trades')
            plt.legend()
            
            # 绘制资金曲线
            plt.subplot(2, 1, 2)
            plt.plot(df.index, df['cumulative_returns'], label='Returns')
            plt.fill_between(df.index, 1, df['cumulative_returns'], where=df['cumulative_returns'] >= 1, facecolor='green', alpha=0.3)
            plt.fill_between(df.index, 1, df['cumulative_returns'], where=df['cumulative_returns'] < 1, facecolor='red', alpha=0.3)
            
            plt.title(f'{symbol} Cumulative Returns')
            plt.legend()
            
            plt.tight_layout()
            
            # 保存图表
            plt.savefig(f"{Config.DATA_DIR}/{symbol}_backtest_result.png")
            plt.close()
            
            self.logger.info(f"Plot saved for {symbol}")
        else:
            # 绘制所有交易对的对比图
            plt.figure(figsize=(14, 8))
            
            for symbol, result in self.results.items():
                df = result['dataframe']
                plt.plot(df.index, df['cumulative_returns'], label=symbol)
            
            plt.title('Cumulative Returns Comparison')
            plt.legend()
            plt.grid(True)
            
            # 保存图表
            plt.savefig(f"{Config.DATA_DIR}/all_symbols_comparison.png")
            plt.close()
            
            self.logger.info("Comparison plot saved for all symbols")

# 用法示例
if __name__ == "__main__":
    # 初始化回测器
    backtester = Backtester(
        symbols=Config.SYMBOLS,
        timeframe=Config.TIME_INTERVAL,
        start_date=datetime.now() - timedelta(days=30),
        end_date=datetime.now()
    )
    
    # 运行回测
    backtester.run_all()
    
    # 生成报告
    report = backtester.generate_report()
    print(report)
    
    # 绘制结果
    for symbol in Config.SYMBOLS:
        backtester.plot_results(symbol)
    
    # 绘制对比图
    backtester.plot_results()