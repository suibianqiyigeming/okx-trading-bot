import time
import pandas as pd
from datetime import datetime, timedelta
from logger import Logger

class BotMonitor:
    def __init__(self, trade_executor=None, data_manager=None):
        self.trade_executor = trade_executor
        self.data_manager = data_manager
        self.logger = Logger()
        
        # 存储性能指标
        self.performance_metrics = {
            'trades_count': 0, # 总交易次数
            'successful_trades': 0,  # 成功交易次数
            'failed_trades': 0,  # 失败交易次数
            'profit_loss': 0,  # 盈亏
            'win_rate': 0,  # 胜率
            'start_balance': 0,  # 初始余额
            'current_balance': 0, # 当前余额
            'roi': 0  # ROI
        }
        
        # 报警设置
        self.alerts = {
            'balance_threshold': 0.1,  # 余额下降超过10%报警
            'consecutive_losses': 3,    # 连续亏损交易数量
            'api_errors': 5            # 连续API错误数量
        }
        
        # 错误计数器
        self.error_counters = {
            'api_errors': 0,
            'consecutive_losses': 0
        }
        
        # 初始化时间
        self.start_time = datetime.now()
        self.last_check_time = self.start_time
    
    def initialize(self):
        """初始化监控器"""
        if self.data_manager:
            self.performance_metrics['start_balance'] = self.data_manager.get_available_balance('USDT')
            self.performance_metrics['current_balance'] = self.performance_metrics['start_balance']
            
            self.logger.info(f"Bot monitor initialized with starting balance: {self.performance_metrics['start_balance']} USDT")
    
    def update_metrics(self):
        """更新性能指标"""
        if not self.data_manager:
            return
        
        # 更新当前余额
        current_balance = self.data_manager.get_available_balance('USDT')
        
        if current_balance > 0 and self.performance_metrics['start_balance'] > 0:
            # 计算ROI
            roi = (current_balance - self.performance_metrics['start_balance']) / self.performance_metrics['start_balance']
            self.performance_metrics['roi'] = roi
            
            # 计算胜率
            if self.performance_metrics['trades_count'] > 0:
                win_rate = self.performance_metrics['successful_trades'] / self.performance_metrics['trades_count']
                self.performance_metrics['win_rate'] = win_rate
        
        self.performance_metrics['current_balance'] = current_balance
        self.performance_metrics['profit_loss'] = current_balance - self.performance_metrics['start_balance']
        
        # 检查是否触发报警
        self.check_alerts()
        
        self.last_check_time = datetime.now()
    
    def record_trade(self, trade_info):
        """记录交易信息并更新指标"""
        self.performance_metrics['trades_count'] += 1
        
        if trade_info.get('status') == 'filled' and trade_info.get('profit', 0) > 0:
            self.performance_metrics['successful_trades'] += 1
            self.error_counters['consecutive_losses'] = 0
        else:
            self.error_counters['consecutive_losses'] += 1
        
        self.update_metrics()
    
    def record_error(self, error_type, error_message):
        """记录错误信息"""
        if error_type == 'api_error':
            self.error_counters['api_errors'] += 1
        
        self.logger.error(f"{error_type}: {error_message}")
        self.check_alerts()
    
    def reset_error_counter(self, error_type):
        """重置错误计数器"""
        if error_type in self.error_counters:
            self.error_counters[error_type] = 0
    
    def check_alerts(self):
        """检查是否需要触发报警"""
        # 检查余额变化
        if self.performance_metrics['start_balance'] > 0:
            balance_change = (self.performance_metrics['current_balance'] - self.performance_metrics['start_balance']) / self.performance_metrics['start_balance']
            
            if balance_change < -self.alerts['balance_threshold']:
                alert_msg = f"ALERT: Balance decreased by {-balance_change*100:.2f}% from {self.performance_metrics['start_balance']} to {self.performance_metrics['current_balance']}"
                self.logger.warning(alert_msg)
                # 这里可以添加发送通知的逻辑
        
        # 检查连续亏损
        if self.error_counters['consecutive_losses'] >= self.alerts['consecutive_losses']:
            alert_msg = f"ALERT: {self.error_counters['consecutive_losses']} consecutive losing trades detected"
            self.logger.warning(alert_msg)
            # 这里可以添加发送通知的逻辑
        
        # 检查API错误
        if self.error_counters['api_errors'] >= self.alerts['api_errors']:
            alert_msg = f"ALERT: {self.error_counters['api_errors']} consecutive API errors detected"
            self.logger.warning(alert_msg)
            # 这里可以添加发送通知的逻辑
    
    def get_performance_summary(self):
        """获取性能摘要"""
        uptime = datetime.now() - self.start_time
        uptime_str = str(uptime).split('.')[0]  # 移除微秒部分
        
        return {
            'uptime': uptime_str,
            'trades_count': self.performance_metrics['trades_count'],
            'win_rate': f"{self.performance_metrics['win_rate']*100:.2f}%",
            'profit_loss': f"{self.performance_metrics['profit_loss']:.2f} USDT",
            'roi': f"{self.performance_metrics['roi']*100:.2f}%",
            'start_balance': f"{self.performance_metrics['start_balance']:.2f} USDT",
            'current_balance': f"{self.performance_metrics['current_balance']:.2f} USDT",
        }
    
    def generate_report(self):
        """生成性能报告"""
        summary = self.get_performance_summary()
        
        report = f"===== Trading Bot Performance Report =====\n"
        report += f"Report Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += f"Bot Uptime: {summary['uptime']}\n\n"
        
        report += f"Trading Statistics:\n"
        report += f"- Total Trades: {summary['trades_count']}\n"
        report += f"- Win Rate: {summary['win_rate']}\n"
        report += f"- Profit/Loss: {summary['profit_loss']}\n"
        report += f"- ROI: {summary['roi']}\n\n"
        
        report += f"Account Information:\n"
        report += f"- Starting Balance: {summary['start_balance']}\n"
        report += f"- Current Balance: {summary['current_balance']}\n\n"
        
        # 添加系统状态信息
        report += f"System Status:\n"
        report += f"- API Error Count: {self.error_counters['api_errors']}\n"
        report += f"- Last Check: {self.last_check_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        self.logger.info(f"Performance report generated")
        return report
        # 这里可以添加发送报告的逻辑