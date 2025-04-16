from okx_api_client import OKXClient

if __name__ == '__main__':
    client = OKXClient()
    response = client.get_kline_data('BTC-USDT', '15m', 10)
    print(response)


