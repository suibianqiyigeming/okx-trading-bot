import okx.Funding as Funding

# API 初始化
apikey = "f3b61ddd-f9fa-46dd-b473-223b2a5b160d"
secretkey = "AB0CC20F1A122C6665A191403A62A710"
passphrase = "Pql7621200208."

flag = "1"  # 实盘: 0, 模拟盘: 1

fundingAPI = Funding.FundingAPI(apikey, secretkey, passphrase, False, flag)

# 获取资金账户余额
result1 = fundingAPI.get_balances()
print(result1)

print("=======================================")

# 获取资金账户余额（指定币种）
result2 = fundingAPI.get_balances("BTC")
print(result2)
print("=======================================")
