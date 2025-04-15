# 交易执行模块
# 该模块负责与交易所API进行交互，执行买卖操作，检查订单状态等功能
import time
from datetime import datetime
from api import OKXClient
from data import DataManager
from risk import RiskManager
from utils import Logger

class TradeExecutor:
    def __init__(self, client=None, data_manager=None, risk_manager=None):
        self.client = client or OKXClient()
        self.data_manager = data_manager or DataManager(self.client)
        self.risk_manager = risk_manager or RiskManager(self.data_manager)
        self.logger = Logger()
        
        # 存储活跃订单
        self.active_orders = {}
        # 存储交易记录
        self.trade_history = []
    
    def execute_trade(self, symbol, action, order_type='market', size=None, price=None):
        """执行交易操作"""
        try:
            if action not in ['buy', 'sell']:
                self.logger.error(f"Invalid action: {action}")
                return None
            
            # 获取当前价格(如果未提供)
            current_price = price or self.data_manager.get_latest_price(symbol)
            if not current_price:
                self.logger.error(f"Failed to get current price for {symbol}")
                return None
            
            # 计算交易数量(如果未提供)
            if not size:
                size = self.risk_manager.calculate_position_size(symbol, current_price)
                if size <= 0:
                    self.logger.error(f"Invalid position size calculated: {size}")
                    return None
            
            # 检查风险限制
            risk_ok, risk_message = self.risk_manager.check_risk_limits(symbol, action, current_price, size)
            if not risk_ok:
                self.logger.warning(f"Risk check failed: {risk_message}")
                return None
            
            # 执行下单
            order_result = self.client.place_order(
                symbol=symbol,
                side=action,
                order_type=order_type,
                size=size,
                price=price if order_type == 'limit' else None
            )
            
            if order_result.get('code') == '0':
                order_data = order_result.get('data')[0]
                order_id = order_data.get('ordId')
                
                # 记录订单信息
                order_info = {
                    'id': order_id,
                    'symbol': symbol,
                    'action': action,
                    'type': order_type,
                    'size': size,
                    'price': price if order_type == 'limit' else current_price,
                    'status': 'placed',
                    'timestamp': datetime.now().isoformat()
                }
                
                self.active_orders[order_id] = order_info
                self.trade_history.append(order_info)
                
                # 更新仓位信息
                self.risk_manager.update_position(symbol, size, current_price, action)
                
                self.logger.info(f"Order placed: {order_id} | {action} {size} {symbol} at {price if order_type == 'limit' else current_price}")
                return order_id
            else:
                self.logger.error(f"Order placement failed: {order_result}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error executing trade: {str(e)}")
            return None
    
    def check_order_status(self, order_id):
        """检查订单状态"""
        if order_id not in self.active_orders:
            return None
        
        order_info = self.active_orders[order_id]
        symbol = order_info['symbol']
        
        try:
            response = self.client.get_order_details(symbol, order_id)
            
            if response.get('code') == '0':
                order_data = response.get('data')[0]
                status = order_data.get('state')
                
                # 更新订单状态
                self.active_orders[order_id]['status'] = status
                
                if status in ['filled', 'canceled']:
                    # 订单已完成或取消，从活跃订单中移除
                    del self.active_orders[order_id]
                
                return status
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error checking order status: {str(e)}")
            return None
    
    def cancel_order(self, order_id):
        """取消订单"""
        if order_id not in self.active_orders:
            return False
        
        order_info = self.active_orders[order_id]
        symbol = order_info['symbol']
        
        try:
            response = self.client.cancel_order(symbol, order_id)
            
            if response.get('code') == '0':
                # 更新订单状态
                self.active_orders[order_id]['status'] = 'canceling'
                self.logger.info(f"Order cancel initiated: {order_id}")
                return True
            else:
                self.logger.error(f"Order cancel failed: {response}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error canceling order: {str(e)}")
            return False
    
    def cancel_all_orders(self, symbol=None):
        """取消所有活跃订单"""
        orders_to_cancel = list(self.active_orders.keys())
        
        if symbol:
            orders_to_cancel = [
                order_id for order_id, info in self.active_orders.items()
                if info['symbol'] == symbol
            ]
        
        results = []
        for order_id in orders_to_cancel:
            result = self.cancel_order(order_id)
            results.append((order_id, result))
        
        return results
    
    def place_stop_loss_order(self, symbol, entry_price, position_type, size):
        """设置止损订单"""
        stop_price = self.risk_manager.calculate_stop_loss(symbol, entry_price, position_type)
        
        action = 'sell' if position_type == 'long' else 'buy'
        
        # 执行止损订单
        order_id = self.execute_trade(
            symbol=symbol,
            action=action,
            order_type='limit',
            size=size,
            price=stop_price
        )
        
        if order_id:
            self.active_orders[order_id]['order_type'] = 'stop_loss'
        
        return order_id
    
    def place_take_profit_order(self, symbol, entry_price, position_type, size):
        """设置止盈订单"""
        take_profit_price = self.risk_manager.calculate_take_profit(symbol, entry_price, position_type)
        
        action = 'sell' if position_type == 'long' else 'buy'
        
        # 执行止盈订单
        order_id = self.execute_trade(
            symbol=symbol,
            action=action,
            order_type='limit',
            size=size,
            price=take_profit_price
        )
        
        if order_id:
            self.active_orders[order_id]['order_type'] = 'take_profit'
        
        return order_id
