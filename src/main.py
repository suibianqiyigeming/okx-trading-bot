import time
import signal
import sys
from datetime import datetime, timedelta
from config import Config
from api import OKXClient
from data import DataManager
from strategy import MACDStrategy, RSIStrategy, CombinedStrategy
from risk import RiskManager
from execution import TradeExecutor
from utils import BotMonitor,Logger


class TradingBot:
    def __init__(self):
        # 初始化API客户端
        self.client = OKXClient(
            api_key=Config.API_KEY,
            secret_key=Config.SECRET_KEY,
            passphrase=Config.PASSPHRASE,
            base_url=Config.BASE_URL
        )
        
        # 初始化数据管理器
        self.data_manager = DataManager(self.client)
        
        # 初始化风险管理器
        self.risk_manager = RiskManager(self.data_manager)
        
        # 初始化交易执行器
        self.trade_executor = TradeExecutor(
            client=self.client,
            data_manager=self.data_manager,
            risk_manager=self.risk_manager
        )
        
        # 初始化监控器
        self.monitor = BotMonitor(
            trade_executor=self.trade_executor,
            data_manager=self.data_manager
        )
        
        # 初始化策略
        self.strategies = {}
        for symbol in Config.SYMBOLS:
            # 创建组合策略
            combined_strategy = CombinedStrategy()
            # 添加MACD策略
            combined_strategy.add_strategy(MACDStrategy())
            # 添加RSI策略
            combined_strategy.add_strategy(RSIStrategy())
            
            self.strategies[symbol] = combined_strategy
        
        # 记录器
        self.logger = Logger()
        
        # 运行标志
        self.running = False
        
        # 注册信号处理
        signal.signal(signal.SIGINT, self.handle_shutdown)
        signal.signal(signal.SIGTERM, self.handle_shutdown)
    
    def initialize(self):
        """初始化交易机器人"""
        try:
            # 初始化监控器
            self.monitor.initialize()
            
            # 记录初始状态
            for symbol in Config.SYMBOLS:
                price = self.data_manager.get_latest_price(symbol)
                if price:
                    self.logger.info(f"Initial price for {symbol}: {price}")
            
            # 记录账户余额
            balance = self.data_manager.get_available_balance('USDT')
            self.logger.info(f"Initial account balance: {balance} USDT")
            
            self.logger.info("Trading bot initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing trading bot: {str(e)}")
            return False
    
    def process_symbol(self, symbol):
        """处理单个交易对的策略和交易"""
        try:
            # 获取K线数据
            kline_data = self.data_manager.get_kline_data(
                symbol=symbol,
                interval=Config.TIME_INTERVAL,
                limit=100,
                use_cache=False  # 确保获取最新数据
            )
            
            if kline_data.empty:
                self.logger.warning(f"No kline data available for {symbol}")
                return
            
            # 生成交易信号
            strategy = self.strategies.get(symbol)
            if not strategy:
                self.logger.warning(f"No strategy defined for {symbol}")
                return
            
            df_with_signals = strategy.generate_signals(kline_data)
            
            # 获取最新信号
            latest_signal = df_with_signals['signal_action'].iloc[-1]
            
            # 记录信号
            self.logger.info(f"Signal for {symbol}: {latest_signal}")
            
            # 执行交易
            if latest_signal in ['buy', 'sell']:
                # 获取最新价格
                latest_price = self.data_manager.get_latest_price(symbol)
                
                if not latest_price:
                    self.logger.error(f"Failed to get latest price for {symbol}")
                    return
                
                # 计算交易数量
                size = self.risk_manager.calculate_position_size(symbol, latest_price)
                
                if size <= 0:
                    self.logger.warning(f"Calculated position size too small for {symbol}: {size}")
                    return
                
                # 执行交易
                order_id = self.trade_executor.execute_trade(
                    symbol=symbol,
                    action=latest_signal,
                    size=size
                )
                
                if order_id:
                    self.logger.info(f"Trade executed for {symbol}: {latest_signal} {size} at {latest_price}")
                    
                    # 如果是买入，设置止损和止盈
                    if latest_signal == 'buy':
                        # 设置止损
                        stop_loss_id = self.trade_executor.place_stop_loss_order(
                            symbol=symbol,
                            entry_price=latest_price,
                            position_type='long',
                            size=size
                        )
                        
                        # 设置止盈
                        take_profit_id = self.trade_executor.place_take_profit_order(
                            symbol=symbol,
                            entry_price=latest_price,
                            position_type='long',
                            size=size
                        )
                        
                        if stop_loss_id:
                            self.logger.info(f"Stop loss order placed for {symbol}: {stop_loss_id}")
                        
                        if take_profit_id:
                            self.logger.info(f"Take profit order placed for {symbol}: {take_profit_id}")
                
        except Exception as e:
            self.logger.error(f"Error processing {symbol}: {str(e)}")
    
    def run(self):
        """运行交易机器人"""
        self.running = True
        
        if not self.initialize():
            self.logger.error("Failed to initialize trading bot. Exiting.")
            return
        
        self.logger.info("Trading bot started")
        
        try:
            while self.running:
                # 处理每个交易对
                for symbol in Config.SYMBOLS:
                    self.process_symbol(symbol)
                
                # 更新监控指标
                self.monitor.update_metrics()
                
                # 每小时生成一次报告
                current_hour = datetime.now().hour
                if hasattr(self, 'last_report_hour') and self.last_report_hour != current_hour:
                    report = self.monitor.generate_report()
                    self.logger.info(report)
                
                self.last_report_hour = current_hour
                
                # 等待下一个循环
                time.sleep(60)  # 每分钟检查一次
                
        except Exception as e:
            self.logger.error(f"Error in main trading loop: {str(e)}")
        
        finally:
            self.shutdown()
    
    def handle_shutdown(self, signum, frame):
        """处理关闭信号"""
        self.logger.info(f"Received shutdown signal: {signum}")
        self.running = False
    
    def shutdown(self):
        """关闭交易机器人"""
        self.logger.info("Shutting down trading bot...")
        
        # 取消所有活跃订单
        self.trade_executor.cancel_all_orders()
        
        # 生成最终报告
        final_report = self.monitor.generate_report()
        self.logger.info("Final performance report:")
        self.logger.info(final_report)
        
        self.logger.info("Trading bot shutdown complete")

if __name__ == "__main__":
    bot = TradingBot()
    bot.run()