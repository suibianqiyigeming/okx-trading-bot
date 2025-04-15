from okx_api_client import OKXClient

if __name__ == '__main__':
    client = OKXClient()
    result = client.get_account_balance()
    print(result)
