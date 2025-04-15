# 配置文件，存储API密钥和交易参数，目前主要交易BTC和ETH现货对

class Config:
    # API配置
    API_KEY = "YOUR_OKX_API_KEY" #替换成自己的
    SECRET_KEY = "YOUR_OKX_SECRET_KEY"
    PASSPHRASE = "YOUR_OKX_PASSPHRASE"
    BASE_URL = "https://www.okx.com"  # 正式环境
    # BASE_URL = "https://www.okx.com/api/v5/sandbox" # 沙箱环境
    
    # 交易配置
    SYMBOLS = ["BTC-USDT", "ETH-USDT"]
    TIME_INTERVAL = "15m"  # 时间间隔: 1m, 5m, 15m, 30m, 1H, 4H, 1D
    
    # 资金管理 合理设置仓位和止损止盈比例
    INITIAL_CAPITAL = 100000  # 初始资金
    MAX_POSITION_SIZE = 0.1  # 最大仓位比例(相对于总资金)
    STOP_LOSS_PERCENT = 0.02  # 止损比例
    TAKE_PROFIT_PERCENT = 0.05  # 止盈比例
    
    # 系统配置
    LOG_LEVEL = "INFO"
    DATA_DIR = "./data"