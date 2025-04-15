# 风险管理模块

from config import Config

class RiskManager:
    def __init__(self, data_manager=None):
        self.data_manager = data_manager
        self.position_sizes = {}  # 存储每个交易对的仓位大小
    
    def calculate_position_size(self, symbol, price):
        """计算交易仓位大小"""
        available_balance = self.data_manager.get_available_balance('USDT')
        max_position = available_balance * Config.MAX_POSITION_SIZE
        
        # 根据当前价格计算可以购买的数量
        if price > 0:
            return max_position / price
        return 0
    
    def check_risk_limits(self, symbol, action, price, size):
        """检查交易是否在风险限制内"""
        current_exposure = self.position_sizes.get(symbol, 0)
        
        if action == 'buy':
            new_exposure = current_exposure + size
        elif action == 'sell':
            new_exposure = current_exposure - size
        else:
            new_exposure = current_exposure
        
        # 检查仓位是否超过最大限制
        available_balance = self.data_manager.get_available_balance('USDT')
        position_value = new_exposure * price
        position_ratio = position_value / (available_balance + position_value)
        
        if position_ratio > Config.MAX_POSITION_SIZE:
            return False, f"Position size {position_ratio:.2f} exceeds max allowed {Config.MAX_POSITION_SIZE}"
        
        return True, "Trade within risk limits"
    
    def calculate_stop_loss(self, symbol, entry_price, position_type):
        """计算止损价格
        position_type: 'long' or 'short'
        """
        if position_type == 'long':
            return entry_price * (1 - Config.STOP_LOSS_PERCENT)
        else:  # short
            return entry_price * (1 + Config.STOP_LOSS_PERCENT)
    
    def calculate_take_profit(self, symbol, entry_price, position_type):
        """计算止盈价格
        position_type: 'long' or 'short'
        """
        if position_type == 'long':
            return entry_price * (1 + Config.TAKE_PROFIT_PERCENT)
        else:  # short
            return entry_price * (1 - Config.TAKE_PROFIT_PERCENT)
    
    def update_position(self, symbol, size, price, action):
        """更新持仓信息"""
        current_size = self.position_sizes.get(symbol, 0)
        
        if action == 'buy':
            self.position_sizes[symbol] = current_size + size
        elif action == 'sell':
            self.position_sizes[symbol] = current_size - size
    
    def check_stop_conditions(self, symbol, current_price, entry_price, position_type):
        """检查是否触发止损或止盈"""
        if position_type == 'long':
            # 止损条件
            if current_price <= self.calculate_stop_loss(symbol, entry_price, position_type):
                return True, 'stop_loss'
            
            # 止盈条件
            if current_price >= self.calculate_take_profit(symbol, entry_price, position_type):
                return True, 'take_profit'
        
        elif position_type == 'short':
            # 止损条件
            if current_price >= self.calculate_stop_loss(symbol, entry_price, position_type):
                return True, 'stop_loss'
            
            # 止盈条件
            if current_price <= self.calculate_take_profit(symbol, entry_price, position_type):
                return True, 'take_profit'
        
        return False, None
