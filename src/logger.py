# 日志模块

import os
import logging
from datetime import datetime
from config import Config

class Logger:
    def __init__(self, log_level=None, log_file=None):
        log_level = log_level or Config.LOG_LEVEL
        
        # 创建日志目录
        log_dir = os.path.join(Config.DATA_DIR, 'logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # 设置默认日志文件名
        if not log_file:
            timestamp = datetime.now().strftime('%Y%m%d')
            log_file = os.path.join(log_dir, f'trading_bot_{timestamp}.log')
        
        # 配置日志记录器
        self.logger = logging.getLogger('trading_bot')
        self.logger.setLevel(getattr(logging, log_level))
        
        # 添加文件处理器
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, log_level))
        
        # 添加控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, log_level))
        
        # 设置格式
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # 添加处理器到记录器
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def info(self, message):
        """记录信息级别日志"""
        self.logger.info(message)
    
    def warning(self, message):
        """记录警告级别日志"""
        self.logger.warning(message)
    
    def error(self, message):
        """记录错误级别日志"""
        self.logger.error(message)
    
    def debug(self, message):
        """记录调试级别日志"""
        self.logger.debug(message)
    
    def critical(self, message):
        """记录严重错误级别日志"""
        self.logger.critical(message)