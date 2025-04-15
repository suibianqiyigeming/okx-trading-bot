import okx.Account as Account
import json

# API 初始化
apikey = "f3b61ddd-f9fa-46dd-b473-223b2a5b160d"
secretkey = "AB0CC20F1A122C6665A191403A62A710"
passphrase = "Pql7621200208."

flag = "1"  # 实盘:0 , 模拟盘:1

accountAPI = Account.AccountAPI(apikey, secretkey, passphrase, False, flag)

# 查看账户余额
result = accountAPI.get_account_balance()
# result1 = json.loads(result)
print(result)
