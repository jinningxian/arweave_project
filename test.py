import json
from asyncio.log import logger
import arweave
from arweave.arweave_lib import Wallet, Transaction
from arweave.transaction_uploader import get_uploader

# wallet_data = json.loads('./token_used/arweave-key-GyltZDFsi09RVhGPoKKsIClHJ6-69yKdKz-mXFAS8fE.json')
# print(type(wallet_data))
# wallet = arweave.Wallet.from_data(wallet_data)
# balance =  wallet.balance
with open('./token_used/arweave-key-GyltZDFsi09RVhGPoKKsIClHJ6-69yKdKz-mXFAS8fE.json', 'r') as f:
  wallet_data = f.read()
  wallet = arweave.Wallet.from_data(wallet_data)
# last_transaction = wallet.get_last_transaction_id()
# print(last_transaction, balance)