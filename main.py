import arweave
from arweave.arweave_lib import Wallet, Transaction
from arweave.transaction_uploader import get_uploader

wallet_file_path = "./wallet_path/arweave-key-63zeIK4-rpSvH4BNVb7cEBEJWldTPOnTw2uaMaLs73M.json"
wallet = arweave.Wallet(wallet_file_path)

# def getBalance(wallet_file_path):



balance =  wallet.balance

last_transaction = wallet.get_last_transaction_id()
print(last_transaction, balance)
wallet = Wallet(wallet_file_path)
with open('Python.pdf', 'r', encoding="latin-1") as mypdf:
    pdf_string_data = mypdf.read()
    transaction = Transaction(wallet, data=pdf_string_data)
    transaction.sign()
    transaction.send()

    print(transaction)

tx = Transaction(wallet, id="0x0000019436E494F0")
tx.get_transaction()