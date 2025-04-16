from data_manager import DataManager
from okx_api_client import OKXClient


if __name__ == '__main__':
    client = OKXClient()
    data_manager = DataManager(client)
    result = data_manager.get_kline_data('BTC-USDT', '15m', 10, use_cache=True)
    print(result)